## 1. Overview


This is a **Microsoft Teams bot** deployed as an **Azure Function** that uses a **LangGraph ReAct agent** backed by an **Azure AI Foundry** language model.

Conversation history is persisted per-session in **Azure PostgreSQL**, and authentication to both PostgreSQL and the LLM uses **Azure Managed Identity** (no secrets/passwords required at runtime).


### 1.1. Project Structure

| File | Responsibility |
|---|---|
| [function_app.py](function_app.py) | Azure Functions HTTP trigger; shim layer between Functions SDK and Agents SDK |
| [bot.py](bot.py) | Microsoft Agents SDK setup; Teams protocol, auth, and message routing |
| [agent.py](agent.py) | LangGraph ReAct agent; PostgreSQL-backed memory; Azure AI Foundry LLM |
| [requirements.txt](requirements.txt) | Python dependencies |

The **single UAMI** serves double duty:
- **Directly** in agent.py via `ManagedIdentityCredential` for Foundry and PostgreSQL
- **As a FIC** in bot.py via `MsalConnectionManager` — MSAL presents the UAMI's token as a client assertion to Entra ID, exchanging it for a Bot Framework service token, eliminating the need for a client secret entirely.

### 1.2. High-Level Architecture

```mermaid
graph TB
    subgraph Teams["Microsoft Teams"]
        User([User])
    end

    subgraph BotFramework["Bot Framework / Azure Bot Service"]
        BFS[Bot Framework Service\nJWT token issuer + relay]
    end

    subgraph AzureFunctions["Azure Functions (this codebase)"]
        direction TB
        FA["function_app.py\nHTTP Trigger /messages"]
        BOT["bot.py\nAgents SDK Layer"]
        AGT["agent.py\nLangGraph ReAct Agent"]
    end

    subgraph AzureServices["Azure Services"]
        FOUNDRY["Azure AI Foundry\nLLM Endpoint"]
        PG["Azure DB for PostgreSQL\nLangGraph Checkpoints"]
        UAMI["User-Assigned\nManaged Identity"]
    end

    User -->|Activity JSON over HTTPS| BFS
    BFS -->|POST /messages + JWT| FA
    FA --> BOT
    BOT -->|Validates JWT, routes turn| AGT
    AGT -->|Token via UAMI| FOUNDRY
    AGT -->|Token via UAMI| PG
    UAMI -.->|FIC: bot auth outbound| BOT
    UAMI -.->|Direct: LLM + DB access| AGT
```

## 2. function_app.py — The Entry Point

```mermaid
sequenceDiagram
    participant Teams as Teams / Bot Framework Service
    participant FA as Azure Functions Runtime
    participant Shim as FunctionRequestShim
    participant SDK as start_agent_process()

    Teams->>FA: POST /messages (Activity JSON + JWT headers)
    FA->>FA: req.get_json() → body dict
    FA->>Shim: FunctionRequestShim(body, headers, method)
    Shim-->>FA: object with .json(), .headers, .method
    FA->>SDK: start_agent_process(shim, AGENT_APP, ADAPTER)
    SDK->>SDK: JWT validation, turn dispatch
    FA-->>Teams: HTTP 200
```

**Key design decisions:**

- `http_auth_level=func.AuthLevel.ANONYMOUS` — Azure Functions itself does **not** validate the caller. JWT validation is delegated entirely to the Agents SDK (`CloudAdapter`). This is correct: the token is a Bot Framework-issued JWT, not an Azure Functions key.
- **`FunctionRequestShim`** — `start_agent_process` was written for the `aiohttp` request model (expecting `.json()`, `.headers`, `.method`). Azure Functions' `HttpRequest` has a different interface. The shim bridges them with the three attributes the SDK actually reads, without pulling in `aiohttp` as a runtime dependency.
- The logging line `logging.getLogger('microsoft_agents').setLevel(...)` silences the Agents SDK at `WARNING` by default but can be raised via the `AGENTS_SDK_LOG_LEVEL` env var.

## 3. bot.py — Microsoft Agents SDK Layer

### 3.1 Component Setup (module-level singletons)

```python
agents_sdk_config = load_configuration_from_env(environ)   # reads env vars → dict
STORAGE            = MemoryStorage()                         # in-process turn state
CONNECTION_MANAGER = MsalConnectionManager(**agents_sdk_config)
ADAPTER            = CloudAdapter(connection_manager=CONNECTION_MANAGER)
AUTHORIZATION      = Authorization(STORAGE, CONNECTION_MANAGER, **agents_sdk_config)
AGENT_APP          = AgentApplication[TurnState](...)
```

All five objects are **module-level singletons** — created once at cold-start and reused across all invocations within the same Function worker instance.

### 3.2 Message Handlers

| Handler | Trigger | Behavior |
|---|---|---|
| `on_members_added` | `conversationUpdate / membersAdded` | Sends welcome message when bot is added |
| `on_clear` | `/clear` message text | Deletes LangGraph checkpoint rows for the current thread |
| `on_message` | Any `message` activity | Sends typing indicator, invokes ReAct agent, sends reply |
| `on_error` | Any unhandled exception | Sends generic error message to user |

### 3.3 Session ID Strategy

```python
match conv_type:
    case 'channel':   session_id = f"channel:{team_id}:{conv_id}"
    case 'groupChat': session_id = f"groupChat:{conv_id}"
    case _:           session_id = f"personal:{conv_id}"
```

Teams has three conversation scopes. The `session_id` becomes LangGraph's `thread_id`, so conversation history is isolated per-channel, per-group-chat, and per-personal-chat.

## 4. agent.py — LangGraph ReAct Agent

### 4.1 `AgentManager` Lifecycle

```mermaid
stateDiagram-v2
    [*] --> Uninitialized : AgentManager()
    Uninitialized --> BuildingPool : get_agent() called\n(no agent or token expired)
    BuildingPool --> TokenFetch : _build_pool()
    TokenFetch --> PoolOpen : UAMI → ossrdbms token
    PoolOpen --> CheckpointerSetup : AsyncPostgresSaver.setup()
    CheckpointerSetup --> ModelInit : init_chat_model(azure_ai:...)
    ModelInit --> AgentReady : create_react_agent(...)
    AgentReady --> AgentReady : get_agent() → return existing\n(token still valid)
    AgentReady --> BuildingPool : token within 300s of expiry\n→ rebuild pool + agent
```

**Token refresh logic** uses a double-checked lock pattern:
```python
if self.agent and time.time() < self.token_expiry - BUFFER:
    return self.agent          # fast path, no lock
async with self.lock:
    if self.agent and time.time() < self.token_expiry - BUFFER:
        return self.agent      # re-check after lock
    # ... rebuild
```
This prevents multiple concurrent requests from each rebuilding the pool on token expiry.

### 4.2 LangGraph ReAct Agent Stack

```
create_react_agent(
  model      = AzureAI(Foundry)  ← UAMI credential
  tools      = []                ← extensible
  prompt     = system + MessagesPlaceholder
  checkpointer = AsyncPostgresSaver(pool)  ← persisted memory
)
```

`AsyncPostgresSaver` stores LangGraph checkpoints in three PostgreSQL tables: `checkpoints`, `checkpoint_blobs`, `checkpoint_writes`. The `/clear` command deletes all three for the current `thread_id`.

## 5. Bot Authentication Flow

This is the most complex part. There are **two distinct authentication concerns**:

| Concern | Direction | Mechanism |
|---|---|---|
| **Inbound JWT validation** | Teams → Bot | `CloudAdapter` verifies Bot Framework JWT on every incoming request |
| **Outbound token acquisition** | Bot → Bot Framework Service | `MsalConnectionManager` + UAMI as FIC to prove bot identity |

### 5.1 Environment Variable Loading

```mermaid
flowchart LR
    ENV["Azure Functions\nApp Settings\n(environment variables)"]
    LCE["load_configuration_from_env(environ)"]
    CFG["agents_sdk_config dict\n• MicrosoftAppId\n• MicrosoftAppTenantId\n• MicrosoftAppType = UserAssignedMsi\n• MicrosoftAppClientId (UAMI_CLIENT_ID)"]

    ENV --> LCE --> CFG
    CFG --> AUTH["Authorization(...)"]
    CFG --> MCM["MsalConnectionManager(...)"]
    CFG --> AA["AgentApplication(...)"]
```

`load_configuration_from_env` reads well-known Bot Framework env vars and returns them as a dict that is `**kwargs`-spread into all SDK components.

### 5.2 FIC Bot Authentication (Outbound — UAMI as Federated Identity Credential)

When `MicrosoftAppType=UserAssignedMsi`, the bot has **no client secret**. Instead, the UAMI is configured as a Federated Identity Credential on the App Registration. MSAL acquires a token for the Bot Framework service by presenting the UAMI's managed identity token as the assertion.

```mermaid
sequenceDiagram
    participant IMDS as Azure IMDS\n(169.254.169.254)
    participant MSAL as MsalConnectionManager
    participant AAD as Microsoft Entra ID
    participant BFS as Bot Framework Service

    Note over MSAL: Bot needs to call Bot Framework Service<br/>(e.g. send proactive message / reply)
    MSAL->>IMDS: GET token?resource=...&client_id=UAMI_CLIENT_ID
    IMDS-->>MSAL: UAMI access token (assertion)
    MSAL->>AAD: POST /token\nclient_id=MicrosoftAppId\nclient_assertion=<UAMI token>\ngrant_type=jwt-bearer (FIC)
    AAD-->>MSAL: Bot Framework service token
    MSAL->>BFS: API call with Bot Framework token
    BFS-->>MSAL: Response
```

### 5.3 Inbound JWT Validation (Incoming — CloudAdapter)

```mermaid
sequenceDiagram
    participant BFS as Bot Framework Service
    participant FA as function_app.py
    participant CA as CloudAdapter
    participant AA as AgentApplication

    BFS->>FA: POST /messages\nAuthorization: Bearer <JWT>
    FA->>CA: start_agent_process(shim, AGENT_APP, ADAPTER)
    CA->>CA: Fetch Bot Framework public keys (JWKS)
    CA->>CA: Verify JWT signature, issuer, audience, expiry
    alt JWT invalid
        CA-->>FA: raise AuthenticationError
        FA-->>BFS: HTTP 401/500
    else JWT valid
        CA->>AA: dispatch Activity to AGENT_APP handlers
        AA-->>FA: turn complete
        FA-->>BFS: HTTP 200
    end
```

## 6. Environment Variables — Two Authentication Domains

```mermaid
graph TB
    subgraph AppSettings["Azure Functions App Settings"]
        direction TB
        V1["UAMI_CLIENT_ID"]
        V2["MicrosoftAppId"]
        V3["MicrosoftAppTenantId"]
        V4["MicrosoftAppType = UserAssignedMsi"]
        V5["FOUNDRY_PROJECT_ENDPOINT"]
        V6["FOUNDRY_MODEL"]
        V7["POSTGRES_HOST / DB / USER / PORT"]
        V8["POSTGRES_POOL_MAX\nTOKEN_REFRESH_BUFFER_SECONDS"]
        V9["AGENT_SYSTEM_PROMPT\nAGENTS_SDK_LOG_LEVEL"]
    end

    subgraph PathA["Path A — UAMI Direct (agent.py)"]
        MA["ManagedIdentityCredential\nclient_id=UAMI_CLIENT_ID"]
        MA -->|Token scope:\nhttps://ossrdbms-aad...| PG["PostgreSQL\npassword = token.token"]
        MA -->|credential= kwarg| LLM["Azure AI Foundry\ninit_chat_model(azure_ai:...)"]
    end

    subgraph PathB["Path B — FIC Bot Auth (bot.py)"]
        MB["MsalConnectionManager\nload_configuration_from_env"]
        MB -->|AppType=UserAssignedMsi\nAsserts UAMI token| AAD["Entra ID\n→ Bot Framework token"]
        AAD --> BFS["Bot Framework Service\n(reply, proactive)"]
    end

    V1 --> MA
    V1 --> MB
    V2 --> MB
    V3 --> MB
    V4 --> MB
    V5 --> LLM
    V6 --> LLM
    V7 --> PG
```

### 6.1. Complete Environment Variable Reference

| Variable | Used In | Purpose |
|---|---|---|
| `UAMI_CLIENT_ID` | agent.py | Client ID of the UAMI used directly by `ManagedIdentityCredential` for PostgreSQL and Foundry authentication |
| `FOUNDRY_PROJECT_ENDPOINT` | agent.py | Azure AI Foundry project URL |
| `FOUNDRY_MODEL` | agent.py | Model deployment name (e.g. `gpt-4o`) |
| `POSTGRES_HOST` | agent.py | PostgreSQL server FQDN |
| `POSTGRES_DB` | agent.py | Database name for checkpoints |
| `POSTGRES_USER` | agent.py | AAD-mapped PostgreSQL user (typically UAMI's display name) |
| `POSTGRES_PORT` | agent.py | Default `5432` |
| `POSTGRES_POOL_MAX` | agent.py | Max pool connections, default `5` |
| `TOKEN_REFRESH_BUFFER_SECONDS` | agent.py | Proactive token refresh window, default `300` |
| `AGENT_SYSTEM_PROMPT` | agent.py | System message for the LLM |
| `AGENTS_SDK_LOG_LEVEL` | function_app.py | SDK verbosity, default `WARNING` |

### 6.2. Microsoft 365 Agents SDK environment variables

Authentication for the M365 agents SDK uses app registration credentials loaded by `load_configuration_from_env` in bot.py.
- Support for `FederatedCredentials` auth type is released in [v0.9.0](https://github.com/microsoft/Agents-for-python/blob/main/changelog.md#microsoft-365-agents-sdk-for-python---release-notes-v090).
- At the point of writing, `FederatedCredentials` auth type is yet to be updated in the [python doc](https://learn.microsoft.com/en-us/microsoft-365/agents-sdk/configure-authentication-msal?pivots=python).
- The [node.js doc for FederatedCredentials](https://learn.microsoft.com/en-us/microsoft-365/agents-sdk/configure-authentication-msal?pivots=nodejs#federatedcredentials) provides the environment variables for `FederatedCredentials` auth type, with difference that python SDK seems to use `CONNECTIONS__SERVICE_CONNECTION__SETTINGS__FEDERATEDCLIENTID` instead of `CONNECTIONS__SERVICE_CONNECTION__SETTINGS__FICCLIENTID`

| Variable | Value |
|---|---|
| `CONNECTIONS__SERVICE_CONNECTION__SETTINGS__AUTHTYPE` | `FederatedCredentials `|
| `CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTID` | `{app-id-guid} `|
| `CONNECTIONS__SERVICE_CONNECTION__SETTINGS__TENANTID` | `{tenant-id-guid} `|
| `CONNECTIONS__SERVICE_CONNECTION__SETTINGS__AUTHORITY` | `https://login.microsoftonline.com/{tenant-id-guid} `|
| `CONNECTIONS__SERVICE_CONNECTION__SETTINGS__FEDERATEDCLIENTID` | `{managed-identity-client-id} `|
| `CONNECTIONS__SERVICE_CONNECTION__SETTINGS__SCOPE` | `https://api.botframework.com `|

## 7. Full End-to-End Message Flow

```mermaid
sequenceDiagram
    participant U as User (Teams)
    participant BFS as Bot Framework Service
    participant FA as function_app.py
    participant BOT as bot.py (AgentApp)
    participant CA as CloudAdapter
    participant AGT as agent.py (AgentManager)
    participant PG as PostgreSQL
    participant LLM as Azure AI Foundry

    U->>BFS: Sends message
    BFS->>FA: POST /messages\nBearer JWT + Activity JSON
    FA->>FA: req.get_json() → FunctionRequestShim
    FA->>CA: start_agent_process()
    CA->>CA: Validate JWT (Bot Framework JWKS)
    CA->>BOT: dispatch Activity → on_message()
    BOT->>BOT: get_session_id() → thread_id
    BOT->>BFS: send typing indicator
    BOT->>AGT: agent_manager.get_agent()
    alt Token expired
        AGT->>AGT: UAMI → ossrdbms token
        AGT->>PG: Open new connection pool
        AGT->>AGT: AsyncPostgresSaver.setup()
        AGT->>AGT: init_chat_model() with UAMI credential
        AGT->>AGT: create_react_agent()
    end
    BOT->>AGT: agent.ainvoke({messages}, thread_id)
    AGT->>PG: Load checkpoint for thread_id
    PG-->>AGT: Prior messages / state
    AGT->>LLM: Chat completion (UAMI token)
    LLM-->>AGT: Assistant response
    AGT->>PG: Save new checkpoint
    AGT-->>BOT: response['messages'][-1]
    BOT->>BFS: send_activity(text)
    BFS->>U: Message displayed in Teams
    FA-->>BFS: HTTP 200
```

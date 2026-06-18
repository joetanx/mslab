## 1. Overview

This is a **Microsoft Teams bot** deployed as an **Azure Function** that uses a **LangGraph ReAct agent** backed by an **Azure AI Foundry** language model. Conversation history is persisted per-session in **Azure PostgreSQL**, and authentication to both PostgreSQL and the LLM uses **Azure Managed Identity** (no secrets/passwords required at runtime).


### 1.1. Project Structure

| File | Responsibility |
|---|---|
| function_app.py | Azure Functions HTTP entry point - receives Teams webhook POSTs |
| bot.py | Microsoft Agents SDK - activity routing and Teams event handling |
| agent.py | LangGraph agent lifecycle - lazy init, token refresh, conversation management |
| requirements.txt | Python dependencies |


### 1.2. High-Level Architecture

```mermaid
flowchart TD
    Teams["Microsoft Teams Client"]
    BotConnector["Bot Connector Service\n(Microsoft Cloud)"]
    AzFunc["Azure Functions\nPOST /messages\nfunction_app.py"]
    BotLayer["Bot Activity Router\nbot.py"]
    AgentLayer["LangGraph Agent\nagent.py"]
    AOAI["Azure AI Foundry\nLLM (chat model)"]
    PG["Azure PostgreSQL\nConversation Checkpoints"]
    UAMI["Managed Identity\n(UAMI)"]

    Teams -->|User sends message| BotConnector
    BotConnector -->|JWT-signed HTTP POST| AzFunc
    AzFunc -->|Wraps & dispatches activity| BotLayer
    BotLayer -->|Routes to handler| AgentLayer
    AgentLayer -->|Streams tokens| AOAI
    AgentLayer -->|Read / write checkpoints| PG
    UAMI -->|AAD tokens| AgentLayer
    UAMI -->|AAD tokens| AOAI
    AgentLayer -->|Streamed reply| BotLayer
    BotLayer -->|send_activity| BotConnector
    BotConnector -->|Delivers reply| Teams
```

## 2. Components

### 2.1. [function_app.py](function_app.py) - Azure Functions Entry Point

Receives HTTP POSTs from the Bot Connector, validates the JSON body, and delegates to the SDK.

**Key design decisions:**
- `AuthLevel.ANONYMOUS` is intentional - JWT validation is handled by the Microsoft Agents SDK inside `start_agent_process`, not by the Functions host.
- `_CIHeaders` provides a case-insensitive header wrapper so the aiohttp-flavoured SDK works against the Azure Functions `HttpRequest`.
- `_FuncRequest` is a lightweight shim that makes an `HttpRequest` look like an `aiohttp` request (required by `start_agent_process`).

```mermaid
sequenceDiagram
    participant Teams as Bot Connector
    participant AF as Azure Function (messages)
    participant Shim as _FuncRequest shim
    participant SDK as start_agent_process (SDK)
    participant Bot as AGENT_APP (bot.py)

    Teams->>AF: POST /messages (JSON body + JWT header)
    AF->>AF: req.get_json() - parse body
    alt Invalid JSON
        AF-->>Teams: 400 Bad Request
    end
    AF->>Shim: wrap body + headers in _FuncRequest
    AF->>SDK: await start_agent_process(mock_req, AGENT_APP, ADAPTER)
    SDK->>SDK: Validate JWT bearer token
    SDK->>Bot: Dispatch Activity to registered handlers
    Bot-->>SDK: Handler completes (replies sent via Bot Connector)
    SDK-->>AF: returns
    AF-->>Teams: 200 OK (acknowledgement)
```

### 2.2. [bot.py](bot.py) - Activity Routing & Teams Handlers

Sets up the `AgentApplication` and registers three activity handlers.

**Module-level singletons (initialised at import time):**

| Object | Type | Purpose |
|---|---|---|
| `STORAGE` | `MemoryStorage` | In-process state store for the SDK |
| `CONNECTION_MANAGER` | `MsalConnectionManager` | MSAL-based auth for outbound calls to Bot Connector |
| `ADAPTER` | `CloudAdapter` | Handles sending/receiving activities |
| `AUTHORIZATION` | `Authorization` | Token validation pipeline |
| `AGENT_APP` | `AgentApplication` | Activity router (decorator-based) |

**Registered handlers:**

```mermaid
flowchart LR
    Activity["Incoming Activity"]
    Activity -->|type = conversationUpdate\nmembersAdded| WelcomeHandler["on_members_added\nSend greeting to new members"]
    Activity -->|type = message| MessageHandler["on_message\nStrip mention → route to agent"]
    Activity -->|unhandled exception| ErrorHandler["on_error\nLog + send fallback reply"]
```

#### Message Handler Flow (`on_message`)

```mermaid
flowchart TD
    Start([Incoming message activity])
    Strip["_strip_mention_text()\nRemove @Bot mention tokens"]
    Empty{Text empty?}
    Session["get_session_id()\nDerive thread_id"]
    ClearCmd{text == '/clear'?}
    ClearOp["clear_conversation(session_id)\nDelete PG checkpoints"]
    SendClear["send_activity: ✅ Cleared"]
    EnsureAgent["ensure_agent()\nGet/init LangGraph agent"]
    Typing["send_activity: typing indicator"]
    Stream["agent.astream_events()\nHumanMessage → LLM stream"]
    Collect["Collect on_chat_model_stream chunks"]
    Reply{Reply non-empty?}
    SendReply["send_activity(reply)"]
    Warn["Log warning: empty reply"]
    End([Done])

    Start --> Strip --> Empty
    Empty -->|yes| End
    Empty -->|no| Session --> ClearCmd
    ClearCmd -->|yes| ClearOp --> SendClear --> End
    ClearCmd -->|no| EnsureAgent --> Typing --> Stream --> Collect --> Reply
    Reply -->|yes| SendReply --> End
    Reply -->|no| Warn --> End
```

### 2.3. [agent.py](agent.py) - LangGraph Agent Lifecycle

This module owns all AI infrastructure: the Managed Identity credential, the PostgreSQL connection pool, the LangGraph checkpointer, and the compiled agent graph. Everything is initialised lazily and refreshed when the AAD token is near expiry.

#### Module-Level Singletons

| Variable | Description |
|---|---|
| `_credential` | `ManagedIdentityCredential` - single AAD credential instance |
| `_pool` | `AsyncConnectionPool` - psycopg3 async pool to PostgreSQL |
| `_checkpointer` | `AsyncPostgresSaver` - LangGraph PG checkpointer |
| `_agent` | Compiled LangGraph `StateGraph` (the ReAct agent) |
| `_token_expires_at` | Unix timestamp of the current AAD token's expiry |
| `_init_lock` | `asyncio.Lock` - prevents concurrent cold-starts |

#### `ensure_agent()` - Double-Checked Locking Pattern

This is the central initialisation function. It uses a **double-checked lock** to handle concurrent coroutines safely without over-serialising.

```mermaid
flowchart TD
    Call([ensure_agent called])
    FastCheck{"_agent exists AND\ntoken valid for >5 min?"}
    ReturnCached1["Return cached agent"]
    AcquireLock["Acquire asyncio.Lock"]
    DoubleCheck{"_agent exists AND\ntoken valid for >5 min?"}
    ReturnCached2["Return cached agent\n(another coroutine already init'd)"]
    InitCred{"_credential is None?"}
    CreateCred["Create ManagedIdentityCredential\n(UAMI_CLIENT_ID)"]
    ClosePool{"Old _pool exists?"}
    CloseOldPool["Close stale pool"]
    OpenPool["_open_pool()\nFetch AAD token → build DSN\nOpen AsyncConnectionPool"]
    SetupCP["AsyncPostgresSaver(_pool)\ncheckpointer.setup()"]
    InitModel["init_chat_model()\nazure_ai:{FOUNDRY_MODEL}"]
    BuildPrompt["ChatPromptTemplate\nsystem prompt + MessagesPlaceholder"]
    CreateAgent["create_react_agent(model, tools=[], prompt, checkpointer)"]
    Return["Return compiled agent"]

    Call --> FastCheck
    FastCheck -->|yes| ReturnCached1
    FastCheck -->|no| AcquireLock --> DoubleCheck
    DoubleCheck -->|yes| ReturnCached2
    DoubleCheck -->|no| InitCred
    InitCred -->|yes| CreateCred --> ClosePool
    InitCred -->|no| ClosePool
    ClosePool -->|yes| CloseOldPool --> OpenPool
    ClosePool -->|no| OpenPool
    OpenPool --> SetupCP --> InitModel --> BuildPrompt --> CreateAgent --> Return
```

#### Token-Aware Connection Pool (`_open_pool` / `_build_dsn`)

PostgreSQL on Azure with AAD authentication requires a **short-lived token** as the password. The pool DSN is rebuilt on every `ensure_agent()` call where the token is within 5 minutes of expiry.

```mermaid
sequenceDiagram
    participant EA as ensure_agent()
    participant BD as _build_dsn()
    participant UAMI as ManagedIdentityCredential
    participant AAD as Azure AD (OIDC)
    participant PG as Azure PostgreSQL

    EA->>BD: _build_dsn()
    BD->>UAMI: get_token("ossrdbms-aad.../.default")
    UAMI->>AAD: Managed Identity token request
    AAD-->>UAMI: JWT access token + expires_on
    UAMI-->>BD: TokenCredential
    BD-->>EA: (dsn_string, expires_at)
    EA->>PG: AsyncConnectionPool.open() using token as password
    PG-->>EA: Connection pool ready
```

#### `get_session_id()` - Conversation Scoping

Maps Teams conversation context to a stable `thread_id` used by LangGraph to isolate conversation history:

```mermaid
flowchart LR
    CT{conversation_type}
    CT -->|channel| CID["channel:{team_id}:{conv.id}"]
    CT -->|groupchat| GID["groupchat:{conv.id}"]
    CT -->|personal / other| PID["personal:{conv.id}"]
```

#### `clear_conversation()` - Reset History

Deletes all LangGraph checkpoint rows for a session from PostgreSQL:

```sql
DELETE FROM checkpoints        WHERE thread_id = <session_id>
DELETE FROM checkpoint_blobs   WHERE thread_id = <session_id>
DELETE FROM checkpoint_writes  WHERE thread_id = <session_id>
```

## 3. End-to-End Message Flow (Happy Path)

```mermaid
sequenceDiagram
    actor User as Teams User
    participant BC as Bot Connector
    participant AF as Azure Function
    participant Bot as bot.py (on_message)
    participant Ag as agent.py (ensure_agent)
    participant PG as PostgreSQL
    participant LLM as Azure AI Foundry

    User->>BC: Send message "@Bot Hello!"
    BC->>AF: POST /messages (JWT signed)
    AF->>AF: Parse JSON, create _FuncRequest
    AF->>Bot: start_agent_process → on_message
    Bot->>Bot: Strip @-mention → "Hello!"
    Bot->>Bot: get_session_id() → "personal:xxxx"
    Bot->>Ag: ensure_agent()
    alt Cold start or token expiry
        Ag->>Ag: Get AAD token, open PG pool
        Ag->>PG: checkpointer.setup()
        Ag->>Ag: init_chat_model + create_react_agent
    end
    Ag-->>Bot: compiled agent
    Bot->>BC: send_activity(typing)
    Bot->>Ag: agent.astream_events(HumanMessage("Hello!"), thread_id)
    Ag->>PG: Load prior checkpoint (conversation history)
    PG-->>Ag: Previous messages
    Ag->>LLM: Stream chat completion
    LLM-->>Ag: Token chunks (on_chat_model_stream)
    Ag->>PG: Save new checkpoint
    Ag-->>Bot: Collected reply text
    Bot->>BC: send_activity("Hi! How can I help?")
    BC->>User: Deliver reply
```

## 4. Environment Variables Reference

| Variable | Used In | Description |
|---|---|---|
| `UAMI_CLIENT_ID` | agent.py | Client ID of the User-Assigned Managed Identity |
| `POSTGRES_HOST` | agent.py | PostgreSQL server hostname |
| `POSTGRES_PORT` | agent.py | PostgreSQL port (default: `5432`) |
| `POSTGRES_DB` | agent.py | Database name |
| `POSTGRES_USER` | agent.py | AAD username for PostgreSQL |
| `POSTGRES_POOL_MAX` | agent.py | Max pool connections (default: `5`) |
| `FOUNDRY_MODEL` | agent.py | Azure AI Foundry model deployment name |
| `FOUNDRY_PROJECT_ENDPOINT` | agent.py | Azure AI Foundry project endpoint URL |
| `AGENT_SYSTEM_PROMPT` | agent.py | System prompt (default: `"You are a helpful assistant."`) |
| `AGENTS_SDK_LOG_LEVEL` | function_app.py | Log level for the Microsoft Agents SDK (default: `WARNING`) |

### 4.1. Microsoft 365 Agents SDK environment variables

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

## 5. Key Design Patterns

**Lazy singleton with double-checked locking** - `ensure_agent()` avoids re-initialising the expensive LangGraph agent on every request while remaining safe under `asyncio` concurrency.

**Token rotation without restart** - The 5-minute pre-expiry window means the pool and agent are silently rebuilt before the AAD token expires, avoiding `authentication failed` errors mid-conversation.

**Stateless Azure Function + stateful checkpointer** - The Azure Function itself is stateless and horizontally scalable. All conversation state lives in PostgreSQL, keyed by `thread_id`, so any function instance can continue any conversation.

**aiohttp shim** - `_FuncRequest` and `_CIHeaders` bridge the Azure Functions `HttpRequest` interface to what the Microsoft Agents SDK's `start_agent_process` expects from an `aiohttp` request, avoiding a hard dependency on aiohttp as the host.

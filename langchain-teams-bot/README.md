## 1. Introduction

A **Microsoft Teams** chatbot that uses **LangGraph** to run a conversational AI agent

The agent deployed as an **Azure Functions** v2 python app and uses **Managed Identity** for all authentication

### 1.1. Architecture

```
Teams user
   │  (HTTPS POST /api/messages — JWT-signed by Teams)
   ▼
Azure Function App  ───────────────────────────────────────────────────────────┐
│                                                                              │
│  function_app.py                                                             │
│  └── _FuncRequest shim ──► start_agent_process()                             │
│                                    │                                         │
│                                    ▼                                         │
│  bot/teams_bot.py            CloudAdapter (Microsoft 365 Agents SDK)         │
│  └── AGENT_APP               │  • validates incoming JWT from Teams          │
│      ├── on_members_added()  │  • calls AGENT_APP.on_turn()                  │
│      ├── on_message()  ◄─────┘                                               │
│      └── on_error()                                                          │
│          │                                                                   │
│          ▼                                                                   │
│  bot/agent.py                LangGraph react agent (create_react_agent)      │
│  └── ensure_agent()          │                                               │
│      ├── ManagedIdentityCredential ──► Azure AI Foundry model                │
│      ├── trim_messages() modifier ── limits history to MAX_HISTORY_TOKENS    │
│      └── AsyncPostgresSaver ──► Azure Database for PostgreSQL                │
│                                 (session keyed by Teams conversation.id)     │
│                                                                              │
│  System-managed identity ────► Bot App Registration (federated credential)   │
│  System-managed identity ────► Azure AI Foundry (token audience)             │
│  System-managed identity ────► Azure PostgreSQL (AAD auth, no password)      │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 1.2. Request flow (step by step)

1. The Teams client sends an activity (message, `@mention`, group-chat event, etc.) as a signed JWT POST to `https://<func-app>.azurewebsites.net/api/messages`.
2. `function_app.py` wraps the Azure Functions `HttpRequest` in a thin `_FuncRequest` shim and calls `start_agent_process()` from the Microsoft 365 Agents SDK.
3. `CloudAdapter` validates the bearer JWT against Microsoft's public keys (audience = bot client ID).
4. The SDK dispatches the activity to the matching handler in `bot/teams_bot.py` (e.g. `on_message`).
5. `on_message` strips any `@mention` text, derives a **session ID** from `activity.conversation.id`, and calls `ensure_agent()`.
6. `ensure_agent()` lazily initialises (once per worker process):
   - A **psycopg3 connection pool** authenticated via a managed-identity token for `ossrdbms-aad.database.windows.net`.
   - An **`AsyncPostgresSaver`** checkpointer that stores per-session LangGraph state.
   - An **`init_chat_model`** client pointing to the Azure AI Foundry deployment, authenticated via the same managed identity.
7. The **`trim_messages` modifier** ensures the conversation history passed to the model never exceeds `MAX_HISTORY_TOKENS`, keeping older turns but always retaining the system message and the most recent human turn(s).
8. The agent streams model events; the reply text is assembled and sent back to Teams through `context.send_activity()`.

### 1.3. Session isolation

| Teams conversation type | `thread_id` format |
|---|---|
| Personal (1:1 DM) | `personal:<conversation.id>` |
| Group chat | `groupchat:<conversation.id>` |
| Channel thread | `channel:<team_id>:<conversation.id>` |

Each value maps to an isolated LangGraph checkpoint in PostgreSQL, so histories never cross session boundaries.

### 1.4. Token / credential lifecycle

| Credential | Usage | Refresh strategy |
|---|---|---|
| `ManagedIdentityCredential` (azure-identity) | Foundry model API calls | Cached internally; refreshed automatically on near-expiry |
| PostgreSQL MI token (`ossrdbms-aad.database.windows.net`) | psycopg3 connection pool DSN | Pool is rebuilt when token is within 5 min of expiry (checked on every `ensure_agent()` call) |
| Bot connector token (Agents SDK) | Sending replies to Teams via Bot Connector | Managed by `MsalConnectionManager` with `SystemManagedIdentity` auth type |

## 2. Prerequisites

| Tool | Version |
|---|---|
| Python | 3.11+ |
| Azure Functions Core Tools | v4 |
| Azure CLI (`az`) | latest |
| Teams CLI (`teams`) | v3 preview — `npm install -g @microsoft/teams-toolkit` |

## 3. Setup

### 3.1. Create the Teams bot app

Use the Teams CLI v3 to create the App Registration and Teams app in a single command.

The `--no-secret` flag skips secret generation because the Function App's managed identity is used as a federated credential instead.

```bash
teams app create \
  --name "My LangChain Bot" \
  --azure \
  --subscription <azure-subscription-id> \
  --resource-group <resource-group> \
  --endpoint https://<func-app>.azurewebsites.net/api/messages \
  --no-secret \
  --env .env.bot
```

The command outputs:

```
CLIENT_ID=<app-registration-client-id>
TENANT_ID=<azure-ad-tenant-id>
```

Keep these values for use in [3.3. Configure Azure Database for PostgreSQL](#33-configure-azure-database-for-postgresql)

### 3.2. Configure the federated identity credential

The Function App's **system-assigned managed identity** is added as a federated credential on the bot's App Registration so it can authenticate without a stored secret.

```bash
# Obtain the managed identity's object ID
MI_OBJECT_ID=$(az functionapp identity show \
  --name <func-app-name> \
  --resource-group <resource-group> \
  --query principalId -o tsv)

# Add the federated identity credential
az ad app federated-credential create \
  --id <CLIENT_ID-from-step-1> \
  --parameters "{
    \"name\": \"func-mi-federation\",
    \"issuer\": \"https://login.microsoftonline.com/<TENANT_ID>/v2.0\",
    \"subject\": \"${MI_OBJECT_ID}\",
    \"audiences\": [\"api://AzureADTokenExchange\"]
  }"
```

> [!Note]
>
> **Why this works:**
>
> `MsalConnectionManager` with `TYPE=SystemManagedIdentity` instructs the Agents SDK to acquire a token for `api://AzureADTokenExchange` via the Function App's managed identity and exchange it for a Bot Connector service token via the federated credential.

### 3.3. Configure Azure Database for PostgreSQL

**Enable Azure AD authentication** on the server and add the managed identity as an AAD administrator or a named PostgreSQL role:

```sql
-- Run in psql as the AAD admin
SELECT * FROM pgaadauth_create_principal('<managed-identity-display-name>', false, false);
GRANT CONNECT ON DATABASE teams_bot TO "<managed-identity-display-name>";
GRANT USAGE, CREATE ON SCHEMA public TO "<managed-identity-display-name>";
```

The managed identity's display name in Azure AD (usually the Function App
name) becomes the `POSTGRES_USER` value.

### 3.4. Configure Azure AI Foundry

Assign the **Cognitive Services User** (or equivalent) role to the Function App's managed identity on the Foundry project:

```bash
az role assignment create \
  --role "Cognitive Services User" \
  --assignee <MI_OBJECT_ID> \
  --scope /subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.CognitiveServices/accounts/<foundry-account>
```

### 3.5. Deploy the Function App

```bash
# From the workspace root
pip install -r requirements.txt           # install locally for a local build
func azure functionapp publish <func-app-name> --python
```

### 3.6. Set application settings

In the Azure Portal (or via `az functionapp config appsettings set`):

| Setting | Value |
|---|---|
| `CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTID` | `CLIENT_ID` from step 1 |
| `CONNECTIONS__SERVICE_CONNECTION__SETTINGS__TENANTID` | `TENANT_ID` from step 1 |
| `CONNECTIONS__SERVICE_CONNECTION__SETTINGS__TYPE` | `SystemManagedIdentity` |
| `FOUNDRY_MODEL` | Foundry deployment name (e.g. `gpt-4o`) |
| `FOUNDRY_PROJECT_ENDPOINT` | Foundry project endpoint URL |
| `AGENT_SYSTEM_PROMPT` | System prompt text (optional) |
| `MAX_HISTORY_TOKENS` | Token budget for conversation history (default `4096`) |
| `POSTGRES_HOST` | PostgreSQL server FQDN |
| `POSTGRES_DB` | Database name |
| `POSTGRES_USER` | Managed identity display name (PostgreSQL role) |
| `POSTGRES_PORT` | `5432` (default) |
| `POSTGRES_POOL_MAX` | Max pool connections per worker (default `5`) |
| `AGENTS_SDK_LOG_LEVEL` | `WARNING` (production) / `INFO` (debug) |

### 3.7. Upload the Teams app manifest

The Teams CLI created a manifest in the current directory.  Upload it to Teams Admin Center or use the CLI:

```bash
teams app publish
```

## 4. Local development

1. Copy `local.settings.json`, fill in your values, and set `CONNECTIONS__SERVICE_CONNECTION__SETTINGS__TYPE=ClientSecret` with a temporary client secret for local testing.

2. Create a dev tunnel:

  ```bash
  devtunnel host -p 7071 --allow-anonymous
  ```

3. Update the Teams bot messaging endpoint to the tunnel URL + `/api/messages`.

4. Start the function app:

  ```bash
  func start
  ```

> [!Tip]
> 
> For local development the Agents SDK can be set to anonymous mode (no JWT validation) by setting `CONNECTIONS__SERVICE_CONNECTION__SETTINGS__ANONYMOUS_ALLOWED=True`.

## 5. Project structure

```
langchain-teams-bot/
├── function_app.py          # Azure Functions entry point (HTTP trigger)
├── bot/
│   ├── __init__.py
│   ├── agent.py             # LangGraph agent, PostgreSQL checkpointer, trim_messages
│   └── teams_bot.py         # Microsoft 365 Agents SDK setup + activity handlers
├── cli-chat-agent.py        # Original CLI agent (reference)
├── requirements.txt
├── host.json
├── local.settings.json      # Local dev settings (not committed)
└── .funcignore
```

## 6. Alternative: client-secret auth

If managed-identity federation is not suitable for your environment, generate a client secret with:

```bash
teams app auth secret create --app-id <CLIENT_ID>
```

Then set:

```
CONNECTIONS__SERVICE_CONNECTION__SETTINGS__TYPE=ClientSecret
CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTSECRET=<secret-value>
```

Store the secret in **Azure Key Vault** and reference it from app settings via the Key Vault reference syntax:

```
CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTSECRET=@Microsoft.KeyVault(SecretUri=https://...)
```

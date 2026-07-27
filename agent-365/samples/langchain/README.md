# LangChain sample agent

This is a LangChain sample agent that:
- deploys in Azure Container Apps that uses a container image built with Python dependencies
- runs from application files under `/app` mounted from Azure Files for faster development iteration
- uses Foundry for model inference
- integrates with Microsoft Agent 365 SDK for wiring of notifications, MCP tooling and observability (via Microsoft OpenTelemetry)
- integrates with Microsoft Agents SDK for HTTP hosting, authen

## 1. Overview

```mermaid
flowchart TD
    User[Message/Notification] -->|/api/messages| Host[host_agent_server.py]
    Host --> Auth[Microsoft Agents auth and token exchange]
    Host --> Obs[Microsoft OpenTelemetry]
    Host --> Agent[LangChainAgent (agent.py)]
    Agent --> LC[_create_agent]
    LC --> Foundry[Foundry model]
    Agent --> MCP[McpToolRegistrationService]
    MCP --> Adapter[langchain-mcp-adapters MultiServerMCPClient]
    Adapter --> Tools[Agent 365 MCP tool servers]
```

### 1.1. Startup flow

```mermaid
flowchart TD
    A[start_with_generic_host.py] --> B[create_and_run_host]
    B --> C[use_microsoft_opentelemetry]
    B --> D[GenericAgentHost(...)]
    D --> E[create_auth_configuration]
    D --> F[start_server(auth_config)]
    F --> G[Register routes]
    G --> H[/api/messages]
    G --> I[/api/health]
    H --> J[Dispatch to activity handlers]
```

### 1.2. Request handling flow

```mermaid
sequenceDiagram
    participant Client
    participant HTTP as aiohttp app
    participant Middleware
    participant SDK as Microsoft Agents SDK
    participant Host as GenericAgentHost
    participant Agent as LangChainAgent

    Client->>HTTP: POST /api/messages
    HTTP->>Middleware: request
    Middleware->>SDK: start_agent_process(req, agent_app, adapter)
    SDK->>Host: parse activity / dispatch
    alt message activity
        Host->>Agent: process_user_message(...)
    else installationUpdate
        Host->>Host: send welcome message
    else notification
        Host->>Agent: handle_agent_notification_activity(...)
    end
    Agent-->>Host: response text
    Host-->>Client: send_activity(...)
```

### 1.3. Auth and route mapping

```mermaid
flowchart TD
    A[Incoming request] --> B{auth_configuration present?}
    B -- Yes --> C[jwt_with_health_bypass]
    B -- No --> D[anonymous_claims]
    C --> E{path = /api/health?}
    E -- Yes --> F[allow through]
    E -- No --> G[JWT auth middleware]
    D --> H[inject anonymous claims]
    F --> I[Route handling]
    G --> I
    H --> I
    I --> J[/api/messages -> entry_point]
    I --> K[/api/health -> health]
    J --> L[activity decorators]
    L --> M[message handler]
    L --> N[installationUpdate handler]
    L --> O[notification handler]
```

## 2. Files

### 2.1. Application (`/app`)

| Path | Purpose |
| --- | --- |
| `start_with_generic_host.py` | Process entrypoint. Imports `LangChainAgent` and starts the generic host. |
| `host_agent_server.py` | Shared Microsoft Agents host.<br>Configures auth, activity handlers, notifications, typing indicators, health checks, and observability. |
| `agent.py` | LangChain implementation.<br>Creates the Azure AI Foundry chat model, builds the LangChain agent, registers MCP tools, and processes messages and notifications. |
| `mcp_tool_registration_service.py` | LangChain-specific MCP registration service that converts Agent 365 MCP server configuration into LangChain tools. |
| `agent_interface.py` | Abstract contract that hosted agent implementations must satisfy. |
| `token_manager.py` | In-memory agentic token cache and exchange helper used by observability and MCP setup. |

### 2.2. Container deployment

| Path | Purpose |
| --- | --- |
| `containerapp.yaml` | Azure Container Apps manifest template.<br>Values are substituted with `envsubst` before deployment. |
| `Dockerfile` | Multi-stage image that installs dependencies into a virtual environment and starts `start_with_generic_host.py`. |
| `pyproject.toml` | Python package dependencies for this sample. |

## 3. Key concepts

### 3.1. Runtime flow

1. Azure Container Apps starts `python start_with_generic_host.py`.
2. `create_and_run_host(LangChainAgent)` validates the implementation and initializes Microsoft OpenTelemetry with LangChain instrumentation enabled.
    - checks that the class really inherits from `AgentInterface`
    - initializes observability with Microsoft OpenTelemetry with LangChain instrumentation enabled
    - creates a `GenericAgentHost`
    - asks it for auth config via `create_auth_configuration()`
    - starts the HTTP server with `start_server(auth_config)`
3. `GenericAgentHost` loads Microsoft Agents SDK configuration from environment variables, configures MSAL service connection authentication, registers message and notification handlers, and exposes `/api/messages` and `/api/health`.
4. On startup, the host constructs `LangChainAgent`.
5. `LangChainAgent` creates an Azure AI Foundry chat model with `init_chat_model`, using the deployment named by `FOUNDRY_MODEL` and the project endpoint in `FOUNDRY_PROJECT_ENDPOINT`.
6. The agent initially starts with no tools so the host can become healthy before the first authenticated turn.
7. On the first user message or notification, `setup_mcp_servers` exchanges an agentic token, discovers configured Agent 365 MCP tool servers, converts them to LangChain tools, and recreates the LangChain agent with those tools attached.
8. User messages are processed with `self.agent.ainvoke({"messages": [{"role": "user", "content": message}]})`.
9. Responses are converted to text by `_extract_result` and sent back through Microsoft Agents SDK.

### 3.2. AgentInterface (Contract)

AgentInterface inherits from ABC (abstract base class), methods marked with `@abstractmethod` are required methods for any implementing class:
- `initialize()`
- `process_user_message(...)`
- `cleanup()`

This is the _contract_: any agent hosted by this system must expose those behaviors.

> Python doesn't enforce it as strictly as Java/C#, but instantiating a subclass that forgets one of these methods would fail.

### 3.3. Observability

Agent 365 observability is provided by Microsoft OpenTelemetry: https://github.com/microsoft/opentelemetry-distro-python/tree/main/src/microsoft/opentelemetry/a365

It is enabled just with a simple `use_microsoft_opentelemetry` ([example](https://github.com/microsoft/opentelemetry-distro-python/blob/main/samples/a365/exporter.py)):

```python
from microsoft.opentelemetry import use_microsoft_opentelemetry

use_microsoft_opentelemetry(
    enable_a365=True,
    a365_token_resolver=get_token,
    instrumentation_options={
        "langchain": {"enabled": True},
    },
)
```

The [documentation](https://github.com/microsoft/opentelemetry-distro-python/blob/main/A365_DOCUMENTATION.md) provides details on auto-instrumented libraries, baggage configuration, token resolver, etc

Microsoft OpenTelemetry replaces A365 observability and observability-extensions packages; the [migration documentation](https://github.com/microsoft/opentelemetry-distro-python/blob/main/MIGRATION_A365.md) provides more details.

### 3.4. `@web_middleware` paths

- If auth_configuration is present, the app uses `jwt_with_health_bypass`:
    - `/api/health` is allowed through
    - all other requests go through JWT authorization middleware
- If auth_configuration is absent, the app uses anonymous_claims:
    - it injects fake/anonymous claims so the request can still flow without JWT

### 3.5. MCP tool behavior

The LangChain sample includes a custom `McpToolRegistrationService` because Agent 365 tooling does not directly return LangChain tools.

During the first turn:

1. `setup_mcp_servers` prepares an observability token and calls the registration service.
2. In production mode, the registration service exchanges an MCP platform token using `auth.exchange_token`.
3. `McpToolServerConfigurationService.list_tool_servers` discovers configured Agent 365 MCP servers for this agent.
4. Each server configuration is converted to a `MultiServerMCPClient` connection with HTTP transport, URL, user-agent header, optional server headers, and bearer authorization.
5. `MultiServerMCPClient.get_tools()` loads LangChain `BaseTool` instances.
6. `LangChainAgent` recreates the LangChain agent with the discovered tool list.
7. `mcp_servers_initialized` prevents re-registering the same tools on every turn.

If no server configurations are returned, the agent continues with its initial tool list.

## 4. Required environment variables

| Variable | Required | Description |
| --- | --- | --- |
| `HOST` | Yes in container | HTTP bind host. Use `0.0.0.0` in Azure Container Apps. |
| `PORT` | Yes in container | HTTP port. The manifests use `3978`. |
| `FOUNDRY_PROJECT_ENDPOINT` | Yes | Azure AI Foundry project endpoint passed to `init_chat_model`. |
| `FOUNDRY_MODEL` | Yes | Foundry model deployment name used in `azure_ai:<deployment>`. |
| `UAMI_CLIENT_ID` | Yes | Client ID of the UAMI used by `ManagedIdentityCredential`. |
| `AUTH_HANDLER_NAME` | Required for production MCP | Set to `AGENTIC` to enable Agent 365 user authorization and token exchange. |
| `PYTHON_ENVIRONMENT` | Recommended | Set to `production` so Agent 365 tooling discovers deployed MCP tool configuration. |
| `ENABLE_OBSERVABILITY` | Recommended | Enables observability support. |
| `ENABLE_A365_OBSERVABILITY_EXPORTER` | Recommended | Enables the Agent 365 observability exporter. |
| `AGENT_PROMPT` | Optional | System instructions for the assistant. Defaults to `You are a helpful assistant.` |
| `TOKEN_REFRESH_BUFFER_SECONDS` | Optional | Number of seconds before expiry when cached tokens are treated as stale. Defaults to `300`. |
| `CONNECTIONS__SERVICE_CONNECTION__SETTINGS__*` | Yes for authenticated deployment | Microsoft Agents SDK service connection settings generated by `a365 setup all`. |
| `CONNECTIONSMAP__0__*` | Yes for authenticated deployment | Maps all service URLs to `SERVICE_CONNECTION`. |
| `AGENTAPPLICATION__USERAUTHORIZATION__HANDLERS__AGENTIC__SETTINGS__*` | Yes for Agent 365 auth | Configures agentic user authorization and Agent 365 scopes. |

### 4.1. Authentication and identity

This sample expects a user-assigned managed identity (UAMI) on the container app.

The UAMI is used for:

| Target | Required configuration |
| --- | --- |
| Azure AI Foundry | Assign `Cognitive Services User` to the Foundry account scope. |
| Azure Container Registry | Assign `AcrPull` to the registry scope. |
| Agent blueprint federated credentials | Create a federated credential on the blueprint app that trusts the UAMI principal ID. |
| Runtime model calls | Set `UAMI_CLIENT_ID` so `ManagedIdentityCredential` can authenticate the LangChain Azure AI model. |

Agentic user authorization is enabled by setting `AUTH_HANDLER_NAME=AGENTIC`. If this value is not set outside development mode, MCP registration raises an error because it cannot exchange the MCP platform token required to discover deployed tool servers.


## 5. Deployment summary

The root [README.md](../README.md) contains the full Azure resource and Agent 365 setup. At a high level:

1. Create shared resources: resource group, Foundry resource and model deployment, storage account, Container Apps environment, and Azure Container Registry.
2. Set `SAMPLE='langchain'`.
3. Create a UAMI for this agent.
4. Grant the UAMI access to Foundry and ACR.
5. Create an Azure Files share named for the app and upload the files from `app`.
6. Build the image from this folder's `Dockerfile` and `pyproject.toml`.
7. Run `a365 setup all` with the container app messaging endpoint.
8. Configure MCP tools with `a365 develop add-mcp-servers`.
9. Grant MCP permissions with `a365 setup permissions mcp`.
10. Publish the Agent 365 manifest.
11. Substitute `containerapp.yaml` with environment variables and deploy it with `az containerapp create`.

### 5.1. Troubleshooting

| Symptom | Likely cause | Check |
| --- | --- | --- |
| `/api/health` returns `agent_initialized: false` | Agent failed during startup. | Inspect container logs for import, managed identity, or Foundry errors. |
| Model calls fail with authentication errors | UAMI is missing or lacks Foundry access. | Verify `UAMI_CLIENT_ID` and the `Cognitive Services User` role assignment. |
| MCP registration raises `auth_handler_name is required outside development mode` | `AUTH_HANDLER_NAME` is unset while `PYTHON_ENVIRONMENT=production`. | Set `AUTH_HANDLER_NAME=AGENTIC` and ensure user authorization settings exist. |
| MCP tools are not available | MCP permissions or tooling configuration is missing. | Run `a365 develop list-configured` and `a365 setup permissions mcp -n $APP_NAME`. |
| LangChain tool calls fail with authorization errors | MCP server authorization header is missing or expired. | Verify token exchange succeeds and the Agent 365 authorization handler scopes are configured. |
| Container app cannot pull the image | UAMI lacks ACR pull permission or registry identity is wrong. | Verify `AcrPull` assignment and `${UAMI_RSC_ID}` in `containerapp.yaml`. |
| Health check fails in Azure Container Apps | App is not listening on the expected host or port. | Ensure `HOST=0.0.0.0`, `PORT=3978`, and ingress `targetPort` is `3978`. |

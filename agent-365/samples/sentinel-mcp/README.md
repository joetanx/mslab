# Sentinel MCP sample agent

This source-only reference hosts a LangChain agent through Microsoft Agents SDK, provides Microsoft Foundry web search, and connects directly to two Microsoft Sentinel MCP servers:

| Server | Endpoint | Delegated scope |
| --- | --- | --- |
| Data exploration | `https://sentinel.microsoft.com/mcp/data-exploration` | `4500ebfb-89b6-4b14-a480-7f749797bfcd/SentinelPlatform.DelegatedAccess` |
| Defender triage | `https://sentinel.microsoft.com/mcp/triage` | `7b7b3966-1961-47b5-b080-43ca5482e21c/MCP.Read.All` |

For each message or notification, the agent exchanges a user token for each server, loads its tools through `MultiServerMCPClient`, and recreates the LangChain agent with those tools. It also provides current-time and Foundry web-search tools, trims persisted conversation history to approximately 12,000 tokens, and keeps conversation checkpoints in memory.

Install the Foundry tools integration with the `tools` extra when packaging this source-only sample:

```sh
pip install -U "langchain-azure-ai[tools]"
```

`WebSearchTool` is a server-side built-in and requires `FOUNDRY_MODEL` to identify an OpenAI model deployed in the configured Microsoft Foundry project.

## Files

| Path | Purpose |
| --- | --- |
| `agent.py` | Foundry-backed LangChain agent, Sentinel MCP token exchange and tool setup, conversation checkpointing, and notification processing. |
| `server.py` | Microsoft Agents SDK HTTP host, authentication, Agent 365 notifications, health endpoint, and Microsoft OpenTelemetry setup. |

## Runtime flow

1. `server.py` initializes Agent 365 observability and starts `AgentHost`.
2. The host loads Microsoft Agents SDK connection configuration from environment variables and exposes `/api/messages` and `/api/health` on port `3978` by default.
3. On application startup, the host creates `LangChainAgent` with the Foundry model, current-time tool, and Foundry web-search tool.
4. For each authenticated turn, the host exchanges an observability token.
5. The agent exchanges delegated tokens for both Sentinel MCP servers and loads their tools.
6. The message or notification runs in a conversation-specific in-memory checkpoint thread.

## Required configuration

| Variable | Description |
| --- | --- |
| `FOUNDRY_PROJECT_ENDPOINT` | Azure AI Foundry project endpoint. |
| `FOUNDRY_MODEL` | Foundry model deployment name. |
| `UAMI_CLIENT_ID` | User-assigned managed identity client ID used for Foundry authentication. |
| `AUTH_HANDLER_NAME` | Agentic authorization handler used for observability and Sentinel MCP token exchange; normally `AGENTIC`. |
| `CONNECTIONS__SERVICE_CONNECTION__SETTINGS__*` | Agent blueprint service connection and federated identity settings. |
| `CONNECTIONSMAP__0__*` | Mapping from service URLs to the service connection. |
| `AGENTAPPLICATION__USERAUTHORIZATION__HANDLERS__AGENTIC__SETTINGS__*` | Agentic user authorization configuration. |
| `HOST` | Optional HTTP bind host; defaults to `localhost`. |
| `PORT` | Optional HTTP port; defaults to `3978`. |
| `AGENT_PROMPT` | Optional system instructions; defaults to `You are a helpful assistant.` |

The agent registration and signed-in user must be granted the delegated scopes listed above before the MCP token exchanges can succeed.

> [!NOTE]
>
> This folder does not currently include a `Dockerfile`, `pyproject.toml`, or `containerapp.yaml`. It is not directly deployable through the root README workflow; add equivalent packaging and Agent 365 connection settings before running it as a standalone sample.
"""MCP tool registration service for LangChain agents."""

import logging
from dataclasses import dataclass
from typing import Any, Optional

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from microsoft_agents.hosting.core import Authorization, TurnContext
from microsoft_agents_a365.runtime.utility import Utility
from microsoft_agents_a365.tooling.models import ToolOptions
from microsoft_agents_a365.tooling.services.mcp_tool_server_configuration_service import (
    McpToolServerConfigurationService,
)
from microsoft_agents_a365.tooling.utils import Constants
from microsoft_agents_a365.tooling.utils.utility import get_mcp_platform_authentication_scope
from token_cache import (
    build_token_cache_key,
    cache_token,
    get_cached_token,
    is_token_valid,
)


McpConnectionConfig = dict[str, Any]


@dataclass
class McpToolCacheEntry:
    """Cached MCP client state for a tenant, agent, and user identity."""

    client: Optional[MultiServerMCPClient]
    connections: dict[str, McpConnectionConfig]
    tools: list[BaseTool]


class McpToolRegistrationService:
    """Discover MCP servers and load their tools for LangChain."""

    _orchestrator_name = "LangChain"

    def __init__(self, logger: Optional[logging.Logger] = None) -> None:
        self._logger = logger or logging.getLogger(self.__class__.__name__)
        self._config_service = McpToolServerConfigurationService(logger=self._logger)
        self._tool_cache: dict[str, McpToolCacheEntry] = {}
        self._active_identity_key: str | None = None
        self._revision = 0

    @property
    def initialized(self) -> bool:
        """Return whether MCP discovery has already completed."""
        return self._active_identity_key is not None

    @property
    def revision(self) -> int:
        """Incremented whenever the loaded MCP tools are replaced."""
        return self._revision

    async def discover_and_load_tools(
        self,
        auth: Authorization,
        auth_handler_name: Optional[str],
        context: TurnContext,
        force_refresh: bool = False,
    ) -> list[BaseTool]:
        """Discover A365 MCP servers and load them as LangChain tools."""
        discovery_token = await self._get_mcp_discovery_token(
            auth, auth_handler_name, context, force_refresh=force_refresh
        )
        agentic_app_id = Utility.resolve_agent_identity(context, discovery_token)
        tenant_id = getattr(context.activity.recipient, "tenant_id", "") or ""
        identity_key = build_token_cache_key(
            tenant_id, agentic_app_id, self._get_user_identity(context)
        )
        cached_entry = self._tool_cache.get(identity_key)

        if (
            cached_entry
            and not force_refresh
            and self._connection_tokens_are_valid(identity_key, cached_entry.connections)
        ):
            if self._active_identity_key != identity_key:
                self._active_identity_key = identity_key
                self._revision += 1
            return list(cached_entry.tools)

        if cached_entry:
            self._logger.info(
                "Refreshing MCP tools for agent identity %s", identity_key
            )
            await self._close_entry(cached_entry)
            self._tool_cache.pop(identity_key, None)
            if self._active_identity_key == identity_key:
                self._active_identity_key = None

        server_configs = await self._config_service.list_tool_servers(
            agentic_app_id=agentic_app_id,
            auth_token=discovery_token,
            options=ToolOptions(orchestrator_name=self._orchestrator_name),
            authorization=auth,
            auth_handler_name=auth_handler_name,
            turn_context=context,
        )
        self._logger.info("Loaded %d MCP server configurations", len(server_configs))

        connections = self._build_mcp_connections(server_configs)
        if not connections:
            self._logger.info("No MCP servers configured")
            self._tool_cache[identity_key] = McpToolCacheEntry(
                client=None,
                connections={},
                tools=[],
            )
            self._active_identity_key = identity_key
            self._revision += 1
            return []

        mcp_client = MultiServerMCPClient(connections)
        tools = await mcp_client.get_tools()
        self._tool_cache[identity_key] = McpToolCacheEntry(
            client=mcp_client,
            connections=connections,
            tools=tools,
        )
        self._active_identity_key = identity_key
        self._revision += 1
        self._logger.info("Loaded %d LangChain MCP tools", len(tools))
        return list(tools)

    async def force_refresh(
        self,
        auth: Authorization,
        auth_handler_name: Optional[str],
        context: TurnContext,
    ) -> list[BaseTool]:
        """Discard cached MCP connections and load tools with fresh auth headers."""
        return await self.discover_and_load_tools(
            auth, auth_handler_name, context, force_refresh=True
        )

    async def _get_mcp_discovery_token(
        self,
        auth: Authorization,
        auth_handler_name: Optional[str],
        context: TurnContext,
        force_refresh: bool = False,
    ) -> Optional[str]:
        """Get the shared discovery token used to list A365 MCP servers."""
        if not auth_handler_name:
            raise ValueError("auth_handler_name is required for production MCP discovery")

        scope = get_mcp_platform_authentication_scope()
        cache_key = build_token_cache_key(
            "mcp-discovery",
            getattr(context.activity.recipient, "tenant_id", ""),
            getattr(context.activity.recipient, "agentic_app_id", ""),
            self._get_user_identity(context),
            self._normalize_scope(scope),
        )
        if not force_refresh:
            cached_token = get_cached_token(cache_key)
            if cached_token:
                return cached_token

        token_result = await auth.exchange_token(
            context,
            scope,
            auth_handler_name,
        )
        if token_result is None or not token_result.token:
            raise ValueError("Failed to obtain token for MCP server discovery")

        cache_token(cache_key, token_result.token)
        return token_result.token

    def _build_mcp_connections(self, server_configs) -> dict[str, McpConnectionConfig]:
        """Convert A365 server configs to langchain-mcp-adapters configs."""
        mcp_connections: dict[str, McpConnectionConfig] = {}

        for config in server_configs:
            server_name = config.mcp_server_name or config.mcp_server_unique_name
            if not config.url:
                self._logger.warning(
                    "Skipping MCP server '%s' without URL", server_name
                )
                continue

            headers = {
                Constants.Headers.USER_AGENT: Utility.get_user_agent_header(
                    self._orchestrator_name
                )
            }
            if config.headers:
                headers.update(config.headers)

            mcp_connections[server_name] = {
                "transport": "http",
                "url": config.url,
                "headers": headers,
            }

        return mcp_connections

    def _connection_tokens_are_valid(
        self, identity_key: str, connections: dict[str, McpConnectionConfig]
    ) -> bool:
        """Check cached MCP connection bearer tokens before reusing tools."""
        for server_name, connection in connections.items():
            headers = connection.get("headers") or {}
            authorization = self._get_header(headers, "authorization")
            if not authorization:
                continue

            scheme, _, token = authorization.partition(" ")
            if scheme.lower() != "bearer" or not token:
                continue

            if not is_token_valid(token):
                self._logger.info(
                    "Cached MCP token for identity '%s' server '%s' is expired or near expiry",
                    identity_key,
                    server_name,
                )
                return False

        return True

    def _get_header(self, headers: dict[str, Any], name: str) -> str | None:
        for header_name, header_value in headers.items():
            if header_name.lower() == name:
                return str(header_value)
        return None

    def get_available_server_names(self) -> list[str]:
        """Get names for the MCP servers registered with LangChain."""
        entry = self._get_active_entry()
        return list(entry.connections.keys()) if entry else []

    def _get_active_entry(self) -> McpToolCacheEntry | None:
        if not self._active_identity_key:
            return None
        return self._tool_cache.get(self._active_identity_key)

    def _get_user_identity(self, context: TurnContext) -> str:
        from_property = getattr(context.activity, "from_property", None)
        if not from_property:
            return ""
        return (
            getattr(from_property, "aad_object_id", None)
            or getattr(from_property, "id", None)
            or ""
        )

    def _normalize_scope(self, scope: Any) -> str:
        if isinstance(scope, (list, tuple, set)):
            return " ".join(str(item) for item in scope)
        return str(scope or "")

    async def _close_entry(self, entry: McpToolCacheEntry) -> None:
        if not entry.client:
            return

        close = getattr(entry.client, "aclose", None) or getattr(entry.client, "close", None)
        if close:
            result = close()
            if hasattr(result, "__await__"):
                await result

    async def cleanup(self) -> None:
        """Clean up MCP client resources."""
        for entry in self._tool_cache.values():
            await self._close_entry(entry)

        self._tool_cache = {}
        self._active_identity_key = None
        self._logger.info("MCP tool registration service cleaned up")

# Copyright (c) Microsoft. All rights reserved.

"""
MCP tool registration service for LangChain agents.

Discovers Agent 365 MCP servers through the A365 tooling SDK, converts those
servers into langchain-mcp-adapters connection definitions, and exposes the
loaded LangChain tools to the agent.
"""

import logging
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
from microsoft_agents_a365.tooling.utils.utility import (
    get_mcp_platform_authentication_scope,
    is_development_environment,
)


McpConnectionConfig: str = dict[str, Any]


class McpToolRegistrationService:
    """Discover MCP servers and load their tools for LangChain."""

    _orchestrator_name = "LangChain"

    def __init__(self, logger: Optional[logging.Logger] = None) -> None:
        self._logger = logger or logging.getLogger(self.__class__.__name__)
        self._config_service = McpToolServerConfigurationService(logger=self._logger)
        self._mcp_client: Optional[MultiServerMCPClient] = None
        self._mcp_connections: dict[str, McpConnectionConfig] = {}
        self._tools: list[BaseTool] = []
        self._initialized = False

    @property
    def initialized(self) -> bool:
        """Return whether MCP discovery has already completed."""
        return self._initialized

    async def discover_and_load_tools(
        self,
        auth: Authorization,
        auth_handler_name: Optional[str],
        context: TurnContext,
    ) -> list[BaseTool]:
        """Discover A365 MCP servers and load them as LangChain tools."""
        if self._initialized:
            return list(self._tools)

        discovery_token = await self._get_mcp_discovery_token(
            auth, auth_handler_name, context
        )
        agentic_app_id = (
            ""
            if is_development_environment()
            else Utility.resolve_agent_identity(context, discovery_token)
        )

        server_configs = await self._config_service.list_tool_servers(
            agentic_app_id=agentic_app_id,
            auth_token=discovery_token,
            options=ToolOptions(orchestrator_name=self._orchestrator_name),
            authorization=auth,
            auth_handler_name=auth_handler_name,
            turn_context=context,
        )
        self._logger.info("Loaded %d MCP server configurations", len(server_configs))

        self._mcp_connections = self._build_mcp_connections(server_configs)
        if not self._mcp_connections:
            self._logger.info("No MCP servers configured")
            self._initialized = True
            return []

        self._mcp_client = MultiServerMCPClient(self._mcp_connections)
        self._tools = await self._mcp_client.get_tools()
        self._initialized = True
        self._logger.info("Loaded %d LangChain MCP tools", len(self._tools))
        return list(self._tools)

    async def _get_mcp_discovery_token(
        self,
        auth: Authorization,
        auth_handler_name: Optional[str],
        context: TurnContext,
    ) -> Optional[str]:
        """Get the shared discovery token used to list A365 MCP servers."""
        if is_development_environment():
            return None

        if not auth_handler_name:
            raise ValueError("auth_handler_name is required for production MCP discovery")

        token_result = await auth.exchange_token(
            context,
            get_mcp_platform_authentication_scope(),
            auth_handler_name,
        )
        if token_result is None or not token_result.token:
            raise ValueError("Failed to obtain token for MCP server discovery")

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

    def get_available_server_names(self) -> list[str]:
        """Get names for the MCP servers registered with LangChain."""
        return list(self._mcp_connections.keys())

    async def cleanup(self) -> None:
        """Clean up MCP client resources."""
        if self._mcp_client:
            close = getattr(self._mcp_client, "aclose", None) or getattr(
                self._mcp_client, "close", None
            )
            if close:
                result = close()
                if hasattr(result, "__await__"):
                    await result

        self._mcp_client = None
        self._mcp_connections = {}
        self._tools = []
        self._initialized = False
        self._logger.info("MCP tool registration service cleaned up")

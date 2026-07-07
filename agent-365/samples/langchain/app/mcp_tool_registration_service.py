"""LangChain MCP tool registration backed by Microsoft Agent 365 tooling."""

from __future__ import annotations

import logging
from typing import Optional

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from microsoft_agents.hosting.core import Authorization, TurnContext
from microsoft_agents_a365.runtime.utility import Utility
from microsoft_agents_a365.tooling.models import ToolOptions
from microsoft_agents_a365.tooling.services.mcp_tool_server_configuration_service import (
    McpToolServerConfigurationService,
)
from microsoft_agents_a365.tooling.utils.constants import Constants
from microsoft_agents_a365.tooling.utils.utility import (
    get_mcp_platform_authentication_scope,
    is_development_environment,
)


class McpToolRegistrationService:
    """Loads Agent 365 MCP server registrations as LangChain tools."""

    _orchestrator_name = "LangChain"

    def __init__(self, logger: Optional[logging.Logger] = None):
        """Create the registration service and its core configuration service."""
        self._logger = logger or logging.getLogger(self.__class__.__name__)
        self._mcp_server_configuration_service = McpToolServerConfigurationService(
            logger=self._logger
        )
        self._mcp_client: MultiServerMCPClient | None = None

    async def add_tool_servers_to_agent(
        self,
        initial_tools: list[BaseTool],
        auth: Authorization,
        auth_handler_name: str | None,
        turn_context: TurnContext,
        auth_token: Optional[str] = None,
    ) -> list[BaseTool]:
        """
        Return initial tools plus LangChain tools discovered from Agent 365 MCP servers.

        The method intentionally mirrors the Agent Framework extension's entrypoint,
        but returns a list suitable for LangChain's ``create_agent(..., tools=...)``.
        """
        is_dev = is_development_environment()
        if not auth_token and not is_dev:
            if not auth_handler_name:
                raise ValueError("auth_handler_name is required outside development mode")
            token_result = await auth.exchange_token(
                turn_context,
                get_mcp_platform_authentication_scope(),
                auth_handler_name,
            )
            if token_result is None or not token_result.token:
                raise ValueError("Token exchange did not return an MCP platform token")
            auth_token = token_result.token

        agentic_app_id = (
            "" if is_dev else Utility.resolve_agent_identity(turn_context, auth_token)
        )
        options = ToolOptions(orchestrator_name=self._orchestrator_name)
        server_configs = await self._mcp_server_configuration_service.list_tool_servers(
            agentic_app_id=agentic_app_id,
            auth_token=auth_token,
            options=options,
            authorization=auth,
            auth_handler_name=auth_handler_name,
            turn_context=turn_context,
        )
        self._logger.info("Loaded %d MCP server configurations", len(server_configs))

        server_connections: dict[str, dict[str, object]] = {}
        for config in server_configs:
            server_name = config.mcp_server_name or config.mcp_server_unique_name
            headers = self._build_server_headers(config.headers, auth_token)
            server_connections[server_name] = {
                "transport": "http",
                "url": config.url,
                "headers": headers,
            }
            self._logger.info("Configured MCP server '%s' at %s", server_name, config.url)

        if not server_connections:
            return list(initial_tools)

        self._mcp_client = MultiServerMCPClient(server_connections)
        mcp_tools = await self._mcp_client.get_tools()
        self._logger.info("Loaded %d LangChain MCP tools", len(mcp_tools))
        return [*initial_tools, *mcp_tools]

    def _build_server_headers(
        self,
        server_headers: dict[str, str] | None,
        auth_token: Optional[str],
    ) -> dict[str, str]:
        """Build HTTP headers for LangChain MCP adapter server connections."""
        headers = {
            Constants.Headers.USER_AGENT: Utility.get_user_agent_header(
                self._orchestrator_name
            )
        }
        if server_headers:
            headers.update(server_headers)

        if Constants.Headers.AUTHORIZATION not in headers and auth_token:
            headers[Constants.Headers.AUTHORIZATION] = (
                auth_token
                if auth_token.lower().startswith(
                    f"{Constants.Headers.BEARER_PREFIX.lower()} "
                )
                else f"{Constants.Headers.BEARER_PREFIX} {auth_token}"
            )

        return headers

    async def cleanup(self) -> None:
        """Release resources created by the LangChain MCP adapter if supported."""
        if self._mcp_client is None:
            return
        close = getattr(self._mcp_client, "aclose", None)
        if close is not None:
            await close()

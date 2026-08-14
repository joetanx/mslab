"""LangChain MCP tool registration backed by Microsoft Agent 365 tooling."""

from __future__ import annotations

import logging

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from microsoft_agents.hosting.core import Authorization, TurnContext
from microsoft_agents_a365.runtime.utility import Utility
from microsoft_agents_a365.tooling.models import ToolOptions
from microsoft_agents_a365.tooling.services.mcp_tool_server_configuration_service import McpToolServerConfigurationService
from microsoft_agents_a365.tooling.utils.constants import Constants
from microsoft_agents_a365.tooling.utils.utility import get_mcp_platform_authentication_scope


class McpToolRegistrationService:
    """Convert Agent 365 MCP server registrations into LangChain tools."""

    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)
        self.config_service = McpToolServerConfigurationService(logger=self.logger)
        self.client: MultiServerMCPClient | None = None

    async def get_tools_from_mcp_servers(
        self,
        auth: Authorization,
        auth_handler_name: str | None,
        turn_context: TurnContext,
    ) -> list[BaseTool]:
        """Return the existing tools plus tools discovered from Agent 365."""
        auth_token = (await auth.exchange_token(
            turn_context,
            get_mcp_platform_authentication_scope(),
            auth_handler_name,
        )).token
        server_configs = await self.config_service.list_tool_servers(
            agentic_app_id=Utility.resolve_agent_identity(turn_context, auth_token),
            auth_token=auth_token,
            options=ToolOptions(orchestrator_name="LangChain"),
            authorization=auth,
            auth_handler_name=auth_handler_name,
            turn_context=turn_context,
        )

        connections: dict[str, dict[str, object]] = {}
        for config in server_configs:
            name = config.mcp_server_name or config.mcp_server_unique_name
            connections[name] = {
                "transport": "http",
                "url": config.url,
                "headers": self._build_headers(config.headers, auth_token),
            }

        if not connections:
            return []

        self.client = MultiServerMCPClient(connections)
        mcp_tools = await self.client.get_tools()
        self.logger.info("Loaded %d LangChain MCP tools", len(mcp_tools))
        return mcp_tools

    def _build_headers(
        self,
        server_headers: dict[str, str] | None,
        auth_token: str | None,
    ) -> dict[str, str]:
        headers = {
            Constants.Headers.USER_AGENT: Utility.get_user_agent_header("LangChain")
        }
        headers.update(server_headers or {})

        if Constants.Headers.AUTHORIZATION not in headers and auth_token:
            prefix = Constants.Headers.BEARER_PREFIX
            headers[Constants.Headers.AUTHORIZATION] = auth_token
            if not auth_token.lower().startswith(f"{prefix.lower()} "):
                headers[Constants.Headers.AUTHORIZATION] = f"{prefix} {auth_token}"

        return headers

    async def cleanup(self) -> None:
        """Close the MCP client if this adapter version supports it."""
        close = getattr(self.client, "aclose", None)
        if close:
            await close()

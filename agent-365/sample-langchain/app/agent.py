# Copyright (c) Microsoft. All rights reserved.

"""
LangChain Agent with MCP Server Integration and Observability

This agent uses LangChain's create_react_agent and connects to MCP servers for extended
functionality, with integrated observability using Microsoft Agent 365.

Features:
- LangChain create_react_agent with init_chat_model for unified model interface
- MCP server integration via McpToolServerConfigurationService + langchain_mcp
- Simplified observability setup following reference examples pattern
- Token-based authentication for Agent 365 Observability
- Comprehensive error handling and cleanup
"""

import asyncio
import logging
from os import environ
from typing import Optional

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =============================================================================
# DEPENDENCY IMPORTS
# =============================================================================
# <DependencyImports>

# LangChain
from langchain.chat_models import init_chat_model
from langchain_mcp import load_mcp_tools, StreamableHTTPClient
from langgraph.prebuilt import create_react_agent

# Agent Interface
from agent_interface import AgentInterface
from azure.identity.aio import ManagedIdentityCredential

# Microsoft Agents SDK
from local_authentication_options import LocalAuthenticationOptions
from microsoft_agents.hosting.core import Authorization, TurnContext

# Notifications
from microsoft_agents_a365.notifications.agent_notification import NotificationTypes

# Observability Components
# Auto-instrumentation is handled by the microsoft-opentelemetry
# distro (see host_agent_server.py). No manual instrumentor setup is needed.

# MCP Tooling (main library - no framework-specific extensions)
from microsoft_agents_a365.tooling import McpToolServerConfigurationService
from microsoft_agents_a365.tooling.models import ToolOptions
from token_cache import get_cached_agentic_token

# </DependencyImports>


class LangChainAgent(AgentInterface):
    """LangChain Agent integrated with MCP servers and Observability"""

    AGENT_PROMPT = environ.get("AGENT_PROMPT", "You are a helpful assistant.")

    # =========================================================================
    # INITIALIZATION
    # =========================================================================
    # <Initialization>

    def __init__(self):
        """Initialize the LangChain agent."""
        self.logger = logging.getLogger(self.__class__.__name__)

        # Initialize authentication options
        self.auth_options = LocalAuthenticationOptions.from_environment()

        # Create the chat model using init_chat_model for a unified interface
        self._create_chat_model()

        # Create the agent with initial configuration (no tools yet)
        self._create_agent()

        # Initialize MCP services
        self._initialize_services()

        # Track if MCP servers have been set up
        self.mcp_servers_initialized = False

        # Track active MCP clients for cleanup
        self._mcp_clients: list[StreamableHTTPClient] = []

    # </Initialization>

    # =========================================================================
    # CLIENT AND AGENT CREATION
    # =========================================================================
    # <ClientCreation>

    def _create_chat_model(self):
        """Create the chat model using init_chat_model for a unified interface"""
        self.model = init_chat_model(
            f"azure_ai:{environ['FOUNDRY_MODEL']}",
            project_endpoint=environ['FOUNDRY_PROJECT_ENDPOINT'],
            credential=ManagedIdentityCredential(client_id=environ.get("UAMI_CLIENT_ID")),
        )
        logger.info(f"✅ Chat model initialized: {environ['FOUNDRY_MODEL']}")

    def _create_agent(self):
        """Create the LangChain agent with initial configuration"""
        try:
            self.agent = create_react_agent(
                model=self.model,
                tools=[],
                prompt=self.AGENT_PROMPT,
            )
            logger.info("✅ LangChain agent created")
        except Exception as e:
            logger.error(f"Failed to create agent: {e}")
            raise

    # </ClientCreation>

    # =========================================================================
    # MCP SERVER SETUP AND INITIALIZATION
    # =========================================================================
    # <McpServerSetup>

    def _initialize_services(self):
        """Initialize MCP services"""
        try:
            self.tool_service = McpToolServerConfigurationService()
            logger.info("✅ MCP tool configuration service initialized")
        except Exception as e:
            logger.warning(f"⚠️ MCP tool configuration service failed: {e}")
            self.tool_service = None

    async def setup_mcp_servers(self, auth: Authorization, auth_handler_name: Optional[str], context: TurnContext):
        """Set up MCP server connections and rebuild the agent with discovered tools"""
        if self.mcp_servers_initialized:
            return

        try:
            if not self.tool_service:
                logger.warning("⚠️ MCP tool configuration service unavailable")
                return

            # Determine auth token
            use_agentic_auth = environ.get("USE_AGENTIC_AUTH", "false").lower() == "true"
            if use_agentic_auth:
                tenant_id = context.activity.recipient.tenant_id
                agent_id = context.activity.recipient.agentic_app_id
                auth_token = get_cached_agentic_token(tenant_id, agent_id) or ""
            else:
                auth_token = self.auth_options.bearer_token

            # Discover MCP tool servers
            agentic_app_id = context.activity.recipient.agentic_app_id or ""
            servers = await self.tool_service.list_tool_servers(
                agentic_app_id=agentic_app_id,
                auth_token=auth_token,
                options=ToolOptions(orchestrator_name="LangChain"),
            )

            if not servers:
                logger.info("No MCP tool servers discovered")
                self.mcp_servers_initialized = True
                return

            # Load tools from each MCP server using langchain_mcp
            all_tools = []
            for server in servers:
                try:
                    client = StreamableHTTPClient(
                        base_url=server.mcp_server_unique_name,
                        api_key=auth_token,
                    )
                    tools = load_mcp_tools(client)
                    all_tools.extend(tools)
                    self._mcp_clients.append(client)
                    logger.info(f"✅ Loaded tools from MCP server: {server.mcp_server_name}")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to load tools from {server.mcp_server_name}: {e}")

            # Rebuild agent with discovered tools
            if all_tools:
                self.agent = create_react_agent(
                    model=self.model,
                    tools=all_tools,
                    prompt=self.AGENT_PROMPT,
                )
                logger.info(f"✅ Agent rebuilt with {len(all_tools)} MCP tools")

            self.mcp_servers_initialized = True
            logger.info("✅ MCP setup completed")

        except Exception as e:
            logger.error(f"MCP setup error: {e}")

    # </McpServerSetup>

    # =========================================================================
    # MESSAGE PROCESSING
    # =========================================================================
    # <MessageProcessing>

    async def initialize(self):
        """Initialize the agent"""
        logger.info("Agent initialized")

    async def process_user_message(
        self, message: str, auth: Authorization, auth_handler_name: Optional[str], context: TurnContext
    ) -> str:
        """Process user message using LangChain create_react_agent"""
        # Log the user identity from activity.from_property
        from_prop = context.activity.from_property
        logger.info(
            "Turn received from user — DisplayName: '%s', UserId: '%s', AadObjectId: '%s'",
            getattr(from_prop, "name", None) or "(unknown)",
            getattr(from_prop, "id", None) or "(unknown)",
            getattr(from_prop, "aad_object_id", None) or "(none)",
        )

        try:
            await self.setup_mcp_servers(auth, auth_handler_name, context)
            result = await asyncio.to_thread(
                self.agent.invoke,
                {"messages": [{"role": "user", "content": message}]},
            )
            return self._extract_result(result) or "I couldn't process your request at this time."
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return f"Sorry, I encountered an error: {str(e)}"

    # </MessageProcessing>

    # =========================================================================
    # NOTIFICATION HANDLING
    # =========================================================================
    # <NotificationHandling>

    async def handle_agent_notification_activity(
        self, notification_activity, auth: Authorization, auth_handler_name: Optional[str], context: TurnContext
    ) -> str:
        """Handle agent notification activities (email, Word mentions, etc.)"""
        try:
            notification_type = notification_activity.notification_type
            logger.info(f"📬 Processing notification: {notification_type}")

            # Setup MCP servers on first call
            await self.setup_mcp_servers(auth, auth_handler_name, context)

            # Handle Email Notifications
            if notification_type == NotificationTypes.EMAIL_NOTIFICATION:
                if not hasattr(notification_activity, "email") or not notification_activity.email:
                    return "I could not find the email notification details."

                email = notification_activity.email
                email_body = getattr(email, "html_body", "") or getattr(email, "body", "")
                message = f"You have received the following email. Please follow any instructions in it. {email_body}"

                result = await asyncio.to_thread(
                    self.agent.invoke,
                    {"messages": [{"role": "user", "content": message}]},
                )
                return self._extract_result(result) or "Email notification processed."

            # Handle Word Comment Notifications
            elif notification_type == NotificationTypes.WPX_COMMENT:
                if not hasattr(notification_activity, "wpx_comment") or not notification_activity.wpx_comment:
                    return "I could not find the Word notification details."

                wpx = notification_activity.wpx_comment
                doc_id = getattr(wpx, "document_id", "")
                comment_id = getattr(wpx, "initiating_comment_id", "")
                drive_id = "default"

                # Get Word document content
                doc_message = f"You have a new comment on the Word document with id '{doc_id}', comment id '{comment_id}', drive id '{drive_id}'. Please retrieve the Word document as well as the comments and return it in text format."
                doc_result = await asyncio.to_thread(
                    self.agent.invoke,
                    {"messages": [{"role": "user", "content": doc_message}]},
                )
                word_content = self._extract_result(doc_result)

                # Process the comment with document context
                comment_text = notification_activity.text or ""
                response_message = f"You have received the following Word document content and comments. Please refer to these when responding to comment '{comment_text}'. {word_content}"
                result = await asyncio.to_thread(
                    self.agent.invoke,
                    {"messages": [{"role": "user", "content": response_message}]},
                )
                return self._extract_result(result) or "Word notification processed."

            # Generic notification handling
            else:
                notification_message = notification_activity.text or f"Notification received: {notification_type}"
                result = await asyncio.to_thread(
                    self.agent.invoke,
                    {"messages": [{"role": "user", "content": notification_message}]},
                )
                return self._extract_result(result) or "Notification processed successfully."

        except Exception as e:
            logger.error(f"Error processing notification: {e}")
            return f"Sorry, I encountered an error processing the notification: {str(e)}"

    def _extract_result(self, result) -> str:
        """Extract text content from LangChain agent result"""
        if not result:
            return ""
        # LangChain create_react_agent returns a dict with "messages" key
        if isinstance(result, dict) and "messages" in result:
            messages = result["messages"]
            # Get the last AI message content
            for msg in reversed(messages):
                if hasattr(msg, "content") and msg.content:
                    return str(msg.content)
                elif isinstance(msg, dict) and msg.get("content"):
                    return str(msg["content"])
        if hasattr(result, "content"):
            return str(result.content)
        return str(result)

    # </NotificationHandling>

    # =========================================================================
    # CLEANUP
    # =========================================================================
    # <Cleanup>

    async def cleanup(self) -> None:
        """Clean up agent resources"""
        try:
            for client in self._mcp_clients:
                try:
                    await client.close()
                except Exception:
                    pass
            self._mcp_clients.clear()
            logger.info("Agent cleanup completed")
        except Exception as e:
            logger.error(f"Cleanup error: {e}")

    # </Cleanup>

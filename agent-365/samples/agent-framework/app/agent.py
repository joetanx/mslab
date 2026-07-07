"""Implements an Agent Framework-backed assistant with MCP tool support."""

import asyncio
import logging
from os import environ
from typing import Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from agent_framework import Agent
from agent_framework.foundry import FoundryChatClient
from agent_interface import AgentInterface
from azure.identity import ManagedIdentityCredential
from microsoft_agents.hosting.core import Authorization, TurnContext
from microsoft_agents_a365.notifications.agent_notification import NotificationTypes
from microsoft_agents_a365.tooling.extensions.agentframework.services.mcp_tool_registration_service import (
    McpToolRegistrationService,
)
from microsoft.opentelemetry.a365.runtime import get_observability_authentication_scope
from token_manager import get_token


class AgentFrameworkAgent(AgentInterface):
    """Runs user messages and notifications through the Agent Framework runtime."""

    AGENT_PROMPT = environ.get("AGENT_PROMPT", "You are a helpful assistant.")

    def __init__(self):
        """Create the chat client, agent, and supporting services."""
        self.logger = logging.getLogger(self.__class__.__name__)
        self._create_chat_client()
        self._create_agent()
        self._initialize_services()
        self.mcp_servers_initialized = False

    def _create_chat_client(self):
        """Create the Foundry chat client used by the agent."""
        self.chat_client = FoundryChatClient(credential=ManagedIdentityCredential(client_id=environ.get("UAMI_CLIENT_ID")))
        logger.info("✅ FoundryChatClient created")

    def _create_agent(self):
        """Create the Agent Framework agent instance."""
        try:
            self.agent = Agent(
                client=self.chat_client,
                instructions=self.AGENT_PROMPT,
                tools=[],
            )
            logger.info("✅ AgentFramework agent created")
        except Exception as e:
            logger.error(f"Failed to create agent: {e}")
            raise

    def _initialize_services(self):
        """Initialize optional services used to register MCP tools."""
        try:
            self.tool_service = McpToolRegistrationService()
            logger.info("✅ MCP tool service initialized")
        except Exception as e:
            logger.warning(f"⚠️ MCP tool service failed: {e}")
            self.tool_service = None

    async def setup_mcp_servers(self, auth: Authorization, auth_handler_name: Optional[str], context: TurnContext):
        """Attach configured MCP tool servers to the agent once per process."""
        if self.mcp_servers_initialized:
            return

        try:
            if not self.tool_service:
                logger.warning("⚠️ MCP tool service unavailable")
                return

            tenant_id = getattr(context.activity.recipient, "tenant_id", None)
            agent_id = getattr(context.activity.recipient, "agentic_app_id", None)
            await get_token(
                agent_id=agent_id,
                tenant_id=tenant_id,
                auth=auth,
                auth_handler_name=auth_handler_name,
                context=context,
                scopes=get_observability_authentication_scope(),
            )

            self.agent = await self.tool_service.add_tool_servers_to_agent(
                chat_client=self.chat_client,
                agent_instructions=self.AGENT_PROMPT,
                initial_tools=[],
                auth=auth,
                auth_handler_name=auth_handler_name,
                turn_context=context,
            )

            if self.agent:
                logger.info("✅ MCP setup completed")
                self.mcp_servers_initialized = True
            else:
                logger.warning("⚠️ MCP setup failed")

        except Exception as e:
            logger.error(f"MCP setup error: {e}")

    async def initialize(self):
        """Log that the agent has completed startup initialization."""
        logger.info("Agent initialized")

    async def process_user_message(
        self, message: str, auth: Authorization, auth_handler_name: Optional[str], context: TurnContext
    ) -> str:
        """Run a user message through the agent and return its response."""
        from_prop = context.activity.from_property
        logger.info(
            "Turn received from user — DisplayName: '%s', UserId: '%s', AadObjectId: '%s'",
            getattr(from_prop, "name", None) or "(unknown)",
            getattr(from_prop, "id", None) or "(unknown)",
            getattr(from_prop, "aad_object_id", None) or "(none)",
        )

        try:
            await self.setup_mcp_servers(auth, auth_handler_name, context)
            result = await self.agent.run(message)
            return self._extract_result(result) or "I couldn't process your request at this time."
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return f"Sorry, I encountered an error: {str(e)}"

    async def handle_agent_notification_activity(
        self, notification_activity, auth: Authorization, auth_handler_name: Optional[str], context: TurnContext
    ) -> str:
        """Process a Microsoft 365 notification activity through the agent."""
        try:
            notification_type = notification_activity.notification_type
            logger.info(f"📬 Processing notification: {notification_type}")

            await self.setup_mcp_servers(auth, auth_handler_name, context)

            if notification_type == NotificationTypes.EMAIL_NOTIFICATION:
                if not hasattr(notification_activity, "email") or not notification_activity.email:
                    return "I could not find the email notification details."

                email = notification_activity.email
                email_body = getattr(email, "html_body", "") or getattr(email, "body", "")
                message = f"You have received the following email. Please follow any instructions in it. {email_body}"

                result = await self.agent.run(message)
                return self._extract_result(result) or "Email notification processed."

            elif notification_type == NotificationTypes.WPX_COMMENT:
                if not hasattr(notification_activity, "wpx_comment") or not notification_activity.wpx_comment:
                    return "I could not find the Word notification details."

                wpx = notification_activity.wpx_comment
                doc_id = getattr(wpx, "document_id", "")
                comment_id = getattr(wpx, "initiating_comment_id", "")
                drive_id = "default"

                doc_message = f"You have a new comment on the Word document with id '{doc_id}', comment id '{comment_id}', drive id '{drive_id}'. Please retrieve the Word document as well as the comments and return it in text format."
                doc_result = await self.agent.run(doc_message)
                word_content = self._extract_result(doc_result)

                comment_text = notification_activity.text or ""
                response_message = f"You have received the following Word document content and comments. Please refer to these when responding to comment '{comment_text}'. {word_content}"
                result = await self.agent.run(response_message)
                return self._extract_result(result) or "Word notification processed."

            else:
                notification_message = notification_activity.text or f"Notification received: {notification_type}"
                result = await self.agent.run(notification_message)
                return self._extract_result(result) or "Notification processed successfully."

        except Exception as e:
            logger.error(f"Error processing notification: {e}")
            return f"Sorry, I encountered an error processing the notification: {str(e)}"

    def _extract_result(self, result) -> str:
        """Convert an agent run result object into response text."""
        if not result:
            return ""
        if hasattr(result, "contents"):
            return str(result.contents)
        elif hasattr(result, "text"):
            return str(result.text)
        elif hasattr(result, "content"):
            return str(result.content)
        else:
            return str(result)

    async def cleanup(self) -> None:
        """Release services created by the agent."""
        try:
            if hasattr(self, "tool_service") and self.tool_service:
                await self.tool_service.cleanup()
            logger.info("Agent cleanup completed")
        except Exception as e:
            logger.error(f"Cleanup error: {e}")

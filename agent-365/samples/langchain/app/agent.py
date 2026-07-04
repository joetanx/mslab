# Copyright (c) Microsoft. All rights reserved.

"""
LangChain Agent with MCP Server Integration and Observability

This agent uses LangChain's create_agent API, initializes chat models through
LangChain's provider-neutral init_chat_model helper, and loads A365 MCP servers
through the core A365 tooling package plus the official langchain-mcp-adapters
library.
"""

import logging
from os import environ
from typing import Optional

from azure.identity.aio import ManagedIdentityCredential
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

# Agent Interface
from agent_interface import AgentInterface
from mcp_tool_registration_service import McpToolRegistrationService

from microsoft_agents.hosting.core import Authorization, TurnContext

# Notifications
from microsoft_agents_a365.notifications.agent_notification import NotificationTypes

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LangChainAgent(AgentInterface):
    """LangChain agent integrated with A365 MCP servers and observability."""

    AGENT_PROMPT = environ.get("AGENT_PROMPT", "You are a helpful assistant.")

    def __init__(self):
        """Initialize the LangChain agent."""
        self.logger = logging.getLogger(self.__class__.__name__)

        self.model = self._create_model()
        self.agent = self._create_agent([])
        self.mcp_service = McpToolRegistrationService(logger=self.logger)

    def _create_model(self):
        """Create a LangChain chat model using init_chat_model."""
        model = init_chat_model(
            f"azure_ai:{environ['FOUNDRY_MODEL']}",
            project_endpoint=environ['FOUNDRY_PROJECT_ENDPOINT'],
            credential=ManagedIdentityCredential(client_id=environ['UAMI_CLIENT_ID'])
        )
        logger.info("✅ LangChain chat model created")
        return model

    def _create_agent(self, tools):
        """Create the LangChain agent graph."""
        agent = create_agent(
            model=self.model,
            tools=tools,
            system_prompt=self.AGENT_PROMPT,
        )
        logger.info("✅ LangChain agent created with %d tools", len(tools))
        return agent

    async def setup_mcp_servers(
        self,
        auth: Authorization,
        auth_handler_name: Optional[str],
        context: TurnContext,
    ) -> None:
        """Discover A365 MCP servers and load them as LangChain tools."""
        if self.mcp_service.initialized:
            return

        tools = await self.mcp_service.discover_and_load_tools(
            auth=auth,
            auth_handler_name=auth_handler_name,
            context=context,
        )
        if not tools:
            return

        self.agent = self._create_agent(tools)
        self.logger.info("✅ MCP setup completed with %d LangChain tools", len(tools))

    async def initialize(self):
        """Initialize the agent."""
        logger.info("LangChain agent initialized")

    async def process_user_message(
        self,
        message: str,
        auth: Authorization,
        auth_handler_name: Optional[str],
        context: TurnContext,
    ) -> str:
        """Process a user message using the LangChain agent graph."""
        from_prop = context.activity.from_property
        logger.info(
            "Turn received from user — DisplayName: '%s', UserId: '%s', AadObjectId: '%s'",
            getattr(from_prop, "name", None) or "(unknown)",
            getattr(from_prop, "id", None) or "(unknown)",
            getattr(from_prop, "aad_object_id", None) or "(none)",
        )

        try:
            await self.setup_mcp_servers(auth, auth_handler_name, context)
            result = await self.agent.ainvoke(
                {"messages": [HumanMessage(content=message)]}
            )
            return self._extract_result(result) or "I couldn't process your request at this time."
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return f"Sorry, I encountered an error: {str(e)}"

    async def handle_agent_notification_activity(
        self,
        notification_activity,
        auth: Authorization,
        auth_handler_name: Optional[str],
        context: TurnContext,
    ) -> str:
        """Handle agent notification activities (email, Word mentions, etc.)."""
        try:
            notification_type = notification_activity.notification_type
            logger.info(f"📬 Processing notification: {notification_type}")

            await self.setup_mcp_servers(auth, auth_handler_name, context)

            if notification_type == NotificationTypes.EMAIL_NOTIFICATION:
                if not hasattr(notification_activity, "email") or not notification_activity.email:
                    return "I could not find the email notification details."

                email = notification_activity.email
                email_body = getattr(email, "html_body", "") or getattr(email, "body", "")
                message = (
                    "You have received the following email. Please follow any "
                    f"instructions in it. {email_body}"
                )
                result = await self.agent.ainvoke(
                    {"messages": [HumanMessage(content=message)]}
                )
                return self._extract_result(result) or "Email notification processed."

            if notification_type == NotificationTypes.WPX_COMMENT:
                if (
                    not hasattr(notification_activity, "wpx_comment")
                    or not notification_activity.wpx_comment
                ):
                    return "I could not find the Word notification details."

                wpx = notification_activity.wpx_comment
                doc_id = getattr(wpx, "document_id", "")
                comment_id = getattr(wpx, "initiating_comment_id", "")
                drive_id = "default"

                doc_message = (
                    "You have a new comment on the Word document with id "
                    f"'{doc_id}', comment id '{comment_id}', drive id '{drive_id}'. "
                    "Please retrieve the Word document as well as the comments and "
                    "return it in text format."
                )
                doc_result = await self.agent.ainvoke(
                    {"messages": [HumanMessage(content=doc_message)]}
                )
                word_content = self._extract_result(doc_result)

                comment_text = notification_activity.text or ""
                response_message = (
                    "You have received the following Word document content and comments. "
                    f"Please refer to these when responding to comment '{comment_text}'. "
                    f"{word_content}"
                )
                result = await self.agent.ainvoke(
                    {"messages": [HumanMessage(content=response_message)]}
                )
                return self._extract_result(result) or "Word notification processed."

            notification_message = (
                notification_activity.text or f"Notification received: {notification_type}"
            )
            result = await self.agent.ainvoke(
                {"messages": [HumanMessage(content=notification_message)]}
            )
            return self._extract_result(result) or "Notification processed successfully."

        except Exception as e:
            logger.error(f"Error processing notification: {e}")
            return f"Sorry, I encountered an error processing the notification: {str(e)}"

    def _extract_result(self, result) -> str:
        """Extract the final assistant text from a LangChain agent response."""
        if not result:
            return ""

        if isinstance(result, dict) and "messages" in result:
            messages = result["messages"]
            if isinstance(messages, list):
                for message in reversed(messages):
                    if isinstance(message, AIMessage):
                        return self._message_content_to_text(message)
                    if isinstance(message, dict) and message.get("role") == "assistant":
                        return self._content_to_text(message.get("content", ""))

        if isinstance(result, BaseMessage):
            return self._message_content_to_text(result)

        if hasattr(result, "content"):
            return self._content_to_text(result.content)

        return str(result)

    def _message_content_to_text(self, message: BaseMessage) -> str:
        return self._content_to_text(message.content)

    def _content_to_text(self, content) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    text = item.get("text") or item.get("content")
                    if text:
                        parts.append(str(text))
            return "\n".join(parts)
        return str(content)

    async def cleanup(self) -> None:
        """Clean up agent resources."""
        try:
            await self.mcp_service.cleanup()
            logger.info("LangChain agent cleanup completed")
        except Exception as e:
            logger.error(f"Cleanup error: {e}")

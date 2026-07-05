"""LangChain Agent with MCP Server Integration and Observability"""

import asyncio
import logging
from os import environ
from typing import Optional

from azure.identity.aio import ManagedIdentityCredential
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langgraph.checkpoint.memory import InMemorySaver

# Agent Interface
from agent_interface import AgentInterface
from mcp_tool_registration_service import McpToolRegistrationService

from microsoft_agents.hosting.core import Authorization, TurnContext

# Notifications
from microsoft_agents_a365.notifications.agent_notification import NotificationTypes

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
        self.checkpointer = InMemorySaver()
        self.agent = self._create_agent([])
        self.mcp_service = McpToolRegistrationService(logger=self.logger)
        self._mcp_tools_revision = self.mcp_service.revision
        self._mcp_invoke_lock = asyncio.Lock()

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
            checkpointer=self.checkpointer,
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
        tools = await self.mcp_service.discover_and_load_tools(
            auth=auth,
            auth_handler_name=auth_handler_name,
            context=context,
        )
        self._replace_agent_if_tools_changed(tools)

    async def refresh_mcp_servers(
        self,
        auth: Authorization,
        auth_handler_name: Optional[str],
        context: TurnContext,
    ) -> None:
        """Force MCP rediscovery and rebuild the LangChain agent with fresh headers."""
        tools = await self.mcp_service.force_refresh(
            auth=auth,
            auth_handler_name=auth_handler_name,
            context=context,
        )
        self._replace_agent_if_tools_changed(tools)

    def _replace_agent_if_tools_changed(self, tools) -> None:
        if self.mcp_service.revision == self._mcp_tools_revision:
            return

        self.agent = self._create_agent(tools)
        self._mcp_tools_revision = self.mcp_service.revision
        self.logger.info("✅ MCP setup completed with %d LangChain tools", len(tools))

    async def _invoke_with_mcp_retry(
        self,
        message: str,
        auth: Authorization,
        auth_handler_name: Optional[str],
        context: TurnContext,
    ):
        thread_id = self._get_thread_id(context)
        config = {"configurable": {"thread_id": thread_id}}
        async with self._mcp_invoke_lock:
            await self.setup_mcp_servers(auth, auth_handler_name, context)
            try:
                return await self.agent.ainvoke(
                    {"messages": [HumanMessage(content=message)]},
                    config=config,
                )
            except Exception as e:
                if not self._is_auth_failure(e):
                    raise

                self.logger.warning(
                    "MCP tool call returned an auth failure; refreshing tool headers and retrying once"
                )
                await self.refresh_mcp_servers(auth, auth_handler_name, context)
                return await self.agent.ainvoke(
                    {"messages": [HumanMessage(content=message)]},
                    config=config,
                )

    def _get_thread_id(self, context: TurnContext) -> str:
        from_prop = getattr(context.activity, "from_property", None)
        user_id = getattr(from_prop, "id", None) if from_prop else None
        if not user_id:
            raise ValueError("UserId is required to checkpoint the LangGraph thread.")
        return user_id

    async def clear_conversation(self, context: TurnContext) -> None:
        """Clear the LangGraph checkpoint state for the current user."""
        thread_id = self._get_thread_id(context)
        async with self._mcp_invoke_lock:
            await self.checkpointer.adelete_thread(thread_id)
        self.logger.info(f"Cleared conversation checkpoint for thread_id {thread_id}")

    def _is_auth_failure(self, exc: BaseException) -> bool:
        if isinstance(exc, BaseExceptionGroup):
            return any(self._is_auth_failure(error) for error in exc.exceptions)

        message = str(exc)
        return "401" in message or "Unauthorized" in message

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
            result = await self._invoke_with_mcp_retry(
                message, auth, auth_handler_name, context
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

            if notification_type == NotificationTypes.EMAIL_NOTIFICATION:
                if not hasattr(notification_activity, "email") or not notification_activity.email:
                    return "I could not find the email notification details."

                email = notification_activity.email
                email_body = getattr(email, "html_body", "") or getattr(email, "body", "")
                message = (
                    "You have received the following email. Please follow any "
                    f"instructions in it. {email_body}"
                )
                result = await self._invoke_with_mcp_retry(
                    message, auth, auth_handler_name, context
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
                doc_result = await self._invoke_with_mcp_retry(
                    doc_message, auth, auth_handler_name, context
                )
                word_content = self._extract_result(doc_result)

                comment_text = notification_activity.text or ""
                response_message = (
                    "You have received the following Word document content and comments. "
                    f"Please refer to these when responding to comment '{comment_text}'. "
                    f"{word_content}"
                )
                result = await self._invoke_with_mcp_retry(
                    response_message, auth, auth_handler_name, context
                )
                return self._extract_result(result) or "Word notification processed."

            notification_message = (
                notification_activity.text or f"Notification received: {notification_type}"
            )
            result = await self._invoke_with_mcp_retry(
                notification_message, auth, auth_handler_name, context
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

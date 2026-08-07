"""Implements a LangChain-backed assistant with MCP tool support."""

import logging
from abc import ABC, abstractmethod
from os import environ
from typing import Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from langchain.agents import create_agent
from langchain.agents.middleware import AgentState, before_model
from langchain.chat_models import init_chat_model
from langchain_core.messages import BaseMessage, HumanMessage, trim_messages
from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.checkpoint.memory import InMemorySaver
from azure.identity import ManagedIdentityCredential
from microsoft_agents.hosting.core import Authorization, TurnContext
from microsoft_agents_a365.notifications.agent_notification import NotificationTypes
from token_manager import get_token, token_is_valid


class AgentInterface(ABC):
    """Declares the lifecycle and messaging contract for agent implementations."""

    @abstractmethod
    async def initialize(self) -> None:
        """Prepare the agent before it starts handling turns."""
        pass

    @abstractmethod
    async def process_user_message(
        self, message: str, auth: Authorization, auth_handler_name: Optional[str], context: TurnContext
    ) -> str:
        """Process a user message and return the response text."""
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """Release resources owned by the agent implementation."""
        pass


def check_agent_inheritance(agent_class) -> bool:
    """Return whether the supplied class implements AgentInterface."""
    if not issubclass(agent_class, AgentInterface):
        print(f"❌ Agent {agent_class.__name__} does not inherit from AgentInterface")
        return False
    return True


@before_model
def trim_conversation_history(state: AgentState, runtime) -> dict:
    """Keep persisted conversation history within the model context window."""
    return {
        "messages": trim_messages(
            state["messages"],
            strategy="last",
            token_counter="approximate",
            max_tokens=12_000,
            start_on="human",
            include_system=True,
        )
    }


class LangChainAgent(AgentInterface):
    """Runs user messages and notifications through a LangChain agent."""

    AGENT_PROMPT = environ.get("AGENT_PROMPT", "You are a helpful assistant.")

    def __init__(self):
        """Create the chat model, agent, and supporting services."""
        self.logger = logging.getLogger(self.__class__.__name__)
        self.model = self._create_model()
        self.tools: list[BaseTool] = []
        self.checkpointer = InMemorySaver()
        self.agent = self._create_agent(self.tools)

    def _create_model(self):
        """Create the LangChain chat model instance."""
        return init_chat_model(
            f"azure_ai:{environ['FOUNDRY_MODEL']}",
            project_endpoint=environ['FOUNDRY_PROJECT_ENDPOINT'],
            credential=ManagedIdentityCredential(client_id=environ['UAMI_CLIENT_ID']),
        )

    def _create_agent(self, tools: list[BaseTool]):
        """Create the LangChain agent instance."""
        agent = create_agent(
            model=self.model,
            tools=tools,
            system_prompt=self.AGENT_PROMPT,
            middleware=[trim_conversation_history],
            checkpointer=self.checkpointer,
        )
        logger.info("✅ LangChain agent created with %d tools", len(tools))
        return agent

    async def _setup_mcp_servers(self, auth: Authorization, auth_handler_name: Optional[str], context: TurnContext):
        """Attach configured MCP tool servers to the agent once per process."""
        tenant_id = getattr(context.activity.recipient, "tenant_id", None)
        agent_id = getattr(context.activity.recipient, "agentic_app_id", None)

        try:
            client = MultiServerMCPClient(
                {
                    "sentinel-mcp-data-exploration": {
                        "transport": "streamable_http",
                        "url": "https://sentinel.microsoft.com/mcp/data-exploration",
                        "headers": {
                            "Authorization": f"Bearer {await get_token(
                                    tenant_id=tenant_id,
                                    agent_id=agent_id,
                                    auth=auth,
                                    auth_handler_name=auth_handler_name,
                                    context=context,
                                    scopes="4500ebfb-89b6-4b14-a480-7f749797bfcd/.default",
                                )
                            }"
                        }
                    },
                    "sentinel-mcp-defender-triage": {
                        "transport": "streamable_http",
                        "url": "https://sentinel.microsoft.com/mcp/triage",
                        "headers": {
                            "Authorization": f"Bearer {await get_token(
                                    tenant_id=tenant_id,
                                    agent_id=agent_id,
                                    auth=auth,
                                    auth_handler_name=auth_handler_name,
                                    context=context,
                                    scopes="https://mcp.securitycenter.microsoft.com/MCP.Read.All",
                                )
                            }"
                        }
                    }
                }
            )
            self.tools = await client.get_tools()
            self.agent = self._create_agent(self.tools)

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
            await self._setup_mcp_servers(auth, auth_handler_name, context)
            result = await self._invoke(message, context)
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

            await self._setup_mcp_servers(auth, auth_handler_name, context)

            if notification_type == NotificationTypes.EMAIL_NOTIFICATION:
                if not hasattr(notification_activity, "email") or not notification_activity.email:
                    return "I could not find the email notification details."

                email = notification_activity.email
                email_body = getattr(email, "html_body", "") or getattr(email, "body", "")

                result = await self._invoke(email_body, context)
                return self._extract_result(result) or "Email notification processed."

            elif notification_type == NotificationTypes.WPX_COMMENT:
                if not hasattr(notification_activity, "wpx_comment") or not notification_activity.wpx_comment:
                    return "I could not find the Word notification details."

                wpx = notification_activity.wpx_comment
                doc_id = getattr(wpx, "document_id", "")
                comment_id = getattr(wpx, "initiating_comment_id", "")
                drive_id = "default"

                doc_message = f"You have a new comment on the Word document with id '{doc_id}', comment id '{comment_id}', drive id '{drive_id}'. Please retrieve the Word document as well as the comments and return it in text format."
                doc_result = await self._invoke(doc_message, context)
                word_content = self._extract_result(doc_result)

                comment_text = notification_activity.text or ""
                response_message = f"You have received the following Word document content and comments. Please refer to these when responding to comment '{comment_text}'. {word_content}"
                result = await self._invoke(response_message, context)
                return self._extract_result(result) or "Word notification processed."

            else:
                notification_message = notification_activity.text or f"Notification received: {notification_type}"
                result = await self._invoke(notification_message, context)
                return self._extract_result(result) or "Notification processed successfully."

        except Exception as e:
            logger.error(f"Error processing notification: {e}")
            return f"Sorry, I encountered an error processing the notification: {str(e)}"

    async def _invoke(self, message: str, context: TurnContext):
        """Invoke the agent within the checkpointed conversation thread."""
        return await self.agent.ainvoke(
            {"messages": [HumanMessage(content=message)]},
            config={"configurable": {"thread_id": self._get_thread_id(context)}},
        )

    def _get_thread_id(self, context: TurnContext) -> str:
        """Return a stable checkpoint namespace for the current conversation."""
        activity = context.activity
        conversation = getattr(activity, "conversation", None)
        conversation_id = getattr(conversation, "id", None) or getattr(activity, "conversation_id", None)
        if conversation_id:
            return str(conversation_id)

        sender = getattr(activity, "from_property", None)
        sender_id = getattr(sender, "id", None)
        return str(sender_id or getattr(activity, "id", "default"))

    def _extract_result(self, result) -> str:
        """Convert an agent run result object into response text."""
        if not result:
            return ""
        if isinstance(result, dict):
            messages = result.get("messages")
            if messages:
                return self._extract_message_text(messages[-1])
            output = result.get("output")
            if output is not None:
                return str(output)
        if hasattr(result, "contents"):
            return str(result.contents)
        elif hasattr(result, "text"):
            return str(result.text)
        elif hasattr(result, "content"):
            return str(result.content)
        else:
            return str(result)

    def _extract_message_text(self, message: BaseMessage | object) -> str:
        """Extract text from a LangChain message."""
        content = getattr(message, "content", message)
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            text_parts = []
            for part in content:
                if isinstance(part, str):
                    text_parts.append(part)
                elif isinstance(part, dict) and isinstance(part.get("text"), str):
                    text_parts.append(part["text"])
            return "\n".join(text_parts)
        return str(content)

    async def cleanup(self) -> None:
        """
        Used if agent uses McpToolRegistrationService from mcp_tool_registration_service.
        So now it's just a placeholder to fulfill AgentInterface contract since tools are managed by the MCP client and don't require explicit cleanup in this agent.
        try:
            if hasattr(self, "tool_service") and self.tool_service:
                await self.tool_service.cleanup()
            logger.info("Agent cleanup completed")
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
        """
        return

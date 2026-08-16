"""Implements a LangChain-backed assistant with MCP tool support."""

import logging
from datetime import datetime
from os import environ

from langchain.agents import create_agent
from langchain.agents.middleware import AgentState, before_model
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, trim_messages
from langchain_core.tools import BaseTool, tool
from langgraph.checkpoint.memory import InMemorySaver
from azure.identity import ManagedIdentityCredential
from microsoft_agents.hosting.core import TurnContext

from graph_tools import create_graph_security_tools

logger = logging.getLogger(__name__)


@tool
def get_current_system_time() -> str:
    """Return the current system date and time, including the local time zone."""
    return datetime.now().astimezone().isoformat()


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


class LangChainAgent:
    """Runs user messages and notifications through a LangChain agent."""

    AGENT_PROMPT = environ.get("AGENT_PROMPT", "You are a helpful assistant.")

    def __init__(self):
        """Create the chat model, agent, and supporting services."""
        self.model = self._create_model()
        self.checkpointer = InMemorySaver()
        self.initial_tools = [get_current_system_time]
        self.agent = self._create_agent(self.initial_tools)

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

    async def _setup_tools(self):
        """Attach Graph and configured MCP tools."""
        tools = list(self.initial_tools)

        try:
            """Graph tools"""
            tools.extend(await create_graph_security_tools())
            logger.info("✅ Microsoft Graph security tools setup completed")
        except Exception:
            logger.exception("⚠️ Microsoft Graph security tools setup failed")

        self.agent = self._create_agent(tools)

    async def process_user_message(self, message: str, context: TurnContext) -> str:
        """Run a user message through the agent and return its response."""
        from_prop = context.activity.from_property
        logger.info(
            "Turn received from user — DisplayName: '%s', UserId: '%s', AadObjectId: '%s'",
            getattr(from_prop, "name", None) or "(unknown)",
            getattr(from_prop, "id", None) or "(unknown)",
            getattr(from_prop, "aad_object_id", None) or "(none)",
        )

        try:
            await self._setup_tools()
            result = await self.agent.ainvoke(
                {"messages": [HumanMessage(content=message)]},
                config={"configurable": {"thread_id": self._get_thread_id(context)}},
            )
            return self._extract_result(result) or "I couldn't process your request at this time."
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return f"Sorry, I encountered an error: {str(e)}"

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

    def _extract_message_text(self, message) -> str:
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

"""Microsoft 365 Agents SDK bootstrap and Teams activity handlers.

Environment variables consumed (see local.settings.json / Azure App Settings):
  CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTID   – Bot App Registration client ID
  CONNECTIONS__SERVICE_CONNECTION__SETTINGS__TENANTID   – Azure AD tenant ID
  CONNECTIONS__SERVICE_CONNECTION__SETTINGS__TYPE       – Auth type; use
    ``SystemManagedIdentity`` (recommended, no secret needed) or ``ClientSecret``
  CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTSECRET – Required only for
    ClientSecret auth type; omit when using SystemManagedIdentity
"""

import logging
import sys
import traceback
from os import environ

from dotenv import load_dotenv
from microsoft_agents.activity import load_configuration_from_env
from microsoft_agents.authentication.msal import MsalConnectionManager
from microsoft_agents.hosting.aiohttp import CloudAdapter
from microsoft_agents.hosting.core import (
    AgentApplication,
    Authorization,
    MemoryStorage,
    TurnContext,
    TurnState,
)

from agent import ensure_agent, get_session_id

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# SDK bootstrap (runs at module import / cold-start)
# ---------------------------------------------------------------------------

load_dotenv()  # no-op in Azure; loads .env for local development
agents_sdk_config = load_configuration_from_env(environ)

STORAGE = MemoryStorage()
CONNECTION_MANAGER = MsalConnectionManager(**agents_sdk_config)
ADAPTER = CloudAdapter(connection_manager=CONNECTION_MANAGER)
AUTHORIZATION = Authorization(STORAGE, CONNECTION_MANAGER, **agents_sdk_config)

AGENT_APP = AgentApplication[TurnState](
    storage=STORAGE,
    adapter=ADAPTER,
    authorization=AUTHORIZATION,
    **agents_sdk_config,
)

# ---------------------------------------------------------------------------
# Activity handlers
# ---------------------------------------------------------------------------


@AGENT_APP.conversation_update("membersAdded")
async def on_members_added(context: TurnContext, _state: TurnState) -> bool:
    """Greet new members when they join the conversation."""
    for member in context.activity.members_added:
        if member.id != context.activity.recipient.id:
            await context.send_activity(
                "Hello! I'm your AI assistant. Send me a message to get started."
            )
    return True


@AGENT_APP.activity("message")
async def on_message(context: TurnContext, _state: TurnState) -> None:
    """Route every incoming Teams message through the LangGraph agent."""
    # Strip @-mentions of the bot so the LLM sees clean input text.
    text = context.activity.remove_mention_text(
        context.activity.recipient.id
    ).strip()

    if not text:
        return

    session_id = get_session_id(context)
    logger.info("Routing message to agent; session=%s", session_id)

    agent = await ensure_agent()
    config = {"configurable": {"thread_id": session_id}}

    # Stream model events and collect text chunks into a single reply.
    reply_parts: list[str] = []
    async for event in agent.astream_events(
        {"messages": [{"role": "user", "content": text}]},
        config=config,
        version="v2",
    ):
        if event["event"] == "on_chat_model_stream":
            for item in event["data"]["chunk"].content:
                if isinstance(item, dict) and item.get("type") == "text":
                    reply_parts.append(item["text"])
                elif isinstance(item, str):
                    reply_parts.append(item)

    reply = "".join(reply_parts).strip()
    if reply:
        await context.send_activity(reply)


@AGENT_APP.error
async def on_error(context: TurnContext, error: Exception) -> None:
    """Log unhandled errors and send a safe message to the user."""
    logger.error("Unhandled bot error: %s", error, exc_info=True)
    traceback.print_exc(file=sys.stderr)
    await context.send_activity(
        "Something went wrong on my end. Please try again in a moment."
    )

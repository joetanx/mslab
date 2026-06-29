import logging
from os import environ

from langchain_core.messages import HumanMessage
from microsoft_agents.activity import Activity, load_configuration_from_env
from microsoft_agents.authentication.msal import MsalConnectionManager
from microsoft_agents.hosting.aiohttp import CloudAdapter
from microsoft_agents.hosting.core import (
    AgentApplication,
    Authorization,
    MemoryStorage,
    TurnContext,
    TurnState,
)

from agent import agent_manager

logger = logging.getLogger(__name__)

# Microsoft Agents SDK setup
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

def get_session_id(context: TurnContext) -> str:
    # Convert Teams/Bot Framework conversation identity into a stable
    # LangGraph thread_id for checkpointed memory.

    conversation = context.activity.conversation
    conv_type = conversation.conversation_type
    conv_id = conversation.id

    match conv_type:
        case 'channel':
            team_id = context.activity.channel_data.get('team', {}).get('id', '')
            session_id = f"channel:{team_id}:{conv_id}"
        case 'groupChat':
            session_id = f"groupChat:{conv_id}"
        case _:
            session_id = f"personal:{conv_id}"
    logger.debug(f"Resolved session_id={session_id} (conv_type={conv_type})")
    return session_id

@AGENT_APP.conversation_update("membersAdded")
async def on_members_added(context: TurnContext, _state: TurnState) -> bool:
    # Send a simple welcome message when the bot is added.

    for member in context.activity.members_added:
        if member.id != context.activity.recipient.id:
            await context.send_activity("Hello! 👋 I am here to help!")

    return True

@AGENT_APP.message('/clear')
async def on_clear(context: TurnContext, _state: TurnState) -> None:
    # Clear LangGraph checkpoint history for the current Teams conversation.

    session_id = get_session_id(context)
    logger.info(f"Clearing conversation history; session={session_id}")

    try:
        await agent_manager.clear_conversation(session_id)
        await context.send_activity('✅ Conversation history cleared! Starting fresh.')
        logger.info(f"Conversation history cleared successfully; session={session_id}")
    except Exception as exc:
        logger.error(f"Failed to clear conversation; session={session_id} error={exc}", exc_info=True)
        await context.send_activity('❌ Failed to clear conversation history. Please try again.')

@AGENT_APP.activity('message')
async def on_message(context: TurnContext, _state: TurnState) -> None:
    # Handle normal user messages.

    text = context.activity.text
    session_id = get_session_id(context)
    logger.info(f"Received message (len={len(text)}); routing to agent; session={session_id}")

    await context.send_activity(Activity(type='typing'))

    agent = await agent_manager.get_agent()

    response = await agent.ainvoke(
        {'messages': [HumanMessage(content=text)]},
        config={'configurable': {'thread_id': session_id}},
    )

    await context.send_activity(response['messages'][-1].content[-1]['text'])

@AGENT_APP.error
async def on_error(context: TurnContext, error: Exception) -> None:
    # Global bot error handler.

    logger.error(f"Unhandled bot error: {error}", exc_info=True)
    await context.send_activity("Something went wrong on my end. Please try again.")

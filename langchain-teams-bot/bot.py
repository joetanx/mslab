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

from agent import clear_conversation, ensure_agent, get_session_id

logger = logging.getLogger(__name__)

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

@AGENT_APP.conversation_update('membersAdded')
async def on_members_added(context: TurnContext, _state: TurnState) -> bool:
    # Send a welcome message to each newly added member (excluding the bot itself).
    for member in context.activity.members_added:
        if member.id != context.activity.recipient.id:
            logger.info(f"Welcoming new member id={member.id}")
            await context.send_activity('Hello! 👋 I am here to help!')
    return True

@AGENT_APP.message('/clear')
async def on_clear(context: TurnContext, state: TurnState) -> None:
    # Handles the /clear command
    session_id = get_session_id(context)
    logger.info(f"Processing /clear command; session={session_id}")
    try:
        await clear_conversation(session_id)
        await context.send_activity('✅ Conversation history cleared! Starting fresh.')
        logger.info(f"Conversation history cleared successfully; session={session_id}")
    except Exception as exc:
        logger.error(f"Failed to clear conversation; session={session_id} error={exc}", exc_info=True)
        await context.send_activity('❌ Failed to clear conversation history. Please try again.')

@AGENT_APP.activity('message')
async def on_message(context: TurnContext, _state: TurnState) -> None:
    # Handle an incoming message activity.

    session_id = get_session_id(context)
    logger.info(f"Received message (len={len(context.activity.text)}); routing to agent; session={session_id}")

    agent = await ensure_agent()
    config = {'configurable': {'thread_id': session_id}}

    reply_parts: list[str] = []
    await context.send_activity(Activity(type='typing'))
    logger.debug(f"Streaming agent response; session={session_id}")
    async for event in agent.astream_events(
        {'messages': [HumanMessage(content=context.activity.text)]},
        config=config,
        version='v2',
    ):
        if event['event'] == 'on_chat_model_stream':
            for item in event['data']['chunk'].content:
                if isinstance(item, dict) and item.get('type') == 'text':
                    reply_parts.append(item['text'])
                elif isinstance(item, str):
                    reply_parts.append(item)

    reply = ''.join(reply_parts).strip()
    if reply:
        logger.info(f"Sending reply (len={len(reply)}); session={session_id}")
        await context.send_activity(reply)
    else:
        logger.warning(f"Agent returned empty reply; session={session_id}")

@AGENT_APP.error
async def on_error(context: TurnContext, error: Exception) -> None:
    # Log unhandled bot errors and send a user-facing fallback message.
    logger.error(f"Unhandled bot error: {error}", exc_info=True)
    await context.send_activity('Something went wrong on my end. Please try again in a moment.')

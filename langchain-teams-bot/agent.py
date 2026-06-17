import asyncio
import logging
import os
import time
from typing import Optional

import psycopg  # noqa: F401  (psycopg must be importable for AsyncPostgresSaver)
from azure.identity.aio import ManagedIdentityCredential
from langchain.chat_models import init_chat_model
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.prebuilt import create_react_agent
from psycopg_pool import AsyncConnectionPool

logger = logging.getLogger(__name__)

# Module-level singletons
_credential: Optional[ManagedIdentityCredential] = None
_pool: Optional[AsyncConnectionPool] = None
_checkpointer: Optional[AsyncPostgresSaver] = None
_agent = None  # compiled LangGraph graph
_token_expires_at: float = 0.0
_init_lock: Optional[asyncio.Lock] = None

def _get_lock() -> asyncio.Lock:
    # Return the module-level asyncio lock, creating it lazily on first call.
    global _init_lock
    if _init_lock is None:
        _init_lock = asyncio.Lock()
    return _init_lock

async def _build_dsn() -> tuple[str, float]:
    # Fetch a fresh AAD token and return a psycopg connection string with its expiry.
    assert _credential is not None
    token = await _credential.get_token('https://ossrdbms-aad.database.windows.net/.default')
    dsn = (
        f"host={os.environ['POSTGRES_HOST']} "
        f"port={os.environ.get('POSTGRES_PORT', '5432')} "
        f"dbname={os.environ['POSTGRES_DB']} "
        f"user={os.environ['POSTGRES_USER']} "
        f"password={token.token} "
        'sslmode=require'
    )
    logger.debug(f"Built DSN for host={os.environ['POSTGRES_HOST']} db={os.environ['POSTGRES_DB']} user={os.environ['POSTGRES_USER']}"
)
    return dsn, float(token.expires_on)

async def _open_pool() -> AsyncConnectionPool:
    # Open a psycopg async connection pool authenticated via AAD token.
    dsn, expires_at = await _build_dsn()
    global _token_expires_at
    _token_expires_at = expires_at

    max_size = int(os.environ.get('POSTGRES_POOL_MAX', '5'))
    pool = AsyncConnectionPool(
        conninfo=dsn,
        min_size=1,
        max_size=max_size,
        open=False,
        kwargs={'autocommit': True, 'prepare_threshold': 0},
    )
    await pool.open()
    logger.info(f"PostgreSQL pool opened (max_size={max_size}); token expires at {expires_at}")
    return pool

def get_session_id(context) -> str:
    # Derive a stable LangGraph thread_id from the Bot Framework TurnContext.
    # Returns a namespaced string:
    # - channel:<team_id>:<conversation_id>  for channel posts
    # - groupchat:<conversation_id>          for group chats
    # - personal:<conversation_id>           for 1-to-1 chats

    activity = context.activity
    conv = activity.conversation
    conv_type = (conv.conversation_type or '').lower()

    if conv_type == 'channel':
        channel_data = getattr(activity, 'channel_data', None) or {}
        team_id = ''
        if isinstance(channel_data, dict):
            team = channel_data.get('team') or {}
            team_id = team.get('id', '') if isinstance(team, dict) else ''
        session_id = f"channel:{team_id}:{conv.id}"
    elif conv_type == 'groupchat':
        session_id = f"groupchat:{conv.id}"
    else:
        session_id = f"personal:{conv.id}"

    logger.debug(f"Resolved session_id={session_id} (conv_type={conv_type})")
    return session_id

async def ensure_agent():
    # Return the compiled LangGraph agent, initialising or refreshing it as needed.
    # Uses a double-checked lock so only one coroutine performs cold-start.
    # Re-initialises (including a fresh AAD token and connection pool) when the current token is within 5 minutes of expiry.

    global _credential, _pool, _checkpointer, _agent

    if _agent is not None and time.time() < _token_expires_at - 300:
        logger.debug(f"Returning cached agent (token valid for {_token_expires_at - time.time():.0f}s)")
        return _agent

    async with _get_lock():
        if _agent is not None and time.time() < _token_expires_at - 300:
            logger.debug('Cached agent valid after lock acquisition; skipping re-init')
            return _agent

        logger.info('Initialising LangGraph agent (cold-start or token refresh)')

        if _credential is None:
            _credential = ManagedIdentityCredential(
                client_id=os.environ.get('UAMI_CLIENT_ID')
            )
            logger.debug(f"Created ManagedIdentityCredential (client_id={os.environ.get('UAMI_CLIENT_ID')})")

        if _pool is not None:
            try:
                await _pool.close()
                logger.debug('Closed stale connection pool')
            except Exception:  # noqa: BLE001
                logger.warning('Failed to close stale pool cleanly; proceeding with new pool')

        _pool = await _open_pool()

        _checkpointer = AsyncPostgresSaver(_pool)
        await _checkpointer.setup()
        logger.debug('AsyncPostgresSaver checkpointer ready')

        model = init_chat_model(
            f"azure_ai:{os.environ['FOUNDRY_MODEL']}",
            project_endpoint=os.environ['FOUNDRY_PROJECT_ENDPOINT'],
            credential=_credential,
        )
        logger.debug(f"Chat model initialised: azure_ai/{os.environ['FOUNDRY_MODEL']}")

        system_prompt = os.environ.get('AGENT_SYSTEM_PROMPT', 'You are a helpful assistant.')

        prompt = ChatPromptTemplate.from_messages([
            ('system', system_prompt),
            MessagesPlaceholder(variable_name='messages'),
        ])

        _agent = create_react_agent(
            model=model,
            tools=[],
            prompt=prompt,
            checkpointer=_checkpointer,
        )

        logger.info(f"Agent initialisation complete (model=azure_ai/{os.environ['FOUNDRY_MODEL']})")
        return _agent

async def clear_conversation(session_id: str) -> None:
    # Delete all LangGraph checkpoint data for *session_id* from PostgreSQL.
    # Removes rows from checkpoints, checkpoint_blobs, and checkpoint_writes, which together constitute the full conversation state stored by LangGraph.
    # Ensures the agent (and pool) is initialised before attempting the deletion.

    await ensure_agent()
    if _pool is None:
        logger.warning(f"Cannot clear conversation: pool not available; session={session_id}")
        return

    logger.info(f"Clearing checkpoint data for session={session_id}")
    try:
        async with _pool.connection() as conn:
            await conn.execute("DELETE FROM checkpoints WHERE thread_id = %s", (session_id,))
            await conn.execute("DELETE FROM checkpoint_blobs WHERE thread_id = %s", (session_id,))
            await conn.execute("DELETE FROM checkpoint_writes WHERE thread_id = %s", (session_id,))
        logger.info(f"Checkpoint data cleared for session={session_id}")
    except Exception as exc:
        logger.error(f"Failed to clear checkpoint data for session={session_id}: {exc}", exc_info=True)
        raise

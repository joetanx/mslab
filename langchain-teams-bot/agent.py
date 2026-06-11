"""LangGraph react agent backed by Azure AI Foundry and a PostgreSQL checkpointer.

The agent is initialised lazily on the first request (cold start).  A
module-level asyncio.Lock prevents concurrent initialisations.  The
PostgreSQL connection pool is rebuilt automatically when the Azure AD token
it was created with is within 5 minutes of expiry.
"""

import asyncio
import logging
import os
import time
from typing import Optional

import psycopg  # noqa: F401  (psycopg must be importable for AsyncPostgresSaver)
from azure.identity.aio import ManagedIdentityCredential
from langchain.chat_models import init_chat_model
from langchain_core.messages import SystemMessage, trim_messages
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.prebuilt import create_react_agent
from psycopg_pool import AsyncConnectionPool

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level singletons
# ---------------------------------------------------------------------------

_credential: Optional[ManagedIdentityCredential] = None
_pool: Optional[AsyncConnectionPool] = None
_checkpointer: Optional[AsyncPostgresSaver] = None
_agent = None  # compiled LangGraph graph
_token_expires_at: float = 0.0
_init_lock: Optional[asyncio.Lock] = None


def _get_lock() -> asyncio.Lock:
    """Return the initialisation lock, creating it lazily inside the event loop."""
    global _init_lock
    if _init_lock is None:
        _init_lock = asyncio.Lock()
    return _init_lock


# ---------------------------------------------------------------------------
# PostgreSQL helpers
# ---------------------------------------------------------------------------

async def _build_dsn() -> tuple[str, float]:
    """Acquire a fresh MI token and return (psycopg DSN, token_expires_on)."""
    assert _credential is not None
    token = await _credential.get_token(
        "https://ossrdbms-aad.database.windows.net/.default"
    )
    dsn = (
        f"host={os.environ['POSTGRES_HOST']} "
        f"port={os.environ.get('POSTGRES_PORT', '5432')} "
        f"dbname={os.environ['POSTGRES_DB']} "
        f"user={os.environ['POSTGRES_USER']} "
        f"password={token.token} "
        "sslmode=require"
    )
    return dsn, float(token.expires_on)


async def _open_pool() -> AsyncConnectionPool:
    """Create and open a psycopg_pool.AsyncConnectionPool with a fresh token."""
    dsn, expires_at = await _build_dsn()
    global _token_expires_at
    _token_expires_at = expires_at

    pool = AsyncConnectionPool(
        conninfo=dsn,
        min_size=1,
        max_size=int(os.environ.get("POSTGRES_POOL_MAX", "5")),
        open=False,
    )
    await pool.open()
    logger.info("PostgreSQL pool opened; token expires at %s", expires_at)
    return pool


# ---------------------------------------------------------------------------
# Session ID helper
# ---------------------------------------------------------------------------

def get_session_id(context) -> str:
    """Return a stable LangGraph thread_id scoped to the Teams conversation.

    * Personal (1:1) DM  → ``personal:<conversation.id>``
    * Group chat          → ``groupchat:<conversation.id>``
    * Channel thread      → ``channel:<team_id>:<conversation.id>``
    """
    activity = context.activity
    conv = activity.conversation
    conv_type = (conv.conversation_type or "").lower()

    if conv_type == "channel":
        channel_data = getattr(activity, "channel_data", None) or {}
        team_id = ""
        if isinstance(channel_data, dict):
            team = channel_data.get("team") or {}
            team_id = team.get("id", "") if isinstance(team, dict) else ""
        return f"channel:{team_id}:{conv.id}"

    if conv_type == "groupchat":
        return f"groupchat:{conv.id}"

    return f"personal:{conv.id}"


# ---------------------------------------------------------------------------
# Lazy agent initialisation
# ---------------------------------------------------------------------------

async def ensure_agent():
    """Build (or rebuild) the agent and its infrastructure on first call.

    The function is idempotent and re-entrant-safe via an asyncio.Lock.
    The pool + checkpointer are rebuilt automatically when the Azure AD
    token used to open the pool is within 5 minutes of expiry.
    """
    global _credential, _pool, _checkpointer, _agent

    # Fast-path: already initialised and token not near expiry.
    if _agent is not None and time.time() < _token_expires_at - 300:
        return _agent

    async with _get_lock():
        # Re-check after acquiring the lock (another coroutine may have finished).
        if _agent is not None and time.time() < _token_expires_at - 300:
            return _agent

        logger.info("Cold-start: initialising LangGraph agent")

        if _credential is None:
            _credential = ManagedIdentityCredential()

        # Close stale pool if we are refreshing an expired token.
        if _pool is not None:
            try:
                await _pool.close()
            except Exception:  # noqa: BLE001
                pass

        _pool = await _open_pool()

        _checkpointer = AsyncPostgresSaver(_pool)
        # Creates the langgraph checkpoint tables if they don't exist yet.
        await _checkpointer.setup()

        # Build the Azure AI Foundry model (reuses the same MI credential).
        model = init_chat_model(
            f"azure_ai:{os.environ['FOUNDRY_MODEL']}",
            project_endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"],
            credential=_credential,
        )

        system_prompt = os.environ.get(
            "AGENT_SYSTEM_PROMPT", "You are a helpful assistant."
        )
        max_tokens = int(os.environ.get("MAX_HISTORY_TOKENS", "4096"))

        def _state_modifier(messages):
            """Prepend system message then trim to the context-window budget."""
            # Ensure exactly one SystemMessage at the front.
            non_system = [m for m in messages if not isinstance(m, SystemMessage)]
            full = [SystemMessage(content=system_prompt)] + non_system
            return trim_messages(
                full,
                strategy="last",
                token_counter=model,
                max_tokens=max_tokens,
                start_on="human",
                include_system=True,
                allow_partial=False,
            )

        _agent = create_react_agent(
            model=model,
            tools=[],
            messages_modifier=_state_modifier,
            checkpointer=_checkpointer,
        )

        logger.info("Agent initialisation complete")
        return _agent

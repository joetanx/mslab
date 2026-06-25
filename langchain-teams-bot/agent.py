import asyncio
from os import environ
import time
import logging

from azure.identity.aio import ManagedIdentityCredential
from langchain.chat_models import init_chat_model
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.prebuilt import create_react_agent
from psycopg_pool import AsyncConnectionPool

logger = logging.getLogger(__name__)

class AgentManager:
    # Manages the lifecycle of a ReAct agent, including connection pooling to a PostgreSQL database and token management for Azure authentication.

    def __init__(self):
        # Initializes the AgentManager with a lock for thread safety, a credential for Azure Managed Identity, and placeholders for the connection pool and agent.

        self.lock = asyncio.Lock()
        self.credential = ManagedIdentityCredential(client_id=environ['UAMI_CLIENT_ID'])
        self.pool = None
        self.agent = None
        self.token_expiry = 0

    async def _build_pool(self):
        # Builds a new async connection pool to the PostgreSQL database using an access token for authentication.

        logger.debug('Building new PostgreSQL connection pool')
        token = await self.credential.get_token('https://ossrdbms-aad.database.windows.net/.default')
        self.token_expiry = token.expires_on

        dsn = (
            f"host={environ['POSTGRES_HOST']} "
            f"port={environ.get('POSTGRES_PORT', '5432')} "
            f"dbname={environ['POSTGRES_DB']} "
            f"user={environ['POSTGRES_USER']} "
            f"password={token.token} "
            "sslmode=require"
        )

        pool = AsyncConnectionPool(
            conninfo=dsn,
            min_size=1,
            max_size=int(environ.get('POSTGRES_POOL_MAX', '5')),
            open=False,
            kwargs={'autocommit': True, 'prepare_threshold': 0},
        )

        await pool.open()
        logger.info('PostgreSQL connection pool established')

        return pool

    async def get_agent(self):
        # Returns the ReAct agent, creating it if necessary. Refreshes the token if it's close to expiry.

        TOKEN_REFRESH_BUFFER_SECONDS = int(environ.get('TOKEN_REFRESH_BUFFER_SECONDS', '300'))

        if self.agent and time.time() < self.token_expiry - TOKEN_REFRESH_BUFFER_SECONDS:
            # Check if the agent already exists and the token is still valid. If so, return the existing agent instance.
            logger.debug('Returning existing agent instance')
            return self.agent

        async with self.lock:

            if self.agent and time.time() < self.token_expiry - TOKEN_REFRESH_BUFFER_SECONDS:
                # Check again after acquiring the lock
                logger.debug('Returning existing agent instance after acquiring lock')
                return self.agent

            if self.pool is not None:
                # Close the existing pool before creating a new one to avoid resource leaks.
                await self.pool.close()

            self.pool = await self._build_pool()

            checkpointer = AsyncPostgresSaver(self.pool)
            await checkpointer.setup()
            logger.debug('Checkpointer setup completed')

            model = init_chat_model(
                f"azure_ai:{environ['FOUNDRY_MODEL']}",
                project_endpoint=environ['FOUNDRY_PROJECT_ENDPOINT'],
                credential=self.credential,
            )
            logger.debug('Chat model initialized')

            prompt = ChatPromptTemplate.from_messages([
                ('system', environ.get('AGENT_SYSTEM_PROMPT', 'You are a helpful assistant.')),
                MessagesPlaceholder(variable_name='messages'),
            ])

            self.agent = create_react_agent(
                model=model,
                tools=[],
                prompt=prompt,
                checkpointer=checkpointer
            )
            logger.info('ReAct agent created successfully')

            return self.agent

    async def clear_conversation(self, session_id: str):
        # Clears the conversation history for a given session ID by deleting related records from the database.

        await self.get_agent()

        async with self.pool.connection() as conn:
            for table in (
                'checkpoint_writes',
                'checkpoint_blobs',
                'checkpoints',
            ):
                await conn.execute(f"DELETE FROM {table} WHERE thread_id = %s", (session_id,))
                logger.info(f"Deleted records from table {table} for session_id={session_id}")

# Singleton instance shared across the application.
agent_manager = AgentManager()

"""Hosts a LangChain agent behind the Microsoft Agents HTTP server."""

import sys, logging
from os import environ

from aiohttp.web import Application, Request, Response, json_response, run_app
from aiohttp.web_middlewares import middleware as web_middleware
from agent import LangChainAgent
from microsoft_agents.activity import load_configuration_from_env
from microsoft_agents.authentication.msal import MsalConnectionManager
from microsoft_agents.hosting.aiohttp import (
    CloudAdapter,
    jwt_authorization_middleware,
    start_agent_process,
)
from microsoft_agents.hosting.core import (
    AgentApplication,
    AgentAuthConfiguration,
    AuthenticationConstants,
    Authorization,
    ClaimsIdentity,
    MemoryStorage,
    TurnContext,
    TurnState,
)
from microsoft.opentelemetry import use_microsoft_opentelemetry
from microsoft.opentelemetry.a365.core import BaggageBuilder
from microsoft.opentelemetry.a365.runtime import get_observability_authentication_scope

from token_manager import get_token

logging.basicConfig(
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

agents_sdk_config = load_configuration_from_env(environ)


class AgentHost:
    """Configures authentication, handlers, notifications, and HTTP hosting."""

    def __init__(self):
        """Initialize host services and register activity handlers."""
        self.auth_handler_name = environ.get("AUTH_HANDLER_NAME")
        self.storage = MemoryStorage()
        self.connection_manager = MsalConnectionManager(**agents_sdk_config)
        self.adapter = CloudAdapter(connection_manager=self.connection_manager)
        self.authorization = Authorization(
            self.storage, self.connection_manager, **agents_sdk_config
        )
        self.agent_app = AgentApplication[TurnState](
            storage=self.storage,
            adapter=self.adapter,
            authorization=self.authorization,
            **agents_sdk_config,
        )
        self.setup_handlers()
        logger.info("✅ Notification handlers registered successfully")
        self.observability_token: str | None = None
        self.auth_configuration = AgentAuthConfiguration(
            **agents_sdk_config["CONNECTIONS"]["SERVICE_CONNECTION"]["SETTINGS"],
            scopes=["5a807f24-c9de-44ee-a3a7-329e88a00ffc/.default"],
        ) or None
        logger.info("🔒 AgentAuthConfiguration initialized with FIC")
        self.agent = LangChainAgent()

    def setup_handlers(self):
        """Register handler for Teams messages."""
        handler_config = {"auth_handlers": [self.auth_handler_name]} if self.auth_handler_name else {}

        @self.agent_app.activity("message", **handler_config)
        async def on_message(context: TurnContext, _: TurnState):
            """Handle incoming chat messages from users."""
            try:
                tenant_id = getattr(context.activity.recipient, "tenant_id")
                agent_id = getattr(context.activity.recipient, "agentic_app_id")
                self.observability_token = await get_token(
                    tenant_id=getattr(context.activity.recipient, "tenant_id"),
                    agent_id=getattr(context.activity.recipient, "agentic_app_id"),
                    agent_user=getattr(context.activity.recipient, "agentic_user_id"),
                    scopes=get_observability_authentication_scope(),
                )
                with BaggageBuilder().tenant_id(tenant_id).agent_id(agent_id).build():
                    logger.info(f"📨 {getattr(context.activity, 'channel_id')}: {context.activity.text}")
                    response = await self.agent.process_user_message(context.activity.text, context)
                    await context.send_activity(response)
            except Exception as e:
                logger.error(f"❌ Error: {e}")
                await context.send_activity(f"Sorry, I encountered an error: {str(e)}")

    def start_server(self):
        """Build and run the aiohttp server for agent traffic."""

        async def entry_point(req: Request) -> Response:
            """Forward message requests into the Microsoft Agents adapter."""
            return await start_agent_process(req, req.app["agent_app"], req.app["adapter"])

        async def health(req: Request) -> Response:
            """Return the health state of the hosted agent."""
            return json_response(
                {
                    "status": "ok",
                    "agent_type": self.agent.__class__.__name__,
                    "agent_initialized": self.agent is not None,
                }
            )

        middlewares = []
        if self.auth_configuration:

            @web_middleware
            async def jwt_with_health_bypass(request, handler):
                """Apply JWT authorization except for health checks."""
                if request.path == "/api/health":
                    return await handler(request)
                return await jwt_authorization_middleware(request, handler)

            middlewares.append(jwt_with_health_bypass)

        @web_middleware
        async def anonymous_claims(request, handler):
            """Inject anonymous claims when authentication is disabled."""
            if not self.auth_configuration:
                request["claims_identity"] = ClaimsIdentity(
                    {
                        AuthenticationConstants.AUDIENCE_CLAIM: "anonymous",
                        AuthenticationConstants.APP_ID_CLAIM: "anonymous-app",
                    },
                    False,
                    "Anonymous",
                )
            return await handler(request)

        middlewares.append(anonymous_claims)
        app = Application(middlewares=middlewares)

        app.router.add_post("/api/messages", entry_point)
        app.router.add_get("/api/messages", lambda _: Response(status=200))
        app.router.add_get("/api/health", health)

        app["agent_configuration"] = self.auth_configuration
        app["agent_app"] = self.agent_app
        app["adapter"] = self.agent_app.adapter

        use_microsoft_opentelemetry(
            enable_a365=True,
            a365_token_resolver=lambda agent_id, tenant_id: self.observability_token,
            instrumentation_options={
                "openai": {"enabled": False},
                "openai_agents": {"enabled": False},
                "langchain": {"enabled": True},
                "semantic_kernel": {"enabled": False},
                "agent_framework": {"enabled": False},
            },
        )

        print("▶️ Starting agent server...")
        run_app(
            app,
            host=environ.get("HOST", "localhost"),
            port=int(environ.get("PORT", 3978)),
            handle_signals=True,
        )
        print("👋 Agent server stopped") # run_app is blocking, so this prints after server is stopped


def main() -> None:
    """Configure observability and start the HTTP host."""
    host = AgentHost()
    host.start_server()


if __name__ == "__main__":
    main()

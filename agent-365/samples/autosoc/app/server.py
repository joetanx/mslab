"""Hosts the authenticated AutoSOC triage webhook on Azure Container Apps."""

import asyncio
import jwt
import logging
import sys
from os import environ
from uuid import uuid4

from aiohttp.web import Application, Request, Response, json_response, run_app
from aiohttp.web_middlewares import middleware as web_middleware
from microsoft_agents.activity import load_configuration_from_env
from microsoft_agents.hosting.aiohttp import jwt_authorization_middleware
from microsoft_agents.hosting.core import AgentAuthConfiguration
from microsoft.opentelemetry import use_microsoft_opentelemetry
from microsoft.opentelemetry.a365.core import BaggageBuilder
from microsoft.opentelemetry.a365.runtime import get_observability_authentication_scope

from token_manager import get_token
from agent import AutoSOCAgent

logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger(__name__)

agents_sdk_config = load_configuration_from_env(environ)


class AutoSOCHost:
    """Configures bearer authentication and background triage execution."""

    def __init__(self) -> None:
        service_settings = agents_sdk_config["CONNECTIONS"]["SERVICE_CONNECTION"]["SETTINGS"]
        client_id = environ["CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTID"]
        token_scope = environ.get("TRIAGE_AUTH_SCOPE", f"{client_id}/.default")
        self.auth_configuration = AgentAuthConfiguration(
            **service_settings,
            scopes=[token_scope],
        )
        self.allowed_callers = {
            caller.strip()
            for caller in environ.get("TRIAGE_ALLOWED_CALLER_APP_IDS", "").split(",")
            if caller.strip()
        }
        if not self.allowed_callers:
            raise ValueError("TRIAGE_ALLOWED_CALLER_APP_IDS must contain the Logic App identity client ID")
        self.observability_token: str | None = None
        self.agent = AutoSOCAgent()
        self.tasks: dict[str, asyncio.Task] = {}
        logger.info("AutoSOC bearer validation configured scope=%s", token_scope)

    async def initialize(self, _app: Application) -> None:
        """Initialize Graph authorization before the service becomes ready."""
        await self.agent.initialize()
        logger.info("AutoSOC host initialized")

    async def shutdown(self, _app: Application) -> None:
        """Cancel in-flight work during a replica shutdown."""
        active_tasks = list(self.tasks.values())
        for task in active_tasks:
            task.cancel()
        if active_tasks:
            await asyncio.gather(*active_tasks, return_exceptions=True)
        logger.info("AutoSOC host stopped; cancelled_tasks=%d", len(active_tasks))

    async def triage(self, request: Request) -> Response:
        """Validate a triage request, schedule it, and acknowledge immediately."""
        if not self._is_allowed_caller(request):
            logger.warning("Triage request rejected: caller identity is not allowlisted")
            return json_response({"error": "Caller is not authorized."}, status=403)
        try:
            payload = await request.json()
        except Exception:
            return json_response({"error": "Request body must be valid JSON."}, status=400)

        incident_id = payload.get("incidentId") if isinstance(payload, dict) else None
        if incident_id is None or not str(incident_id).strip():
            return json_response({"error": "incidentId is required."}, status=400)
        incident_id = str(incident_id).strip()

        existing = self.tasks.get(incident_id)
        if existing and not existing.done():
            logger.info("Duplicate triage request accepted incident_id=%s", incident_id)
            return json_response(
                {"status": "accepted", "incidentId": incident_id, "duplicate": True},
                status=202,
            )

        thread_id = f"incident:{incident_id}:run:{uuid4()}"
        task = asyncio.create_task(
            self._run_triage(incident_id, thread_id),
            name=f"triage-{incident_id}",
        )
        self.tasks[incident_id] = task
        logger.info("Triage request accepted incident_id=%s thread_id=%s", incident_id, thread_id)
        return json_response(
            {"status": "accepted", "incidentId": incident_id},
            status=202,
        )

    async def _run_triage(self, incident_id: str, thread_id: str) -> None:
        try:
            tenant_id=environ.get("CONNECTIONS__SERVICE_CONNECTION__SETTINGS__TENANTID")
            agent_id=environ.get("AGENTIC_INSTANCE_ID")
            agent_user=environ.get("AGENTIC_USER_ID")
            self.observability_token = await get_token(
                tenant_id=tenant_id,
                agent_id=agent_id,
                agent_user=agent_user,
                scopes=get_observability_authentication_scope(),
            )
            with BaggageBuilder().tenant_id(tenant_id).agent_id(agent_id).build():
                await self.agent.triage(incident_id, thread_id)
        except asyncio.CancelledError:
            logger.warning("Triage cancelled incident_id=%s", incident_id)
            raise
        except Exception:
            logger.exception("Triage failed incident_id=%s thread_id=%s", incident_id, thread_id)
        finally:
            current = asyncio.current_task()
            if self.tasks.get(incident_id) is current:
                self.tasks.pop(incident_id, None)

    def _is_allowed_caller(self, request: Request) -> bool:
        """Authorize the managed identity after SDK signature and audience validation."""
        authorization = request.headers.get("Authorization", "")
        if not authorization.lower().startswith("bearer "):
            return False
        token = authorization.split(None, 1)[1]
        try:
            claims = jwt.decode(
                token,
                options={
                    "verify_signature": False,
                    "verify_aud": False,
                    "verify_exp": False,
                },
            )
        except jwt.PyJWTError:
            return False
        caller_id = claims.get("azp") or claims.get("appid")
        return caller_id in self.allowed_callers

    def create_app(self) -> Application:
        """Build the authenticated aiohttp application."""

        @web_middleware
        async def jwt_with_health_bypass(request, handler):
            if request.path == "/api/health":
                return await handler(request)
            return await jwt_authorization_middleware(request, handler)

        async def health(_request: Request) -> Response:
            return json_response({
                "status": "ok",
                "agent_initialized": bool(self.agent._tools),
                "active_triages": len(self.tasks),
            })

        app = Application(middlewares=[jwt_with_health_bypass])
        app.router.add_post("/api/triage", self.triage)
        app.router.add_get("/api/health", health)
        app["agent_configuration"] = self.auth_configuration
        app.on_startup.append(self.initialize)
        app.on_shutdown.append(self.shutdown)
        return app

    def run(self) -> None:
        """Run the AutoSOC web service."""
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
        run_app(
            self.create_app(),
            host=environ.get("HOST", "0.0.0.0"),
            port=int(environ.get("PORT", "3978")),
            handle_signals=True,
        )


def main() -> None:
    """Start the AutoSOC host."""
    AutoSOCHost().run()


if __name__ == "__main__":
    main()

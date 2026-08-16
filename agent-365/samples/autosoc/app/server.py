"""Host AutoSOC behind an authenticated asynchronous HTTP webhook."""

import asyncio
import logging
import sys
from collections.abc import Awaitable, Callable
from os import environ
from typing import Protocol
from uuid import uuid4

from aiohttp import web
from pydantic import ValidationError

from auth import AuthenticationError, EntraTokenVerifier, get_bearer_token
from models import TriageAccepted, TriageRequest


logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger(__name__)

TRIAGE_TASKS_KEY = web.AppKey("triage_tasks", set[asyncio.Task[None]])
ACTIVE_INCIDENTS_KEY = web.AppKey("active_incidents", dict[str, str])
RUNNER_KEY = web.AppKey("triage_runner", dict[str, object])
VERIFIER_KEY = web.AppKey("token_verifier", object)
SEMAPHORE_KEY = web.AppKey("triage_semaphore", asyncio.Semaphore)
ACCEPTING_KEY = web.AppKey("accepting_requests", dict[str, bool])
CALLER_KEY = web.RequestKey("authenticated_caller", object)


class TriageRunner(Protocol):
    """Service capable of completing one autonomous incident triage."""

    async def run_triage(self, incident_id: str, correlation_id: str) -> None:
        """Run triage through assessment and Defender write-back."""

    async def close(self) -> None:
        """Release credentials and network clients."""


class TokenVerifier(Protocol):
    """Minimal verifier contract used by the authentication middleware."""

    async def verify(self, token: str) -> object:
        """Validate a bearer token and return selected caller claims."""


RunnerFactory = Callable[[], TriageRunner]


@web.middleware
async def authentication_middleware(
    request: web.Request,
    handler: Callable[[web.Request], Awaitable[web.StreamResponse]],
) -> web.StreamResponse:
    """Require a trusted Entra bearer token except on the health endpoint."""
    if request.path == "/api/health":
        return await handler(request)

    try:
        token = get_bearer_token(request.headers.get("Authorization"))
        request[CALLER_KEY] = await request.app[VERIFIER_KEY].verify(token)
    except AuthenticationError:
        return web.json_response({"error": "unauthorized"}, status=401)
    return await handler(request)


def create_app(
    *,
    runner: TriageRunner | None = None,
    runner_factory: RunnerFactory | None = None,
    verifier: TokenVerifier | None = None,
) -> web.Application:
    """Create the HTTP application with injectable services for tests."""
    app = web.Application(
        middlewares=[authentication_middleware],
        client_max_size=int(environ.get("MAX_REQUEST_BYTES", "16384")),
    )
    app[TRIAGE_TASKS_KEY] = set()
    app[ACTIVE_INCIDENTS_KEY] = {}
    app[SEMAPHORE_KEY] = asyncio.Semaphore(
        int(environ.get("MAX_CONCURRENT_TRIAGE", "2"))
    )
    app[ACCEPTING_KEY] = {"value": True}

    if verifier is None:
        verifier = EntraTokenVerifier(
            tenant_id=environ["ENTRA_TENANT_ID"],
            audience=environ["AUTOSOC_API_AUDIENCE"],
        )
    app[VERIFIER_KEY] = verifier

    app[RUNNER_KEY] = {
        "instance": runner,
        "factory": runner_factory or _default_runner_factory,
    }

    app.router.add_post("/api/triage", _triage)
    app.router.add_get("/api/health", _health)
    app.on_startup.append(_startup)
    app.on_shutdown.append(_shutdown)
    app.on_cleanup.append(_cleanup)
    return app


async def _startup(app: web.Application) -> None:
    """Construct the expensive model and Graph services after app startup."""
    runner_holder = app[RUNNER_KEY]
    if runner_holder["instance"] is None:
        runner_holder["instance"] = runner_holder["factory"]()
    logger.info("AutoSOC service initialized")


async def _triage(request: web.Request) -> web.Response:
    """Accept an incident and schedule autonomous triage in this process."""
    if not request.app[ACCEPTING_KEY]["value"]:
        return web.json_response({"error": "service_unavailable"}, status=503)
    if request.content_type != "application/json":
        return web.json_response({"error": "content_type_must_be_json"}, status=415)

    try:
        payload = TriageRequest.model_validate(await request.json())
    except (ValidationError, ValueError, TypeError):
        return web.json_response({"error": "invalid_request"}, status=400)

    active_incidents = request.app[ACTIVE_INCIDENTS_KEY]
    existing_correlation_id = active_incidents.get(payload.incident_id)
    if existing_correlation_id:
        acknowledgement = TriageAccepted(
            status="already_accepted",
            incidentId=payload.incident_id,
            correlationId=existing_correlation_id,
        )
        return web.json_response(acknowledgement.model_dump(by_alias=True), status=202)

    correlation_id = str(uuid4())
    active_incidents[payload.incident_id] = correlation_id
    task = asyncio.create_task(
        _run_triage(request.app, payload.incident_id, correlation_id),
        name=f"triage:{payload.incident_id}:{correlation_id}",
    )
    request.app[TRIAGE_TASKS_KEY].add(task)
    task.add_done_callback(
        lambda completed: _complete_task(
            request.app, payload.incident_id, correlation_id, completed
        )
    )

    acknowledgement = TriageAccepted(
        incidentId=payload.incident_id,
        correlationId=correlation_id,
    )
    return web.json_response(acknowledgement.model_dump(by_alias=True), status=202)


async def _run_triage(
    app: web.Application,
    incident_id: str,
    correlation_id: str,
) -> None:
    """Run accepted work under the process concurrency bound."""
    logger.info(
        "Triage accepted incident_id=%s correlation_id=%s",
        incident_id,
        correlation_id,
    )
    async with app[SEMAPHORE_KEY]:
        await app[RUNNER_KEY]["instance"].run_triage(incident_id, correlation_id)


def _complete_task(
    app: web.Application,
    incident_id: str,
    correlation_id: str,
    task: asyncio.Task[None],
) -> None:
    """Consume task failures and release process-local deduplication state."""
    app[TRIAGE_TASKS_KEY].discard(task)
    if app[ACTIVE_INCIDENTS_KEY].get(incident_id) == correlation_id:
        app[ACTIVE_INCIDENTS_KEY].pop(incident_id, None)
    try:
        task.result()
    except asyncio.CancelledError:
        logger.warning(
            "Triage cancelled incident_id=%s correlation_id=%s",
            incident_id,
            correlation_id,
        )
    except Exception:
        logger.exception(
            "Triage failed incident_id=%s correlation_id=%s",
            incident_id,
            correlation_id,
        )
    else:
        logger.info(
            "Triage completed incident_id=%s correlation_id=%s",
            incident_id,
            correlation_id,
        )


async def _health(request: web.Request) -> web.Response:
    """Report process readiness without exposing task or incident details."""
    return web.json_response(
        {
            "status": "ok" if request.app[ACCEPTING_KEY]["value"] else "stopping",
            "activeTriageCount": len(request.app[ACTIVE_INCIDENTS_KEY]),
        }
    )


async def _shutdown(app: web.Application) -> None:
    """Stop accepting work and give accepted triage tasks time to finish."""
    app[ACCEPTING_KEY]["value"] = False
    tasks = set(app[TRIAGE_TASKS_KEY])
    if not tasks:
        return

    timeout = float(environ.get("TRIAGE_SHUTDOWN_TIMEOUT_SECONDS", "60"))
    done, pending = await asyncio.wait(tasks, timeout=timeout)
    logger.info("Shutdown drained %d triage tasks; cancelling %d", len(done), len(pending))
    for task in pending:
        task.cancel()
    if pending:
        await asyncio.gather(*pending, return_exceptions=True)


async def _cleanup(app: web.Application) -> None:
    """Release resources owned by the production triage runner."""
    runner = app[RUNNER_KEY]["instance"]
    if runner is not None:
        await runner.close()


def _default_runner_factory() -> TriageRunner:
    """Load the production runner lazily to keep HTTP tests isolated."""
    from agent import AutoSOCAgent

    return AutoSOCAgent()


def main() -> None:
    """Start the AutoSOC webhook server."""
    web.run_app(
        create_app(),
        host=environ.get("HOST", "0.0.0.0"),
        port=int(environ.get("PORT", "3978")),
        handle_signals=True,
    )


if __name__ == "__main__":
    main()

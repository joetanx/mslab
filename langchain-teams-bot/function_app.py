"""Azure Functions v2 entry point for the Teams LangChain bot.

The single HTTP trigger at POST /api/messages receives all incoming Teams
activities (messages, conversation-update events, invoke payloads, etc.) and
forwards them to the Microsoft 365 Agents SDK via a minimal aiohttp-compatible
request shim.  The SDK handles JWT validation, activity dispatching, and reply
delivery back to Teams through the Bot Connector service.
"""

import logging

import azure.functions as func

from bot import ADAPTER, AGENT_APP

# ---------------------------------------------------------------------------
# SDK log configuration (INFO shows authentication + activity events)
# ---------------------------------------------------------------------------
_sdk_logger = logging.getLogger("microsoft_agents")
if not _sdk_logger.handlers:
    _sdk_logger.addHandler(logging.StreamHandler())
_sdk_logger.setLevel(
    logging.getLevelName(
        __import__("os").environ.get("AGENTS_SDK_LOG_LEVEL", "WARNING")
    )
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Minimal aiohttp.Request shim
# ---------------------------------------------------------------------------
# start_agent_process (microsoft_agents.hosting.aiohttp) only reads
# req.json() and req.headers from the request object, so a small duck-typed
# shim is sufficient to bridge Azure Functions HttpRequest to the SDK.


class _CIHeaders:
    """Case-insensitive read-only dict wrapper (approximates aiohttp headers)."""

    def __init__(self, raw):
        self._data = {k.lower(): v for k, v in raw.items()}

    def get(self, key: str, default: str = "") -> str:
        return self._data.get(key.lower(), default)

    def __getitem__(self, key: str) -> str:
        return self._data[key.lower()]

    def __contains__(self, key: str) -> bool:
        return key.lower() in self._data


class _FuncRequest:
    """Duck-typed shim that lets start_agent_process consume an Azure Functions request."""

    def __init__(self, body: dict, headers):
        self._body = body
        self.headers = _CIHeaders(headers)

    async def json(self) -> dict:
        return self._body


# ---------------------------------------------------------------------------
# Azure Functions app and trigger
# ---------------------------------------------------------------------------

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)


@app.route(route="messages", methods=["POST"])
async def messages(req: func.HttpRequest) -> func.HttpResponse:
    """Handle all incoming Teams bot activities at POST /api/messages."""
    # Import here to avoid a circular import at module load time.
    from microsoft_agents.hosting.aiohttp import start_agent_process  # noqa: PLC0415

    try:
        body = req.get_json()
    except ValueError:
        logger.warning("Received request with non-JSON body")
        return func.HttpResponse("Invalid JSON body", status_code=400)

    mock_req = _FuncRequest(body, req.headers)

    try:
        # start_agent_process validates the JWT bearer token, creates the
        # Activity, and dispatches to the registered AGENT_APP handlers.
        # The SDK sends replies back to Teams through the Bot Connector
        # service; the HTTP response here is just an acknowledgement.
        await start_agent_process(mock_req, AGENT_APP, ADAPTER)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Error processing Teams activity: %s", exc)
        return func.HttpResponse("Internal Server Error", status_code=500)

    return func.HttpResponse(status_code=200)

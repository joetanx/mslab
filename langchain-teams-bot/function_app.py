import logging
import os

import azure.functions as func
from microsoft_agents.hosting.aiohttp import start_agent_process

from bot import ADAPTER, AGENT_APP

_sdk_logger = logging.getLogger('microsoft_agents')
_sdk_logger.setLevel(
    logging.getLevelName(
        os.environ.get('AGENTS_SDK_LOG_LEVEL', 'WARNING')
    )
)

logger = logging.getLogger(__name__)

class _CIHeaders:
    # Case-insensitive header mapping compatible with the aiohttp request interface.

    def __init__(self, raw):
        self._data = {k.lower(): v for k, v in raw.items()}

    def get(self, key: str, default: str = '') -> str:
        return self._data.get(key.lower(), default)

    def __getitem__(self, key: str) -> str:
        return self._data[key.lower()]

    def __contains__(self, key: str) -> bool:
        return key.lower() in self._data

class _FuncRequest:
    # Minimal aiohttp-style request shim wrapping an Azure Functions HttpRequest.
    # Exposes only the interface required by start_agent_process: headers (case-insensitive), json(), method, and get().
    # Query-string access via get() returns None because the agent SDK does not use query parameters.

    method = 'POST'

    def __init__(self, body: dict, headers):
        self._body = body
        self.headers = _CIHeaders(headers)

    def get(self, key: str, default=None):
        # Return None for all query-string keys (not used by the agent SDK).
        return default

    async def json(self) -> dict:
        # Return the pre-parsed JSON body.
        return self._body

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

@app.route(route='messages', methods=['POST'])
async def messages(req: func.HttpRequest) -> func.HttpResponse:
    # Azure Functions HTTP trigger that forwards Teams activity payloads to the agent.
    # Authentication is handled by the Microsoft Agents SDK (JWT validation), so the function endpoint is intentionally exposed at AuthLevel.ANONYMOUS.

    logger.debug(f"Received POST /messages (content-type={req.headers.get('content-type', '')}, user-agent={req.headers.get('user-agent', '')})")

    try:
        body = req.get_json()
    except ValueError:
        logger.warning('Rejected request: non-JSON body')
        return func.HttpResponse('Invalid JSON body', status_code=400)

    activity_type = body.get('type', '<unknown>') if isinstance(body, dict) else '<non-dict>'
    logger.info(f"Processing Teams activity type={activity_type}")

    mock_req = _FuncRequest(body, req.headers)

    try:
        # start_agent_process validates the JWT bearer token, creates the Activity, and dispatches to the registered AGENT_APP handlers.
        # The SDK sends replies back to Teams through the Bot Connector service; the HTTP response here is just an acknowledgement.
        await start_agent_process(mock_req, AGENT_APP, ADAPTER)
    except Exception as exc:  # noqa: BLE001
        logger.exception(f"Error processing Teams activity type={activity_type}: {exc}")
        return func.HttpResponse('Internal Server Error', status_code=500)

    logger.debug(f"Successfully processed activity type={activity_type}")
    return func.HttpResponse(status_code=200)

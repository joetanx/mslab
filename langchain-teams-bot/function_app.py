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

class _func_aiohttp_shim:
    def __init__(self, body: dict, headers, method):
        self._body = body
        self.headers = headers
        self.method = method

    def get(self, key: str, default=None):
        # Return None for all query-string keys (not used by the agent SDK).
        return default

    async def json(self):
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

    try:
        # start_agent_process validates the JWT bearer token, creates the Activity, and dispatches to the registered AGENT_APP handlers.
        # The SDK sends replies back to Teams through the Bot Connector service; the HTTP response here is just an acknowledgement.
        await start_agent_process(
            request=_func_aiohttp_shim(body, req.headers, req.method),
            agent_application=AGENT_APP,
            adapter=ADAPTER
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception(f"Error processing Teams activity type={activity_type}: {exc}")
        return func.HttpResponse('Internal Server Error', status_code=500)

    logger.debug(f"Successfully processed activity type={activity_type}")
    return func.HttpResponse(status_code=200)

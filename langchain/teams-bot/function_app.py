import logging
from os import environ

import azure.functions as func
from microsoft_agents.hosting.aiohttp import start_agent_process

from bot import ADAPTER, AGENT_APP

logging.getLogger('microsoft_agents').setLevel(
    logging.getLevelName(environ.get('AGENTS_SDK_LOG_LEVEL', 'WARNING'))
)

logger = logging.getLogger(__name__)

class FunctionRequestShim:
    # Minimal shim to make Azure Functions HttpRequest compatible
    # with the Microsoft Agents SDK aiohttp-style request expectation.

    def __init__(self, body: dict, headers, method: str):
        self._body = body
        self.headers = headers
        self.method = method

    def get(self, key: str, default=None):
        # Query-string lookup is not required by the Agents SDK path here.
        return default

    async def json(self):
        return self._body

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

@app.route(route='messages', methods=['POST'])
async def messages(req: func.HttpRequest) -> func.HttpResponse:
    # Azure Functions HTTP trigger for Teams messages.
    # Anonymous auth because Agents SDK performs JWT validation internally.

    body = req.get_json()
    logger.info(f"Processing activity type={body.get('type')}")

    await start_agent_process(
        request=FunctionRequestShim(body, req.headers, req.method),
        agent_application=AGENT_APP,
        adapter=ADAPTER
    )

    return func.HttpResponse(status_code=200)

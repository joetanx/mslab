from aiohttp import web
import json

async def whoami(request: web.Request) -> web.Response:
    data = {
        "method": request.method,
        "path": str(request.rel_url),
        "remote": request.remote,
        "headers": dict(request.headers),
        "query": dict(request.rel_url.query),
    }
    return web.Response(
        text=json.dumps(data, indent=2),
        content_type="application/json",
    )

async def health(health):
    return web.json_response({"status": "running", "framework": "aiohttp"})

app = web.Application()
app.router.add_route("*", "/whoami", whoami)
app.router.add_route("*", "/health", health)

if __name__ == "__main__":
    # ACA requires binding to 0.0.0.0
    web.run_app(app, host="0.0.0.0", port=8080)

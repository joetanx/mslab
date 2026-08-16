import asyncio

from aiohttp.test_utils import TestClient, TestServer

from server import ACTIVE_INCIDENTS_KEY, TRIAGE_TASKS_KEY, create_app


class FakeVerifier:
    async def verify(self, token):
        if token != "valid":
            raise AssertionError("unexpected test token")
        return object()


class BlockingRunner:
    def __init__(self):
        self.started = asyncio.Event()
        self.release = asyncio.Event()
        self.calls = []
        self.closed = False

    async def run_triage(self, incident_id, correlation_id):
        self.calls.append((incident_id, correlation_id))
        self.started.set()
        await self.release.wait()

    async def close(self):
        self.closed = True


async def test_triage_returns_202_before_background_completion_and_deduplicates():
    runner = BlockingRunner()
    app = create_app(runner=runner, verifier=FakeVerifier())
    client = TestClient(TestServer(app))
    await client.start_server()
    try:
        health = await client.get("/api/health")
        assert health.status == 200

        unauthorized = await client.post("/api/triage", json={"incidentId": "42"})
        assert unauthorized.status == 401

        headers = {"Authorization": "Bearer valid"}
        accepted = await client.post(
            "/api/triage", json={"incidentId": "42"}, headers=headers
        )
        assert accepted.status == 202
        body = await accepted.json()
        await asyncio.wait_for(runner.started.wait(), timeout=1)
        assert not runner.release.is_set()

        duplicate = await client.post(
            "/api/triage", json={"incidentId": "42"}, headers=headers
        )
        duplicate_body = await duplicate.json()
        assert duplicate.status == 202
        assert duplicate_body["status"] == "already_accepted"
        assert duplicate_body["correlationId"] == body["correlationId"]

        runner.release.set()
        for _ in range(20):
            if not app[TRIAGE_TASKS_KEY]:
                break
            await asyncio.sleep(0)
        assert not app[TRIAGE_TASKS_KEY]
        assert not app[ACTIVE_INCIDENTS_KEY]
    finally:
        runner.release.set()
        await client.close()
    assert runner.closed


async def test_rejects_non_json_and_unknown_fields():
    runner = BlockingRunner()
    client = TestClient(TestServer(create_app(runner=runner, verifier=FakeVerifier())))
    await client.start_server()
    headers = {"Authorization": "Bearer valid"}
    try:
        response = await client.post("/api/triage", data="42", headers=headers)
        assert response.status == 415
        response = await client.post(
            "/api/triage",
            json={"incidentId": "42", "unexpected": True},
            headers=headers,
        )
        assert response.status == 400
    finally:
        await client.close()

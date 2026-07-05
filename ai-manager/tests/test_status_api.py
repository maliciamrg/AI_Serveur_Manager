import pytest


@pytest.mark.asyncio
async def test_health_is_public(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_status_requires_auth(client):
    response = await client.get("/status")
    assert response.status_code == 401


class FailingSSHService:
    async def run_command(self, command: str, use_sudo: bool = False):  # noqa: ARG002
        raise FileNotFoundError("missing key")


@pytest.mark.asyncio
async def test_shutdown_returns_error_payload_when_ssh_key_missing(app, client):
    login = await client.post("/login", data={"username": "admin", "password": "password"}, follow_redirects=False)
    assert login.status_code == 303
    app.state.container.server_control_service.ssh_service = FailingSSHService()
    response = await client.post("/server/shutdown")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "error"
    assert "SSH key file not found" in payload["message"]

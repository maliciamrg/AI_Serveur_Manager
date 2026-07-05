import pytest


@pytest.mark.asyncio
async def test_login_logout_flow(client):
    response = await client.post("/login", data={"username": "admin", "password": "password"}, follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/"

    page = await client.get("/")
    assert page.status_code == 200
    assert "AI Manager".lower() in page.text.lower()

    logout_response = await client.post("/logout", follow_redirects=False)
    assert logout_response.status_code == 303
    assert logout_response.headers["location"] == "/login"


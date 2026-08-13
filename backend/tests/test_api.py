from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app


def auth_headers(client: TestClient) -> dict:
    login = client.post("/api/auth/login", json={"email": "admin@example.com", "password": "change-this-before-production"})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_health():
    with TestClient(app) as client:
        assert client.get("/health").json() == {"status": "ok"}


def test_project_task_lifecycle(tmp_path: Path):
    repo = tmp_path / "fixture"; repo.mkdir()
    (repo / "main.py").write_text("from fastapi import FastAPI\napp = FastAPI()\n")
    (repo / "requirements.txt").write_text("fastapi\n")
    with TestClient(app) as client:
        headers = auth_headers(client)
        project = client.post("/api/projects", json={"repository_url": str(repo)}, headers=headers).json()
        analysis = client.post("/api/analyze", json={"project_id": project["id"]}, headers=headers)
        assert analysis.status_code == 200 and analysis.json()["framework"] == "FastAPI/Python"
        task = client.post("/api/tasks", json={"project_id": project["id"], "request": "Add a health-check endpoint to this FastAPI application."}, headers=headers).json()
        run = client.post(f"/api/tasks/{task['id']}/run", headers=headers)
        assert run.status_code == 202
        # TestClient completes background tasks before returning.
        assert client.get(f"/api/tasks/{task['id']}", headers=headers).json()["status"] == "completed"
        changes = client.get(f"/api/tasks/{task['id']}/changes", headers=headers).json()
        assert changes and changes[0]["path"] == "main.py"

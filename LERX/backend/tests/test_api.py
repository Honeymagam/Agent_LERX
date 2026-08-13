from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app


def test_health():
    with TestClient(app) as client:
        assert client.get("/health").json() == {"status": "ok"}


def test_project_task_lifecycle(tmp_path: Path):
    repo = tmp_path / "fixture"; repo.mkdir()
    (repo / "main.py").write_text("from fastapi import FastAPI\napp = FastAPI()\n")
    (repo / "requirements.txt").write_text("fastapi\n")
    with TestClient(app) as client:
        project = client.post("/api/projects", json={"repository_url": str(repo)}).json()
        analysis = client.post("/api/analyze", json={"project_id": project["id"]})
        assert analysis.status_code == 200 and analysis.json()["framework"] == "FastAPI/Python"
        task = client.post("/api/tasks", json={"project_id": project["id"], "request": "Add a health-check endpoint to this FastAPI application."}).json()
        run = client.post(f"/api/tasks/{task['id']}/run")
        assert run.status_code == 202
        # TestClient completes background tasks before returning.
        assert client.get(f"/api/tasks/{task['id']}").json()["status"] == "completed"
        changes = client.get(f"/api/tasks/{task['id']}/changes").json()
        assert changes and changes[0]["path"] == "main.py"

import importlib.util
import os

from fastapi.testclient import TestClient

root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
app_main_path = os.path.join(root, "app", "main.py")
spec = importlib.util.spec_from_file_location("local_app_main", app_main_path)
local_app = importlib.util.module_from_spec(spec)
loader = spec.loader
if loader is None:
    raise RuntimeError("Cannot load local app.main")
loader.exec_module(local_app)
app = getattr(local_app, "app")


def test_dashboard_catalog_and_episode_run():
    with TestClient(app) as client:
        summary = client.get("/api/dashboard/summary")
        assert summary.status_code == 200
        assert summary.json()["episodes"] >= 6

        catalog = client.get("/api/dashboard/catalog")
        assert catalog.status_code == 200
        payload = catalog.json()
        assert "episodes" in payload
        assert "agents" in payload
        assert "workflows" in payload

        run = client.post("/api/dashboard/run/episode-4", json={"text": "reservation for two"})
        assert run.status_code == 200
        result = run.json()
        assert result["episode_id"] == "episode-4"
        assert result["response"]["intent"] == "reservation"

import sys
import os
import importlib.util
from fastapi.testclient import TestClient

# Load local app/main.py directly to avoid package name collisions
root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
app_main_path = os.path.join(root, 'app', 'main.py')
spec = importlib.util.spec_from_file_location('local_app_main', app_main_path)
local_app = importlib.util.module_from_spec(spec)
loader = spec.loader
if loader is None:
    raise RuntimeError('Cannot load local app.main')
loader.exec_module(local_app)
app = getattr(local_app, 'app')


def test_health():
    with TestClient(app) as client:
        r = client.get('/health')
        assert r.status_code == 200
        j = r.json()
        assert j.get('status') == 'ok'

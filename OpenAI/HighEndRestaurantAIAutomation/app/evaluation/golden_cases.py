from __future__ import annotations

import json
from pathlib import Path


def load_golden_cases() -> list[dict]:
    path = Path(__file__).resolve().parents[2] / "evals" / "restaurant_test_cases.json"
    if not path.exists():
        return []
    return json.loads(path.read_text())

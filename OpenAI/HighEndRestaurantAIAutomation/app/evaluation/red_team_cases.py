from __future__ import annotations

import json
from pathlib import Path


def load_red_team_cases() -> list[dict]:
    path = Path(__file__).resolve().parents[2] / "evals" / "red_team_prompts.json"
    if not path.exists():
        return []
    return json.loads(path.read_text())

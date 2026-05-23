from __future__ import annotations


def compute_summary(results: list[dict]) -> dict:
    scenario_count = len(results)
    pass_count = sum(1 for item in results if item["result"] == "pass")
    fail_count = scenario_count - pass_count
    tool_calls = sum(item.get("tool_calls", 0) for item in results)
    blocked_count = sum(1 for item in results if item.get("safety_decision") == "block")
    pass_rate = pass_count / scenario_count if scenario_count else 0.0
    return {
        "scenario_count": scenario_count,
        "pass_count": pass_count,
        "fail_count": fail_count,
        "pass_rate": pass_rate,
        "tool_calls": tool_calls,
        "blocked_count": blocked_count,
        "results": results,
    }

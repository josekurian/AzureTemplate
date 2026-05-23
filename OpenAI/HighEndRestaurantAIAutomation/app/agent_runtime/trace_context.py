from __future__ import annotations

from collections import defaultdict
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


_current_trace_id: ContextVar[str | None] = ContextVar("current_trace_id", default=None)
_traces: dict[str, list[dict[str, Any]]] = defaultdict(list)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def start_trace(name: str, metadata: dict[str, Any] | None = None) -> str:
    trace_id = str(uuid4())
    _current_trace_id.set(trace_id)
    add_event("trace", "started", {"name": name, **(metadata or {})}, trace_id=trace_id)
    return trace_id


def current_trace_id() -> str | None:
    return _current_trace_id.get()


def set_current_trace(trace_id: str) -> None:
    _current_trace_id.set(trace_id)


def add_event(component: str, event: str, details: dict[str, Any] | None = None, trace_id: str | None = None) -> None:
    active_trace = trace_id or current_trace_id() or start_trace("implicit")
    _traces[active_trace].append(
        {
            "timestamp": utc_now(),
            "component": component,
            "event": event,
            "details": details or {},
        }
    )


def finish_trace(status: str, details: dict[str, Any] | None = None) -> str | None:
    trace_id = current_trace_id()
    if trace_id:
        add_event("trace", "finished", {"status": status, **(details or {})}, trace_id=trace_id)
    return trace_id


def get_trace(trace_id: str) -> list[dict[str, Any]]:
    return list(_traces.get(trace_id, []))

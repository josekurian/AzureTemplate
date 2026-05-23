from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.agent_runtime.trace_context import add_event


@dataclass
class AgentContext:
    session_id: str | None
    trace_id: str
    actor_role: str
    message: str
    language: str = "en"
    guest_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentStep:
    agent: str
    action: str
    status: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolCallRecord:
    tool_name: str
    status: str
    actor_role: str
    result: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResult:
    agent_name: str
    answer: str
    safety_decision: str = "allow"
    sources: list[str] = field(default_factory=list)
    steps: list[AgentStep] = field(default_factory=list)
    tool_calls: list[ToolCallRecord] = field(default_factory=list)
    approvals_requested: list[str] = field(default_factory=list)
    data: dict[str, Any] = field(default_factory=dict)


class BaseAgent:
    name = "base_agent"
    allowed_tools: tuple[str, ...] = ()

    def __init__(self, tool_registry) -> None:
        self.tool_registry = tool_registry

    def step(self, action: str, status: str, details: dict[str, Any] | None = None) -> AgentStep:
        add_event(self.name, action, {"status": status, **(details or {})})
        return AgentStep(agent=self.name, action=action, status=status, details=details or {})

    async def call_tool(self, context: AgentContext, tool_name: str, payload: dict[str, Any]) -> ToolCallRecord:
        result = await self.tool_registry.invoke(tool_name, context.actor_role, payload)
        return ToolCallRecord(tool_name=tool_name, status="success", actor_role=context.actor_role, result=result)

    async def run(self, context: AgentContext) -> AgentResult:
        raise NotImplementedError

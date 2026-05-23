from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from pydantic import BaseModel, ValidationError

from app.agent_runtime.policies import can_use_tool
from app.agent_runtime.trace_context import add_event


ToolHandler = Callable[[BaseModel], Awaitable[dict[str, Any]]]


@dataclass
class ToolDefinition:
    name: str
    description: str
    schema_model: type[BaseModel]
    handler: ToolHandler


class ToolPermissionError(PermissionError):
    pass


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, definition: ToolDefinition) -> None:
        self._tools[definition.name] = definition

    def list_tools(self) -> list[dict[str, str]]:
        return [
            {"name": tool.name, "description": tool.description}
            for tool in self._tools.values()
        ]

    async def invoke(self, tool_name: str, actor_role: str, payload: dict[str, Any]) -> dict[str, Any]:
        if tool_name not in self._tools:
            raise KeyError(f"Unknown tool: {tool_name}")
        if not can_use_tool(actor_role, tool_name):
            raise ToolPermissionError(f"Role {actor_role} cannot use tool {tool_name}")
        definition = self._tools[tool_name]
        try:
            args = definition.schema_model(**payload)
        except ValidationError as exc:
            add_event("tool_registry", "validation_failed", {"tool_name": tool_name, "errors": exc.errors()})
            raise
        add_event("tool_registry", "invoke", {"tool_name": tool_name, "actor_role": actor_role, "payload": payload})
        result = await definition.handler(args)
        add_event("tool_registry", "result", {"tool_name": tool_name, "actor_role": actor_role, "result": result})
        return result

"""Tool-call executor that delegates execution to application tools."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from skill_adapter.exceptions import SkillExecutionError
from skill_adapter.executors.base import SkillExecutor
from skill_adapter.models import (
    SkillError,
    SkillExecutionRequest,
    SkillExecutionResult,
    SkillSpec,
)


class ToolCallExecutor(SkillExecutor):
    """Execute a skill by calling an application-provided tool."""

    def __init__(self, tool_resolver: Callable[[str], Any]) -> None:
        self._tool_resolver = tool_resolver

    def execute(
        self, skill_spec: SkillSpec, request: SkillExecutionRequest
    ) -> SkillExecutionResult:
        tool = self._tool_resolver(skill_spec.name)
        if tool is None:
            raise SkillExecutionError(f"No tool mapped for skill '{skill_spec.name}'")

        try:
            output = self._invoke_tool(tool, request.input_data)
        except Exception as exc:  # pragma: no cover - defensive wrapper
            return SkillExecutionResult(
                skill_name=skill_spec.name,
                status="error",
                error=SkillError(
                    code="TOOL_EXECUTION_FAILED",
                    message=f"Tool execution failed for skill '{skill_spec.name}'",
                    details={"exception_type": exc.__class__.__name__},
                ),
                metadata={"mode": request.mode, "tool_name": self._tool_name(tool)},
            )

        return SkillExecutionResult(
            skill_name=skill_spec.name,
            status="success",
            output=output,
            metadata={"mode": request.mode, "tool_name": self._tool_name(tool)},
        )

    def _invoke_tool(self, tool: Any, input_data: Any) -> Any:
        if hasattr(tool, "invoke"):
            return tool.invoke(input_data)
        if callable(tool):
            return tool(input_data)
        raise SkillExecutionError("Tool must be callable or expose .invoke(...)")

    def _tool_name(self, tool: Any) -> str:
        name = getattr(tool, "name", None)
        if isinstance(name, str) and name.strip():
            return name
        return tool.__class__.__name__

"""LangGraph-oriented helper utilities."""

from __future__ import annotations

from typing import Any

from skill_adapter.models import SkillExecutionResult
from skill_adapter.registry import SkillRegistry


def execute_skill(
    registry: SkillRegistry,
    *,
    skill_name: str,
    input_data: Any,
    context: dict[str, Any] | None = None,
    mode: str = "tool_call",
) -> SkillExecutionResult:
    """Convenience helper for LangGraph node functions."""
    return registry.execute_by_name(
        skill_name,
        input_data,
        context=context or {},
        mode=mode,
    )

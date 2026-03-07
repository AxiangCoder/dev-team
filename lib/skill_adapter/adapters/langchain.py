"""LangChain adapter helpers for skill registry integration."""

from __future__ import annotations

from typing import Any

from skill_adapter.exceptions import SkillImportError
from skill_adapter.registry import SkillRegistry


def build_skills_prompt(registry: SkillRegistry, title: str = "Available skills:") -> str:
    """Build a concise prompt from registered skills."""
    return registry.build_skills_prompt(title=title)


def to_langchain_tool(
    registry: SkillRegistry, skill_name: str, *, mode: str = "tool_call"
) -> Any:
    """Wrap one registered skill as a LangChain tool."""
    try:
        from langchain_core.tools import tool
    except Exception as exc:  # pragma: no cover - optional dependency guard
        raise SkillImportError(
            "LangChain is not installed. Install langchain-core to use adapters."
        ) from exc

    spec = registry.get(skill_name)
    description = spec.description or f"Skill wrapper for '{skill_name}'."

    @tool(skill_name, description=description)
    def _skill_tool(payload: dict[str, Any]) -> dict[str, Any]:
        result = registry.execute_by_name(
            skill_name,
            payload,
            context={},
            mode=mode,
        )
        return {
            "status": result.status,
            "output": result.output,
            "error": result.error.message if result.error else None,
            "metadata": result.metadata,
        }

    return _skill_tool

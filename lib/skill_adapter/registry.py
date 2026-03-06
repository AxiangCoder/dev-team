"""Skill registry implementation with middleware pipeline support."""

from __future__ import annotations

from typing import Any, Literal

from skill_adapter.exceptions import (
    SkillConflictError,
    SkillExecutionError,
    SkillNotFoundError,
)
from skill_adapter.middleware import SkillInvoker, SkillMiddleware
from skill_adapter.models import (
    SkillExecutionRequest,
    SkillExecutionResult,
    SkillRuntime,
)

ConflictPolicy = Literal["error", "override", "keep_existing"]


class SkillRegistry:
    """Store and execute skills with deterministic conflict handling."""

    def __init__(self, conflict_policy: ConflictPolicy = "error") -> None:
        """Initialize registry with duplicate-name conflict policy."""
        self._skills: dict[str, SkillRuntime] = {}
        self._middlewares: list[SkillMiddleware] = []
        self._conflict_policy = conflict_policy

    def register(self, runtime: SkillRuntime) -> None:
        """Register one runtime skill into the registry."""
        existing = self._skills.get(runtime.name)
        if existing is not None:
            if self._conflict_policy == "error":
                raise SkillConflictError(f"Skill '{runtime.name}' already registered")
            if self._conflict_policy == "keep_existing":
                return
        self._skills[runtime.name] = runtime

    def register_many(self, runtimes: list[SkillRuntime]) -> None:
        """Register multiple skill runtimes."""
        for runtime in runtimes:
            self.register(runtime)

    def unregister(self, skill_name: str) -> None:
        """Unregister a skill if it exists."""
        self._skills.pop(skill_name, None)

    def list_skills(self) -> list[str]:
        """List registered skill names in sorted order."""
        return sorted(self._skills.keys())

    def get_skill(self, skill_name: str) -> SkillRuntime:
        """Get one registered skill runtime by name."""
        if skill_name not in self._skills:
            available = ", ".join(self.list_skills()) or "none"
            raise SkillNotFoundError(
                f"Skill '{skill_name}' not found. Available skills: {available}"
            )
        return self._skills[skill_name]

    def build_skills_prompt(self, title: str = "Available skills:") -> str:
        """Build a concise prompt section from registered skill descriptions."""
        lines = [title]
        for skill_name in self.list_skills():
            runtime = self._skills[skill_name]
            description = runtime.description.strip() or "No description."
            lines.append(f"- {runtime.name}: {description}")
        return "\n".join(lines)

    def use(self, middleware: SkillMiddleware) -> None:
        """Append one middleware into the execution pipeline."""
        self._middlewares.append(middleware)

    def execute(
        self,
        skill_name: str,
        input_data: Any,
        # context: dict[str, Any] | None = None,
        context: Any,
    ) -> SkillExecutionResult:
        """Execute one skill by name with middleware and typed response."""
        if skill_name not in self._skills:
            available = ", ".join(self.list_skills()) or "none"
            raise SkillNotFoundError(
                f"Skill '{skill_name}' not found. Available skills: {available}"
            )

        request = SkillExecutionRequest(
            skill_name=skill_name,
            input_data=input_data,
            context=context,
        )

        invoker = self._build_invoker()
        return invoker(request)

    def _build_invoker(self) -> SkillInvoker:
        def _base_invoker(request: SkillExecutionRequest) -> SkillExecutionResult:
            runtime = self._skills[request.skill_name]
            try:
                output = runtime.handler(request.input_data)
            except Exception as exc:  # pragma: no cover - defensive wrapper
                raise SkillExecutionError(
                    f"Execution failed for skill '{request.skill_name}'"
                ) from exc

            return SkillExecutionResult(
                skill_name=request.skill_name,
                output=output,
                status="success",
                metadata={
                    "skill_description": runtime.description,
                    **runtime.metadata,
                },
            )

        invoker = _base_invoker
        for middleware in reversed(self._middlewares):
            invoker = middleware.wrap(invoker)
        return invoker

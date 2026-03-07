"""Skill registry implementation with middleware and executor routing."""

from __future__ import annotations

from typing import Any, Literal

from skill_adapter.exceptions import (
    SkillConfigurationError,
    SkillConflictError,
    SkillNotFoundError,
    SkillPermissionError,
    SkillValidationError,
)
from skill_adapter.executors.base import SkillExecutor
from skill_adapter.middleware import SkillInvoker, SkillMiddleware
from skill_adapter.models import (
    SkillError,
    SkillExecutionRequest,
    SkillExecutionResult,
    SkillSpec,
)

ConflictPolicy = Literal["error", "override", "keep_existing"]
_VALID_CONFLICT_POLICIES: set[str] = {"error", "override", "keep_existing"}


class SkillRegistry:
    """Store and execute skills with deterministic conflict handling."""

    def __init__(self, conflict_policy: ConflictPolicy = "error") -> None:
        if conflict_policy not in _VALID_CONFLICT_POLICIES:
            raise SkillConfigurationError(
                f"Invalid conflict policy '{conflict_policy}'. "
                f"Expected one of: {sorted(_VALID_CONFLICT_POLICIES)}"
            )
        self._skills: dict[str, SkillSpec] = {}
        self._middlewares: list[SkillMiddleware] = []
        self._executors: dict[str, SkillExecutor] = {}
        self._conflict_policy = conflict_policy

    def register(self, spec: SkillSpec) -> None:
        """Register one skill spec into the registry."""
        existing = self._skills.get(spec.name)
        if existing is not None:
            if self._conflict_policy == "error":
                raise SkillConflictError(f"Skill '{spec.name}' already registered")
            if self._conflict_policy == "keep_existing":
                return
        self._skills[spec.name] = spec

    def register_many(self, specs: list[SkillSpec]) -> None:
        """Register multiple skill specs."""
        for spec in specs:
            self.register(spec)

    def unregister(self, skill_name: str) -> None:
        """Unregister a skill if it exists."""
        self._skills.pop(skill_name, None)

    def list(self) -> list[str]:
        """List registered skill names in sorted order."""
        return sorted(self._skills.keys())

    def list_skills(self) -> list[str]:
        """Backward-compatible alias for list()."""
        return self.list()

    def get(self, skill_name: str) -> SkillSpec:
        """Get one registered skill spec by name."""
        if skill_name not in self._skills:
            available = ", ".join(self.list()) or "none"
            raise SkillNotFoundError(
                f"Skill '{skill_name}' not found. Available skills: {available}"
            )
        return self._skills[skill_name]

    def get_skill(self, skill_name: str) -> SkillSpec:
        """Backward-compatible alias for get()."""
        return self.get(skill_name)

    def build_skills_prompt(self, title: str = "Available skills:") -> str:
        """Build a concise prompt section from registered skill descriptions."""
        lines = [title]
        for skill_name in self.list():
            spec = self._skills[skill_name]
            description = spec.description.strip() or "No description."
            lines.append(f"- {spec.name}: {description}")
        return "\n".join(lines)

    def add_executor(self, mode: str, executor: SkillExecutor) -> None:
        """Register one executor for a named execution mode."""
        normalized_mode = mode.strip()
        if not normalized_mode:
            raise SkillConfigurationError("Execution mode must not be empty")
        self._executors[normalized_mode] = executor

    def use(self, middleware: SkillMiddleware) -> None:
        """Append one middleware into the execution pipeline."""
        self._middlewares.append(middleware)

    def execute(
        self,
        request_or_skill_name: SkillExecutionRequest | str,
        input_data: Any | None = None,
        context: dict[str, Any] | None = None,
        mode: str = "tool_call",
    ) -> SkillExecutionResult:
        """Execute one skill request with middleware and mode-specific executor."""
        request = self._to_request(
            request_or_skill_name=request_or_skill_name,
            input_data=input_data,
            context=context,
            mode=mode,
        )

        invoker = self._build_invoker()
        try:
            return invoker(request)
        except SkillNotFoundError as exc:
            return self._error_result(request, "SKILL_NOT_FOUND", str(exc))
        except SkillPermissionError as exc:
            return self._error_result(request, "SKILL_PERMISSION_DENIED", str(exc))
        except SkillValidationError as exc:
            return self._error_result(request, "SKILL_VALIDATION_ERROR", str(exc))
        except SkillConfigurationError as exc:
            return self._error_result(request, "CONFIGURATION_ERROR", str(exc))
        except Exception as exc:  # pragma: no cover - defensive wrapper
            return self._error_result(
                request,
                "EXECUTION_ERROR",
                f"Execution failed for skill '{request.skill_name}'",
                {"exception_type": exc.__class__.__name__},
            )

    def execute_by_name(
        self,
        skill_name: str,
        input_data: Any,
        *,
        context: dict[str, Any] | None = None,
        mode: str = "tool_call",
    ) -> SkillExecutionResult:
        """Convenience wrapper to execute skill by name."""
        return self.execute(skill_name, input_data, context=context, mode=mode)

    def _to_request(
        self,
        request_or_skill_name: SkillExecutionRequest | str,
        input_data: Any | None,
        context: dict[str, Any] | None,
        mode: str,
    ) -> SkillExecutionRequest:
        if isinstance(request_or_skill_name, SkillExecutionRequest):
            if not isinstance(request_or_skill_name.context, dict):
                raise SkillConfigurationError("Request context must be a dict")
            return request_or_skill_name

        if not isinstance(request_or_skill_name, str):
            raise SkillConfigurationError(
                "execute(...) expects SkillExecutionRequest or skill name string"
            )
        if not isinstance(context, dict) and context is not None:
            raise SkillConfigurationError("Execution context must be a dict or None")

        return SkillExecutionRequest(
            skill_name=request_or_skill_name,
            input_data=input_data,
            context=context or {},
            mode=mode,
        )

    def _build_invoker(self) -> SkillInvoker:
        def _base_invoker(request: SkillExecutionRequest) -> SkillExecutionResult:
            spec = self.get(request.skill_name)
            executor = self._executors.get(request.mode)
            if executor is None:
                raise SkillConfigurationError(
                    f"No executor registered for mode '{request.mode}'"
                )
            result = executor.execute(spec, request)
            metadata = {
                "skill_description": spec.description,
                "skill_version": spec.version,
                **spec.metadata,
                **result.metadata,
            }
            return SkillExecutionResult(
                skill_name=result.skill_name or spec.name,
                status=result.status,
                output=result.output,
                error=result.error,
                duration_ms=result.duration_ms,
                metadata=metadata,
            )

        invoker = _base_invoker
        for middleware in reversed(self._middlewares):
            invoker = middleware.wrap(invoker)
        return invoker

    def _error_result(
        self,
        request: SkillExecutionRequest,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> SkillExecutionResult:
        return SkillExecutionResult(
            skill_name=request.skill_name,
            status="error",
            error=SkillError(code=code, message=message, details=details or {}),
            metadata={"mode": request.mode},
        )

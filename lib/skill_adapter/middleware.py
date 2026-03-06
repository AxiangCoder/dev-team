"""Middleware implementations for skill execution."""

from __future__ import annotations

import time
from collections.abc import Callable

from skill_adapter.exceptions import SkillPermissionError
from skill_adapter.models import SkillExecutionRequest, SkillExecutionResult

SkillInvoker = Callable[[SkillExecutionRequest], SkillExecutionResult]


class SkillMiddleware:
    """Base middleware contract."""

    def wrap(self, invoker: SkillInvoker) -> SkillInvoker:
        """Wrap execution callable and return next callable in the chain."""
        return invoker


class PermissionMiddleware(SkillMiddleware):
    """Allow execution only when skill name appears in allowed skill context."""

    def __init__(self, allowed_skills_context_key: str = "allowed_skills") -> None:
        """Create middleware that reads allowed skills from request context."""
        self._allowed_skills_context_key = allowed_skills_context_key

    def wrap(self, invoker: SkillInvoker) -> SkillInvoker:
        """Wrap invoker with skill allow-list check."""
        def _wrapped(request: SkillExecutionRequest) -> SkillExecutionResult:
            allowed_skills = request.context.get(self._allowed_skills_context_key, [])
            if allowed_skills and request.skill_name not in set(allowed_skills):
                raise SkillPermissionError(
                    f"Skill '{request.skill_name}' is not allowed in current context"
                )
            return invoker(request)

        return _wrapped


class TimingMiddleware(SkillMiddleware):
    """Measure execution duration and annotate result and request logs."""

    def __init__(self, logs_context_key: str = "logs") -> None:
        """Create middleware that writes timing entries to context logs."""
        self._logs_context_key = logs_context_key

    def wrap(self, invoker: SkillInvoker) -> SkillInvoker:
        """Wrap invoker with duration measurement."""
        def _wrapped(request: SkillExecutionRequest) -> SkillExecutionResult:
            start = time.perf_counter()
            result = invoker(request)
            duration_ms = (time.perf_counter() - start) * 1000

            logs = request.context.setdefault(self._logs_context_key, [])
            logs.append(f"skill:{request.skill_name}:duration_ms:{duration_ms:.2f}")

            metadata = dict(result.metadata)
            metadata["duration_ms"] = duration_ms
            return SkillExecutionResult(
                skill_name=result.skill_name,
                output=result.output,
                status=result.status,
                duration_ms=duration_ms,
                metadata=metadata,
            )

        return _wrapped

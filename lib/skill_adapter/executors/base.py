"""Executor abstractions for skill execution modes."""

from __future__ import annotations

from typing import Protocol

from skill_adapter.models import SkillExecutionRequest, SkillExecutionResult, SkillSpec


class SkillExecutor(Protocol):
    """Contract for mode-specific skill executors."""

    def execute(
        self, skill_spec: SkillSpec, request: SkillExecutionRequest
    ) -> SkillExecutionResult:
        """Execute one request for one skill definition."""
        ...

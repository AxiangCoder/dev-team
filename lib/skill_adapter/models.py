"""Typed models for skill adapter components."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SkillSpec:
    """Declarative skill specification loaded from disk."""

    name: str
    description: str
    body: str
    root_path: Path
    version: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    input_schema: dict[str, Any] | None = None
    output_schema: dict[str, Any] | None = None


@dataclass(frozen=True)
class SkillError:
    """Structured error payload for skill execution failures."""

    code: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SkillExecutionRequest:
    """Request object passed through middleware and into execution."""

    skill_name: str
    input_data: Any
    context: dict[str, Any] = field(default_factory=dict)
    mode: str = "tool_call"


@dataclass(frozen=True)
class SkillExecutionResult:
    """Result object returned from registry execution."""

    skill_name: str
    status: str = "success"
    output: Any = None
    error: SkillError | None = None
    duration_ms: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

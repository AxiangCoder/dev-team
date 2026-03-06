"""Typed models for skill adapter components."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SkillHandler = Callable[[Any], Any]


@dataclass(frozen=True)
class SkillSpec:
    """Declarative skill specification loaded from disk."""

    name: str
    description: str
    skill_markdown: str
    root_path: Path
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SkillRuntime:
    """Runtime representation of a callable skill."""

    name: str
    description: str
    handler: SkillHandler
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SkillExecutionRequest:
    """Request object passed through middleware and into execution."""

    skill_name: str
    input_data: Any
    context: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SkillExecutionResult:
    """Result object returned from registry execution."""

    skill_name: str
    output: Any
    status: str = "success"
    duration_ms: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

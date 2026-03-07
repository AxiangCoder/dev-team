"""Factory helpers for creating fully configured skill registries."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from skill_adapter.executors.base import SkillExecutor
from skill_adapter.loader import SkillLoader
from skill_adapter.middleware import (
    PermissionMiddleware,
    SkillMiddleware,
    TimingMiddleware,
    ValidationMiddleware,
)
from skill_adapter.registry import SkillRegistry

ConflictPolicy = Literal["error", "override", "keep_existing"]


def build_skill_registry(
    skills_directory: str | Path,
    *,
    conflict_policy: ConflictPolicy = "error",
    executors: dict[str, SkillExecutor] | None = None,
    middleware: list[SkillMiddleware] | None = None,
) -> SkillRegistry:
    """Create and return a ready-to-use skill registry from one directory."""
    loader = SkillLoader()
    specs = loader.load_directory(skills_directory)

    registry = SkillRegistry(conflict_policy=conflict_policy)
    registry.register_many(specs)

    for mode, executor in (executors or {}).items():
        registry.add_executor(mode, executor)

    chain = (
        middleware
        if middleware is not None
        else [ValidationMiddleware(), PermissionMiddleware(), TimingMiddleware()]
    )
    for layer in chain:
        registry.use(layer)
    return registry


def build_registry(
    skills_directory: str | Path,
    *,
    conflict_policy: ConflictPolicy = "error",
    executors: dict[str, SkillExecutor] | None = None,
    middleware: list[SkillMiddleware] | None = None,
) -> SkillRegistry:
    """Alias for build_skill_registry with the same behavior."""
    return build_skill_registry(
        skills_directory,
        conflict_policy=conflict_policy,
        executors=executors,
        middleware=middleware,
    )

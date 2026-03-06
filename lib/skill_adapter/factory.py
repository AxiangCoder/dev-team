"""Factory helpers for creating fully configured skill registries."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from skill_adapter.loader import SkillLoader
from skill_adapter.middleware import (
    PermissionMiddleware,
    SkillMiddleware,
    TimingMiddleware,
)
from skill_adapter.registry import SkillRegistry

ConflictPolicy = Literal["error", "override", "keep_existing"]


def build_skill_registry(
    skills_directory: str | Path,
    *,
    conflict_policy: ConflictPolicy = "error",
    middleware: list[SkillMiddleware] | None = None,
) -> SkillRegistry:
    """Create and return a ready-to-use skill registry from one directory."""
    loader = SkillLoader()
    runtimes = loader.load_directory(skills_directory)

    registry = SkillRegistry(conflict_policy=conflict_policy)
    registry.register_many(runtimes)

    chain = middleware if middleware is not None else [PermissionMiddleware(), TimingMiddleware()]
    for layer in chain:
        registry.use(layer)
    return registry

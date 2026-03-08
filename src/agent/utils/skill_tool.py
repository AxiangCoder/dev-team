"""Helpers for loading shared skill metadata from the adapter layer."""

from functools import lru_cache
from pathlib import Path

from skill_adapter import SkillRegistry, build_skill_registry


@lru_cache(maxsize=1)
def get_skill_adapter() -> SkillRegistry:
    """Build and cache the shared skill registry."""
    return build_skill_registry(Path("src/agent/skills"))


def get_skill_instructions(skill_name: str) -> str:
    """Return the instruction body for one registered skill."""
    spec = get_skill_adapter().get_skill(skill_name)
    return spec.body

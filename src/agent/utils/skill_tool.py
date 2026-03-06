from functools import lru_cache
from pathlib import Path

from lib.skill_adapter import build_skill_registry


@lru_cache(maxsize=16)
def get_skill_adapter():
    return build_skill_registry(Path("src/agent/skills"))

"""Loader for native SKILL.md-based skill directories."""

from __future__ import annotations

from pathlib import Path

from skill_adapter.exceptions import SkillDefinitionError
from skill_adapter.models import SkillRuntime, SkillSpec


class SkillLoader:
    """Load skills from directories that contain `SKILL.md`."""

    def load_directory(self, skills_directory: str | Path) -> list[SkillRuntime]:
        """Load all skill directories under the given root path."""
        root = Path(skills_directory)
        if not root.exists() or not root.is_dir():
            raise SkillDefinitionError(
                f"Skill directory does not exist or is not a directory: {root}"
            )

        runtimes: list[SkillRuntime] = []
        for skill_dir in sorted(path for path in root.iterdir() if path.is_dir()):
            skill_markdown_path = skill_dir / "SKILL.md"
            if not skill_markdown_path.exists():
                continue
            runtimes.append(self.load_skill(skill_dir))

        if not runtimes:
            raise SkillDefinitionError(
                f"No valid skills found in {root}. Expected <skill_name>/SKILL.md"
            )
        return runtimes

    def load_dir(self, skills_directory: str | Path) -> list[SkillRuntime]:
        """Backward-compatible alias for `load_directory`."""
        return self.load_directory(skills_directory)

    def load_skill(self, skill_directory: str | Path) -> SkillRuntime:
        """Load one skill directory and create a runtime."""
        directory = Path(skill_directory)
        skill_markdown_path = directory / "SKILL.md"
        if not skill_markdown_path.exists():
            raise SkillDefinitionError(f"SKILL.md not found in {directory}")

        skill_markdown = skill_markdown_path.read_text(encoding="utf-8").strip()
        if not skill_markdown:
            raise SkillDefinitionError(f"SKILL.md is empty in {directory}")

        frontmatter = self._parse_frontmatter(skill_markdown)
        skill_name = str(frontmatter.get("name", "")).strip()
        if not skill_name:
            raise SkillDefinitionError(
                f"SKILL.md missing required frontmatter field 'name' in {directory}"
            )
        description = self._extract_description(skill_markdown, frontmatter)

        skill_spec = SkillSpec(
            name=skill_name,
            description=description,
            skill_markdown=skill_markdown,
            root_path=directory,
            metadata={
                "skill_markdown_path": str(skill_markdown_path),
                "scripts_path": str(directory / "scripts"),
                "assets_path": str(directory / "assets"),
                "references_path": str(directory / "references"),
            },
        )

        return SkillRuntime(
            name=skill_spec.name,
            description=skill_spec.description,
            handler=self._build_default_handler(skill_spec),
            metadata=skill_spec.metadata,
        )

    def _extract_description(
        self, skill_markdown: str, frontmatter: dict[str, str]
    ) -> str:
        description = frontmatter.get("description", "").strip()
        if description:
            return description[:140]

        for line in skill_markdown.splitlines():
            normalized = line.strip()
            if not normalized:
                continue
            if normalized == "---":
                continue
            if normalized.startswith("#"):
                continue
            return normalized[:140]
        return "Skill loaded from SKILL.md"

    def _parse_frontmatter(self, skill_markdown: str) -> dict[str, str]:
        lines = skill_markdown.splitlines()
        if len(lines) < 3 or lines[0].strip() != "---":
            return {}

        metadata: dict[str, str] = {}
        for line in lines[1:]:
            normalized = line.strip()
            if normalized == "---":
                return metadata
            if ":" not in normalized:
                continue
            key, value = normalized.split(":", maxsplit=1)
            metadata[key.strip()] = value.strip()
        return {}

    def _build_default_handler(self, skill_spec: SkillSpec):
        def _handler(input_data):
            return {
                "skill_name": skill_spec.name,
                "instructions": skill_spec.skill_markdown,
                "input": input_data,
            }

        return _handler


# Backward-compatible alias
SkillManifestLoader = SkillLoader

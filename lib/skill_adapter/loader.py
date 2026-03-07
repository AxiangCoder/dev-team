"""Loader for native SKILL.md-based skill directories."""

from __future__ import annotations

from pathlib import Path

from skill_adapter.exceptions import SkillDefinitionError
from skill_adapter.models import SkillSpec


class SkillLoader:
    """Load skills from directories that contain `SKILL.md`."""

    def load_directory(self, skills_directory: str | Path) -> list[SkillSpec]:
        """Load all skill directories under the given root path."""
        root = Path(skills_directory)
        if not root.exists() or not root.is_dir():
            raise SkillDefinitionError(
                f"Skill directory does not exist or is not a directory: {root}"
            )

        specs: list[SkillSpec] = []
        for skill_dir in sorted(path for path in root.iterdir() if path.is_dir()):
            skill_markdown_path = skill_dir / "SKILL.md"
            if not skill_markdown_path.exists():
                continue
            specs.append(self.load_skill(skill_dir))

        if not specs:
            raise SkillDefinitionError(
                f"No valid skills found in {root}. Expected <skill_name>/SKILL.md"
            )
        return specs

    def load_dir(self, skills_directory: str | Path) -> list[SkillSpec]:
        """Backward-compatible alias for `load_directory`."""
        return self.load_directory(skills_directory)

    def load_skill(self, skill_directory: str | Path) -> SkillSpec:
        """Load one skill directory and create a skill spec."""
        directory = Path(skill_directory)
        skill_markdown_path = directory / "SKILL.md"
        if not skill_markdown_path.exists():
            raise SkillDefinitionError(f"SKILL.md not found in {directory}")

        skill_markdown = skill_markdown_path.read_text(encoding="utf-8").strip()
        if not skill_markdown:
            raise SkillDefinitionError(f"SKILL.md is empty in {directory}")

        frontmatter, body = self._parse_skill_markdown(skill_markdown)
        skill_name = str(frontmatter.get("name", "")).strip()
        if not skill_name:
            raise SkillDefinitionError(
                f"SKILL.md missing required frontmatter field 'name' in {directory}"
            )
        description = self._extract_description(frontmatter)
        version = str(frontmatter.get("version", "")).strip() or None

        return SkillSpec(
            name=skill_name,
            description=description,
            body=body,
            root_path=directory,
            version=version,
            metadata={
                "skill_markdown_path": str(skill_markdown_path),
                "scripts_path": str(directory / "scripts"),
                "assets_path": str(directory / "assets"),
                "references_path": str(directory / "references"),
                "frontmatter": frontmatter,
            },
        )

    def _extract_description(self, frontmatter: dict[str, str]) -> str:
        description = frontmatter.get("description", "").strip()
        if description:
            return description[:140]
        return ""

    def _parse_skill_markdown(self, skill_markdown: str) -> tuple[dict[str, str], str]:
        lines = skill_markdown.splitlines()
        if len(lines) < 3 or lines[0].strip() != "---":
            return {}, skill_markdown.strip()

        metadata: dict[str, str] = {}
        end_index = None
        for index, line in enumerate(lines[1:], start=1):
            normalized = line.strip()
            if normalized == "---":
                end_index = index
                break
            if ":" not in normalized:
                continue
            key, value = normalized.split(":", maxsplit=1)
            metadata[key.strip()] = value.strip()
        if end_index is None:
            return {}, skill_markdown.strip()

        body = "\n".join(lines[end_index + 1 :]).strip()
        return metadata, body


# Backward-compatible alias
SkillManifestLoader = SkillLoader

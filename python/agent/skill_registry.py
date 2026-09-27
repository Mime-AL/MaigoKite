"""Local, declarative Skill discovery used by the Agent runtime."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml

_SKILL_NAME = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
_MAX_SKILL_BYTES = 256 * 1024


@dataclass(frozen=True)
class SkillDefinition:
    """A local instruction package loaded from a ``SKILL.md`` file."""

    name: str
    version: str
    description: str
    instructions: str
    source_path: str
    kind: str = "instruction"
    parameters_schema: dict[str, Any] | None = None

    def to_dict(self, *, include_instructions: bool = False) -> dict[str, Any]:
        value = asdict(self)
        value["parameters_schema"] = value["parameters_schema"] or {}
        if not include_instructions:
            value.pop("instructions", None)
        return value


class SkillRegistry:
    """Discovers auditable local Skills without executing arbitrary package code."""

    def __init__(self) -> None:
        self._skills: dict[str, SkillDefinition] = {}

    def register(self, skill: SkillDefinition) -> None:
        if not _SKILL_NAME.fullmatch(skill.name):
            raise ValueError(f"invalid skill name: {skill.name!r}")
        if skill.kind not in {"instruction", "workflow"}:
            raise ValueError(f"unsupported local skill kind: {skill.kind!r}")
        if skill.name in self._skills:
            raise ValueError(f"duplicate skill name: {skill.name}")
        self._skills[skill.name] = skill

    def unregister(self, skill_name: str) -> None:
        self._skills.pop(skill_name, None)

    def get_skill(self, skill_name: str) -> SkillDefinition | None:
        return self._skills.get(skill_name)

    def list_skills(self) -> list[SkillDefinition]:
        return sorted(self._skills.values(), key=lambda item: item.name)

    def load_directories(self, directories: list[str], workspace_root: str | Path) -> list[str]:
        """Load Skills and return non-fatal validation errors for observability."""
        errors: list[str] = []
        workspace = Path(workspace_root).expanduser().resolve()
        for raw_directory in directories:
            directory = Path(raw_directory).expanduser()
            if not directory.is_absolute():
                directory = workspace / directory
            directory = directory.resolve()
            if not directory.exists():
                continue
            if not directory.is_dir():
                errors.append(f"skill path is not a directory: {directory}")
                continue
            for source in sorted(directory.rglob("SKILL.md")):
                try:
                    resolved = source.resolve()
                    resolved.relative_to(directory)
                    if resolved.stat().st_size > _MAX_SKILL_BYTES:
                        raise ValueError("SKILL.md exceeds 256 KiB")
                    self.register(self._parse(resolved))
                except (OSError, ValueError, yaml.YAMLError) as exc:
                    errors.append(f"{source}: {exc}")
        return errors

    @staticmethod
    def _parse(source: Path) -> SkillDefinition:
        raw = source.read_text(encoding="utf-8")
        metadata: dict[str, Any] = {}
        instructions = raw.strip()
        if raw.startswith("---\n"):
            end = raw.find("\n---\n", 4)
            if end < 0:
                raise ValueError("unterminated YAML frontmatter")
            parsed = yaml.safe_load(raw[4:end]) or {}
            if not isinstance(parsed, dict):
                raise ValueError("frontmatter must be an object")
            metadata = parsed
            instructions = raw[end + 5 :].strip()
        name = str(metadata.get("name") or source.parent.name).strip().lower()
        description = str(metadata.get("description") or "").strip()
        version = str(metadata.get("version") or "1.0.0").strip()
        kind = str(metadata.get("kind") or "instruction").strip().lower()
        parameters = metadata.get("parameters_schema") or {}
        if not description:
            raise ValueError("skill description is required")
        if not instructions:
            raise ValueError("skill instructions are required")
        if not isinstance(parameters, dict):
            raise ValueError("parameters_schema must be an object")
        return SkillDefinition(
            name=name,
            version=version,
            description=description,
            instructions=instructions,
            source_path=str(source),
            kind=kind,
            parameters_schema=parameters,
        )

    def catalog_prompt(self) -> str:
        if not self._skills:
            return ""
        lines = ["Available local Skills (read one with the skill tool before applying it):"]
        lines.extend(f"- {item.name}: {item.description}" for item in self.list_skills())
        return "\n".join(lines)

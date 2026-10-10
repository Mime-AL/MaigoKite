"""Local, declarative Skill discovery used by the Agent runtime."""

from __future__ import annotations

import os
import re
import stat
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from threading import Event
from typing import Any

import yaml

_SKILL_NAME = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
_MAX_SKILL_BYTES = 256 * 1024
_MAX_SCAN_ENTRIES = 20_000
_MAX_SCAN_SKILLS = 512
_MAX_SCAN_BYTES = 8 * 1024 * 1024
_SCAN_SECONDS = 10
_SKIP_DIRECTORIES = {".git", ".venv", "venv", "node_modules", "__pycache__", "dist", "build"}


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

    def load_directories(
        self, directories: list[str], workspace_root: str | Path, *, stop: Event | None = None,
    ) -> list[str]:
        """Bounded stdlib scan, run on a private registry off the Core event loop.

        The deadline is cooperative between filesystem calls, not a promise to
        interrupt a blocked OS read. Limit failures discard partial discoveries.
        """
        errors: list[str] = []
        workspace = Path(workspace_root).expanduser().resolve()
        deadline = time.monotonic() + _SCAN_SECONDS
        entries = skills = size = 0
        found: dict[str, SkillDefinition] = {}

        def check_limit() -> None:
            if ((stop is not None and stop.is_set()) or time.monotonic() >= deadline
                    or entries > _MAX_SCAN_ENTRIES or skills > _MAX_SCAN_SKILLS or size > _MAX_SCAN_BYTES):
                raise ValueError("Skill scan stopped or exceeded its entry/time/content budget; narrow the directories")

        def walk_error(_error: OSError) -> None:
            errors.append("Skill scan skipped an unreadable directory")

        for raw_directory in directories:
            try:
                check_limit()
                directory = Path(raw_directory).expanduser()
                if not directory.is_absolute():
                    directory = workspace / directory
                directory = directory.resolve()
                if not directory.is_dir():
                    errors.append(f"skill directory is unavailable: {directory}")
                    continue
                for root, children, files in os.walk(directory, followlinks=False, onerror=walk_error):
                    entries += len(children) + len(files) + 1
                    check_limit()
                    children[:] = sorted(name for name in children if name not in _SKIP_DIRECTORIES)
                    if "SKILL.md" not in files:
                        continue
                    skills += 1
                    check_limit()
                    source = Path(root) / "SKILL.md"
                    try:
                        resolved = source.resolve()
                        resolved.relative_to(directory)
                        if not resolved.is_file():
                            raise ValueError("Skill source must be a regular file")
                        # Nonblocking open + fstat also reject a FIFO swapped in
                        # after is_file(). This cannot interrupt ordinary OS I/O.
                        flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_BINARY", 0)
                        flags |= getattr(os, "O_NOFOLLOW", 0)
                        fd = os.open(resolved, flags)
                        try:
                            if not stat.S_ISREG(os.fstat(fd).st_mode):
                                raise ValueError("Skill source must be a regular file")
                            with os.fdopen(fd, "rb", closefd=False) as stream:
                                content = stream.read(_MAX_SKILL_BYTES + 1)
                        finally:
                            os.close(fd)
                        size += len(content)
                        skill = self.parse_content(content.decode("utf-8"), str(resolved))
                        if skill.name in found or skill.name in self._skills:
                            raise ValueError("duplicate Skill")
                        found[skill.name] = skill
                    except (OSError, ValueError, RuntimeError, yaml.YAMLError):
                        errors.append(f"{source}: unreadable, invalid, oversized or duplicate Skill")
                    check_limit()
            except (OSError, RuntimeError):
                errors.append(f"{raw_directory}: skill directory cannot be scanned")
        self._skills.update(found)
        return errors

    @staticmethod
    def _parse(source: Path) -> SkillDefinition:
        return SkillRegistry.parse_content(source.read_text(encoding="utf-8"), str(source))

    @staticmethod
    def parse_content(raw: str, source_path: str) -> SkillDefinition:
        """Validate imported Markdown through the same parser as disk Skills."""
        if len(raw.encode("utf-8")) > _MAX_SKILL_BYTES:
            raise ValueError("SKILL.md exceeds 256 KiB")
        raw = raw.removeprefix("\ufeff").replace("\r\n", "\n")
        source = Path(source_path)
        metadata: dict[str, Any] = {}
        instructions = raw.strip()
        if raw.startswith("---\n"):
            end = raw.find("\n---\n", 4)
            if end < 0:
                raise ValueError("unterminated YAML frontmatter")
            try:
                parsed = yaml.safe_load(raw[4:end]) or {}
            except yaml.YAMLError as exc:
                raise ValueError("invalid Skill YAML frontmatter") from exc
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
        result = SkillDefinition(
            name=name,
            version=version,
            description=description,
            instructions=instructions,
            source_path=str(source),
            kind=kind,
            parameters_schema=parameters,
        )
        if not _SKILL_NAME.fullmatch(result.name) or result.kind not in {"instruction", "workflow"}:
            raise ValueError("invalid Skill name or kind")
        return result

    def catalog_prompt(self) -> str:
        if not self._skills:
            return ""
        lines = ["Available local Skills (read one with the skill tool before applying it):"]
        lines.extend(f"- {item.name}: {item.description}" for item in self.list_skills())
        return "\n".join(lines)

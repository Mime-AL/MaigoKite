"""Skill registry for managing agent capabilities."""

from __future__ import annotations

from typing import Any, Optional


class SkillDefinition:
    """Metadata describing a registered skill."""

    name: str
    version: str
    description: str
    parameters_schema: dict[str, Any]

    def __init__(
        self,
        name: str,
        version: str,
        description: str,
        parameters_schema: dict[str, Any],
    ) -> None:
        ...


class SkillRegistry:
    """Central registry for agent skills and capabilities."""

    def register(self, skill: SkillDefinition) -> None:
        ...

    def unregister(self, skill_name: str) -> None:
        ...

    def get_skill(self, skill_name: str) -> SkillDefinition | None:
        ...

    def list_skills(self) -> list[SkillDefinition]:
        ...

    async def invoke_skill(
        self, skill_name: str, arguments: dict[str, Any], context: dict[str, Any]
    ) -> Any:
        ...

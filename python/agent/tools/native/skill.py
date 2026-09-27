"""SkillTool exposes discovered local instruction packages to the model."""

from __future__ import annotations

from typing import Any

from agent.skill_registry import SkillRegistry
from agent.tools.base import BaseTool, ExecutionContext, ToolResult


class SkillTool(BaseTool):
    def __init__(self, registry: SkillRegistry) -> None:
        self.registry = registry

    @property
    def name(self) -> str:
        return "skill"

    @property
    def description(self) -> str:
        return "List installed local Skills or read one Skill's instructions before applying it."

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["list", "read"]},
                "name": {"type": "string", "maxLength": 64},
            },
            "required": ["action"],
            "additionalProperties": False,
        }

    async def execute(self, context: ExecutionContext, arguments: dict[str, Any]) -> ToolResult:
        action = str(arguments.get("action", ""))
        if action == "list":
            items = [item.to_dict() for item in self.registry.list_skills()]
            return ToolResult({"skills": items}, f"Found {len(items)} installed Skill(s).")
        if action == "read":
            name = str(arguments.get("name", "")).strip()
            item = self.registry.get_skill(name)
            if item is None:
                return ToolResult.failure({"name": name}, f"Skill not found: {name}", error_code="SKILL_NOT_FOUND")
            return ToolResult(
                item.to_dict(include_instructions=True),
                f"Loaded Skill {item.name} {item.version}.",
                raw=item.instructions,
            )
        return ToolResult.failure(
            {"action": action}, "Skill action must be list or read.", error_code="SKILL_ACTION_INVALID"
        )

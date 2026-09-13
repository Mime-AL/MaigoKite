"""Prompt template registry and output parsers for NanamiGopher Agent."""

from agent.prompts.templates import (
    agent_step_template,
    reflection_template,
    safety_check_template,
    summarize_template,
    tool_call_format,
)
from agent.prompts.parsers import PlanOutputParser, ToolCallOutputParser

__all__ = [
    "agent_step_template",
    "reflection_template",
    "safety_check_template",
    "summarize_template",
    "tool_call_format",
    "PlanOutputParser",
    "ToolCallOutputParser",
]

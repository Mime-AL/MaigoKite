"""A user question suspended by LangGraph, not by a second continuation loop."""

from __future__ import annotations

from typing import Any

from langgraph.types import interrupt
from pydantic import BaseModel, Field

from agent.tools.base import BaseTool, ExecutionContext, ToolResult


class QuestionOption(BaseModel):
    label: str = Field(min_length=1, max_length=200)
    recommended: bool = False


class QuestionParams(BaseModel):
    title: str = Field(min_length=1, max_length=2000)
    options: list[QuestionOption] = Field(default_factory=list, max_length=8)


class AskUserQuestionTool(BaseTool):
    risk_level = 1

    @property
    def name(self) -> str:
        return "ask_user_question"

    @property
    def description(self) -> str:
        return "Ask the user a necessary clarification and wait for their answer. Use only when user input is needed."

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return QuestionParams.model_json_schema()

    async def execute(self, context: ExecutionContext, arguments: dict[str, Any]) -> ToolResult:
        params = QuestionParams.model_validate(arguments)
        answer = interrupt({
            "kind": "user_question", "tool_call_id": context.step_id,
            **params.model_dump(),
        })
        if not isinstance(answer, str) or not answer.strip() or len(answer) > 10000:
            raise ValueError("invalid user answer")
        return ToolResult({"answer": answer}, "User answered the question", raw=answer)

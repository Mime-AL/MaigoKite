"""Command execution without shell expansion; BashTool is a legacy alias."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from agent.tools.base import BaseTool, ExecutionContext, ToolResult
from agent.utils.sandbox import SandboxExecutor, SandboxUnavailableError


class BashParams(BaseModel):
    """Parameters for executing a command."""

    command: str = Field(
        min_length=1,
        max_length=8_192,
        description=(
            "The command to execute without shell expansion. Run concise, targeted "
            "commands rather than long multi-step pipelines."
        ),
    )
    timeout: int = Field(
        default=30,
        ge=1,
        le=120,
        description="Maximum seconds to wait for the command before killing it.",
    )
    workdir: str | None = Field(
        default=None,
        description="Working directory; outside-workspace access requires approval or full access.",
    )
    sandbox_permissions: Literal["use_default", "require_escalated"] = Field(
        default="use_default", description="Request one host execution only when needed. Also request network_access=true because host execution cannot isolate networking. Both require approval, never grant it.",
    )
    network_access: bool = Field(default=False, description="Request network access for this command; requires approval in confined modes.")
    max_output_bytes: int = Field(default=8000, ge=256, le=32_000,
                                  description="Preview bytes per stream. Full output is saved in workspace log files.")
    interactive: bool = Field(default=False, description="Allow the user to send stdin from the process panel. Requires approval; not a terminal or detached job. Timeout still applies.")


BASH_DESCRIPTION = (
    "Execute argv without shell expansion. Normal commands use a workspace process sandbox with no network. "
    "Request network_access for networking within the sandbox, or require_escalated plus network_access for host execution; policy decides approval. "
    "Returns bounded stdout/stderr, exit code and log paths. Use file_read with offset to inspect more output."
)


class ExecCommandTool(BaseTool):
    @property
    def name(self) -> str:
        return "exec_command"

    @property
    def description(self) -> str:
        return BASH_DESCRIPTION

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return BashParams.model_json_schema()

    async def execute(
        self, context: ExecutionContext, arguments: dict[str, Any]
    ) -> ToolResult:
        workspace_root = Path(
            str(context.metadata.get("workspace_root") or arguments.get("workdir") or Path.cwd())
        ).expanduser().resolve()
        workdir = Path(str(arguments.get("workdir") or workspace_root)).expanduser().resolve()
        executor = SandboxExecutor(
            {"workspace_root": str(workspace_root), "workdir": str(workdir),
             "sandbox_mode": context.metadata.get("sandbox_mode", "workspace"),
             "allow_network": context.metadata.get("allow_network", False),
             "output_limit": int(arguments.get("max_output_bytes", 8000)),
             "output_directory": str(workspace_root / ".maigokite" / "outputs")}
        )
        registry = context.metadata.get("process_registry")
        def on_spawn(process, stdout, stderr, stop):
            if registry is not None:
                registry.attach(context.step_id, str(context.metadata.get("workspace_id", "personal")),
                                context.task_id, process, stdout, stderr, stop)
        def on_exit():
            if registry is not None:
                registry.detach(context.step_id)
        try:
            result = await executor.execute_command(
                str(arguments["command"]), int(arguments.get("timeout", 30)), on_spawn=on_spawn, on_exit=on_exit,
                interactive=bool(arguments.get("interactive", False)),
            )
        except SandboxUnavailableError as exc:
            return ToolResult.failure({}, str(exc), error_code="SANDBOX_UNAVAILABLE",
                                      user_hint="受限命令需要可用的系统沙箱。请安装或启用 bubblewrap；也可单次批准明确的沙箱外执行请求。")

        parts = [f"Exit code {result.exit_code}"]
        if result.timed_out:
            parts.insert(0, "Timed out")
        parts.append(f"Duration: {result.duration_ms / 1000:.2f}s")

        return ToolResult(
            data={
                "return_code": result.exit_code,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "duration_seconds": round(result.duration_ms / 1000, 3),
                "timed_out": result.timed_out,
                "output_truncated": result.output_truncated,
                "sandboxed": result.sandboxed,
                "stdout_path": result.stdout_path,
                "stderr_path": result.stderr_path,
            },
            summary="; ".join(parts),
            raw=result.stdout or result.stderr or "",
            metadata={
                "tool": self.name,
                "type": "process",
                "exit_code": result.exit_code,
                "sandboxed": result.sandboxed,
            },
            success=result.exit_code == 0 and not result.timed_out,
            error_code=("COMMAND_TIMEOUT" if result.timed_out else "COMMAND_FAILED")
            if result.exit_code != 0 or result.timed_out else None,
        )


class BashTool(ExecCommandTool):
    """Historical command alias; not exposed as a second model tool."""

    @property
    def name(self) -> str:
        return "bash"

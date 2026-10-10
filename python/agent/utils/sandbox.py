"""Workspace-confined subprocess execution used by native tools."""

from __future__ import annotations

import asyncio
import os
import platform
import shlex
import shutil
import signal
import subprocess
import tempfile
import time
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SandboxExecutionResult:
    exit_code: int
    stdout: str = ""
    stderr: str = ""
    duration_ms: float = 0.0
    timed_out: bool = False
    output_truncated: bool = False
    sandboxed: bool = False


@lru_cache(maxsize=4)
def _bubblewrap_works(binary: str) -> bool:
    """Return whether bubblewrap can create a minimal namespace on this host."""
    try:
        result = subprocess.run(
            [
                binary,
                "--die-with-parent",
                "--new-session",
                "--unshare-all",
                "--share-net",
                "--ro-bind",
                "/usr",
                "/usr",
                "--ro-bind-try",
                "/bin",
                "/bin",
                "--ro-bind-try",
                "/lib",
                "/lib",
                "--ro-bind-try",
                "/lib64",
                "/lib64",
                "--proc",
                "/proc",
                "--dev",
                "/dev",
                "/bin/true",
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=2,
            check=False,
            env={"PATH": "/usr/bin:/bin"},
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0


class SandboxExecutor:
    """Execute argv without a shell and confine filesystem writes to a workspace."""

    _FALLBACK_READ_ONLY = {"pwd", "ls", "cat", "head", "tail", "wc", "rg", "grep", "git"}
    _UNSAFE_GIT_OPTIONS = {
        "-c",
        "-p",
        "--paginate",
        "--config-env",
        "--exec-path",
        "--git-dir",
        "--work-tree",
    }
    _OUTPUT_LIMIT = 1_000_000

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        values = config or {}
        self.workspace_root = Path(values.get("workspace_root") or Path.cwd()).expanduser().resolve()
        self.workdir = Path(values.get("workdir") or self.workspace_root).expanduser().resolve()
        if self.workspace_root == Path(self.workspace_root.anchor):
            raise ValueError("sandbox workspace must not be a filesystem root")
        self.allow_network = bool(values.get("allow_network", True))
        try:
            self.workdir.relative_to(self.workspace_root)
        except ValueError as exc:
            raise ValueError("sandbox workdir is outside the workspace") from exc
        if not self.workdir.is_dir():
            raise ValueError("sandbox workdir does not exist")
        self._cpu_seconds = 0.0
        self._memory_mb = 0

    async def execute_command(
        self, command: str, timeout: int = 30, *, on_spawn: Any = None, on_exit: Any = None,
    ) -> SandboxExecutionResult:
        try:
            args = shlex.split(command)
        except ValueError as exc:
            raise ValueError("command has invalid quoting") from exc
        if not args:
            raise ValueError("command must not be empty")

        argv, sandboxed = self._build_argv(args)
        start = time.monotonic()
        with tempfile.TemporaryFile() as stdout_file, tempfile.TemporaryFile() as stderr_file:
            process = await asyncio.create_subprocess_exec(
                *argv,
                stdin=asyncio.subprocess.DEVNULL,
                stdout=stdout_file,
                stderr=stderr_file,
                cwd=str(self.workdir),
                env=self._minimal_environment(),
                start_new_session=os.name == "posix",
            )
            timed_out = False
            try:
                if on_spawn is not None:
                    on_spawn(process, stdout_file, stderr_file, self._kill_process_group)
                await asyncio.wait_for(process.wait(), timeout)
            except asyncio.TimeoutError:
                timed_out = True
                self._kill_process_group(process)
                await process.wait()
            except asyncio.CancelledError:
                self._kill_process_group(process)
                await process.wait()
                raise
            except Exception:
                self._kill_process_group(process)
                await process.wait()
                raise
            finally:
                if on_exit is not None:
                    on_exit()

            stdout_file.seek(0)
            stderr_file.seek(0)
            stdout_bytes = stdout_file.read(self._OUTPUT_LIMIT + 1)
            stderr_bytes = stderr_file.read(self._OUTPUT_LIMIT + 1)

        stdout = stdout_bytes.decode("utf-8", errors="replace")
        stderr = stderr_bytes.decode("utf-8", errors="replace")
        return SandboxExecutionResult(
            exit_code=-1 if timed_out else int(process.returncode or 0),
            stdout=stdout[: self._OUTPUT_LIMIT],
            stderr=stderr[: self._OUTPUT_LIMIT] or ("command timed out" if timed_out else ""),
            duration_ms=(time.monotonic() - start) * 1000,
            timed_out=timed_out,
            output_truncated=(
                len(stdout_bytes) > self._OUTPUT_LIMIT or len(stderr_bytes) > self._OUTPUT_LIMIT
            ),
            sandboxed=sandboxed,
        )

    async def execute_python(
        self, code: str, timeout: int = 30
    ) -> SandboxExecutionResult:
        executable = shutil.which("python3") or shutil.which("python")
        if executable is None:
            raise RuntimeError("Python executable is unavailable")
        return await self.execute_command(
            f"{shlex.quote(executable)} -c {shlex.quote(code)}", timeout
        )

    def set_limits(self, cpu_seconds: float, memory_mb: int) -> None:
        # Reserved for a future cgroup/job-object adapter. The process deadline is
        # enforced now; accepting invalid values would create a false guarantee.
        if cpu_seconds < 0 or memory_mb < 0:
            raise ValueError("sandbox limits must not be negative")
        self._cpu_seconds = cpu_seconds
        self._memory_mb = memory_mb

    def _build_argv(self, args: list[str]) -> tuple[list[str], bool]:
        bubblewrap = shutil.which("bwrap") if platform.system() == "Linux" else None
        if bubblewrap and _bubblewrap_works(bubblewrap):
            return self._bubblewrap_argv(bubblewrap, args), True
        self._validate_fallback(args)
        return args, False

    def _bubblewrap_argv(self, binary: str, args: list[str]) -> list[str]:
        command = [
            binary,
            "--die-with-parent",
            "--new-session",
            "--unshare-all",
        ]
        if self.allow_network:
            command.append("--share-net")
        command.extend(["--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp"])

        for source in ("/usr", "/usr/local", "/bin", "/sbin", "/lib", "/lib64"):
            if Path(source).exists():
                command.extend(["--ro-bind", source, source])
        for source in (
            "/etc/hosts",
            "/etc/resolv.conf",
            "/etc/nsswitch.conf",
            "/etc/ssl/certs",
            "/etc/ca-certificates",
        ):
            if Path(source).exists():
                command.extend(["--ro-bind", source, source])

        # Bind destinations need their parent hierarchy in the fresh mount namespace.
        parent = self.workspace_root.parent
        parents: list[Path] = []
        while parent != parent.parent:
            parents.append(parent)
            parent = parent.parent
        for directory in reversed(parents):
            if str(directory) not in {
                "/usr", "/usr/local", "/bin", "/sbin", "/lib", "/lib64", "/tmp"
            }:
                command.extend(["--dir", str(directory)])

        command.extend(
            [
                "--bind",
                str(self.workspace_root),
                str(self.workspace_root),
                "--chdir",
                str(self.workdir),
                "--clearenv",
                "--setenv",
                "HOME",
                str(self.workspace_root),
                "--setenv",
                "PATH",
                "/usr/local/bin:/usr/local/go/bin:/usr/bin:/bin",
                "--setenv",
                "LANG",
                os.environ.get("LANG", "C.UTF-8"),
                "--setenv",
                "LC_ALL",
                os.environ.get("LC_ALL", "C.UTF-8"),
                "--setenv",
                "TMPDIR",
                "/tmp",
                "--setenv",
                "GOCACHE",
                "/tmp/go-build",
                "--setenv",
                "GOMODCACHE",
                "/tmp/go-mod",
                "--setenv",
                "npm_config_cache",
                "/tmp/npm-cache",
                "--",
                *args,
            ]
        )
        return command

    def _validate_fallback(self, args: list[str]) -> None:
        executable = args[0]
        if Path(executable).name not in self._FALLBACK_READ_ONLY or executable != Path(executable).name:
            raise RuntimeError(
                "secure process sandbox is unavailable; only built-in read-only commands are enabled"
            )
        if executable == "git" and any(
            argument in self._UNSAFE_GIT_OPTIONS
            or any(argument.startswith(option + "=") for option in self._UNSAFE_GIT_OPTIONS)
            for argument in args[1:]
        ):
            raise PermissionError("git option is not allowed without a process sandbox")

        for argument in args[1:]:
            candidate_value = (
                argument.split("=", 1)[1]
                if argument.startswith("-") and "=" in argument
                else argument
            )
            if candidate_value.startswith("-"):
                continue
            candidate = Path(candidate_value).expanduser()
            if not candidate.is_absolute():
                candidate = self.workdir / candidate
            try:
                candidate.resolve().relative_to(self.workspace_root)
            except (OSError, ValueError) as exc:
                raise PermissionError("command path is outside the workspace") from exc

    @staticmethod
    def _minimal_environment() -> dict[str, str]:
        return {
            "PATH": "/usr/local/bin:/usr/local/go/bin:/usr/bin:/bin",
            "HOME": "/tmp",
            "LANG": os.environ.get("LANG", "C.UTF-8"),
            "LC_ALL": os.environ.get("LC_ALL", "C.UTF-8"),
            "TMPDIR": "/tmp",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_PAGER": "cat",
        }

    @staticmethod
    def _kill_process_group(process: asyncio.subprocess.Process) -> None:
        if os.name == "posix":
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        else:
            process.kill()

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

from agent.security.sensitive_paths import is_sensitive_path


class SandboxUnavailableError(RuntimeError):
    """A confined request must not silently become a host process."""


@dataclass(frozen=True)
class SandboxExecutionResult:
    exit_code: int
    stdout: str = ""
    stderr: str = ""
    duration_ms: float = 0.0
    timed_out: bool = False
    output_truncated: bool = False
    sandboxed: bool = False
    stdout_path: str = ""
    stderr_path: str = ""


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

    _OUTPUT_LIMIT = 1_000_000

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        values = config or {}
        self.workspace_root = Path(values.get("workspace_root") or Path.cwd()).expanduser().resolve()
        self.workdir = Path(values.get("workdir") or self.workspace_root).expanduser().resolve()
        if self.workspace_root == Path(self.workspace_root.anchor):
            raise ValueError("sandbox workspace must not be a filesystem root")
        self.mode = str(values.get("sandbox_mode", "workspace"))
        if self.mode not in {"read_only", "workspace", "danger_full_access"}:
            raise ValueError("invalid process sandbox mode")
        self.allow_network = bool(values.get("allow_network", False))
        self.output_limit = min(max(int(values.get("output_limit", self._OUTPUT_LIMIT)), 1), self._OUTPUT_LIMIT)
        self.output_directory: Path | None = None
        if self.mode != "danger_full_access" and not self.workdir.is_relative_to(self.workspace_root):
            raise ValueError("sandbox workdir is outside the workspace")
        if not self.workdir.is_dir():
            raise ValueError("sandbox workdir does not exist")
        if values.get("output_directory"):
            directory = Path(values["output_directory"]).resolve()
            directory.relative_to(self.workspace_root)
            directory.mkdir(mode=0o700, parents=True, exist_ok=True)
            directory.resolve().relative_to(self.workspace_root)
            self.output_directory = directory
        self._cpu_seconds = 0.0
        self._memory_mb = 0

    async def execute_command(
        self, command: str, timeout: int = 30, *, on_spawn: Any = None, on_exit: Any = None, interactive: bool = False,
    ) -> SandboxExecutionResult:
        try:
            args = shlex.split(command)
        except ValueError as exc:
            raise ValueError("command has invalid quoting") from exc
        if not args:
            raise ValueError("command must not be empty")

        argv, sandboxed = self._build_argv(args)
        start = time.monotonic()
        # Only command tools request durable workspace logs. Search subprocesses
        # retain their existing temporary output and do not create artifacts.
        def output_file():
            if self.output_directory is None:
                return tempfile.TemporaryFile()
            return tempfile.NamedTemporaryFile(mode="w+b", prefix="command_", suffix=".log",
                                               dir=self.output_directory, delete=False)
        with output_file() as stdout_file, output_file() as stderr_file:
            process = await asyncio.create_subprocess_exec(
                *argv,
                stdin=asyncio.subprocess.PIPE if interactive else asyncio.subprocess.DEVNULL,
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
            stdout_bytes = stdout_file.read(self.output_limit + 1)
            stderr_bytes = stderr_file.read(self.output_limit + 1)
            stdout_path = str(stdout_file.name) if self.output_directory is not None else ""
            stderr_path = str(stderr_file.name) if self.output_directory is not None else ""

        return SandboxExecutionResult(
            exit_code=-1 if timed_out else int(process.returncode or 0),
            stdout=stdout_bytes[:self.output_limit].decode("utf-8", errors="replace"),
            stderr=stderr_bytes[:self.output_limit].decode("utf-8", errors="replace") or ("command timed out" if timed_out else ""),
            duration_ms=(time.monotonic() - start) * 1000,
            timed_out=timed_out,
            output_truncated=(
                len(stdout_bytes) > self.output_limit or len(stderr_bytes) > self.output_limit
            ),
            sandboxed=sandboxed,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
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
        if self.mode == "danger_full_access":
            if not self.allow_network:
                raise PermissionError("Host execution requires explicit network authorization; no command was started")
            return args, False
        bubblewrap = shutil.which("bwrap") if platform.system() == "Linux" else None
        if bubblewrap and _bubblewrap_works(bubblewrap):
            return self._bubblewrap_argv(bubblewrap, args), True
        raise SandboxUnavailableError(
            "Process sandbox unavailable. Install/enable bubblewrap on Linux, "
            "or explicitly approve a require_escalated call with network_access=true. No command was started."
        )

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
                "--ro-bind" if self.mode == "read_only" else "--bind",
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
            ]
        )
        # Protect common root credential files and Git metadata in the process
        # namespace too. This is a bounded guard, not recursive content DLP.
        for path in self.workspace_root.iterdir():
            if path.is_symlink():
                continue
            if path.name == ".git":
                command.extend(["--ro-bind", str(path), str(path)])
            elif is_sensitive_path(path):
                if path.is_dir():
                    command.extend(["--tmpfs", str(path), "--remount-ro", str(path)])
                elif path.is_file():
                    command.extend(["--ro-bind", "/dev/null", str(path)])
        command.extend(["--", *args])
        return command

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

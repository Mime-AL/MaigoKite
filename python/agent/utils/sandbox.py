"""Workspace-confined subprocess execution used by native tools."""

from __future__ import annotations

import asyncio
import codecs
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

from agent.security.sensitive_paths import is_sensitive_path, validate_windows_path
from agent.utils.command_shell import powershell_argv, resolve_command_shell


class SandboxUnavailableError(RuntimeError):
    """A confined request must not silently become a host process."""

    @property
    def user_hint(self) -> str:
        if os.name == "nt":
            return ("Windows 原生受限进程沙箱尚未接入；安装 PowerShell 或 WSL 不会自动启用隔离。"
                    "命令需明确请求单次宿主执行及网络权限并获得批准，或由用户开启完全访问。")
        if platform.system() == "Linux":
            return ("请安装或更新 bubblewrap，并确认系统允许非特权用户命名空间。"
                    "也可以明确申请单次沙箱外执行及网络权限；不会自动放行。")
        return "当前平台尚未接入受限进程沙箱；命令需明确申请单次宿主执行及网络权限。"


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
    shell: str = "direct"
    executable: str = ""
    output_decoding_errors: bool = False


def _decode_preview(data: bytes, limit: int) -> tuple[str, bool]:
    """Do not turn a byte-limit-split Chinese character into a spurious U+FFFD."""
    decoder = codecs.getincrementaldecoder("utf-8")()
    try:
        return decoder.decode(data[:limit], final=len(data) <= limit), False
    except UnicodeDecodeError:
        return data[:limit].decode("utf-8", errors="replace"), True


@lru_cache(maxsize=8)
def _bubblewrap_works(binary: str, allow_network: bool = False) -> bool:
    """Return whether bubblewrap can create a minimal namespace on this host."""
    try:
        result = subprocess.run(
            [
                binary,
                "--die-with-parent",
                "--new-session",
                "--unshare-all",
                "--unshare-user",
                "--disable-userns",
                "--cap-drop", "ALL",
                *(["--share-net"] if allow_network else []),
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


def process_sandbox_status() -> dict[str, Any]:
    """Report host isolation capability separately from a session's authorization mode."""
    system = platform.system()
    binary = shutil.which("bwrap") if system == "Linux" else None
    available = bool(binary and _bubblewrap_works(binary))
    return {
        "platform": system,
        "backend": "bubblewrap" if system == "Linux" else "none",
        "status": "available" if available else "unavailable",
        "reason": "" if available else (
            "bubblewrap_probe_failed" if binary else "bubblewrap_not_installed" if system == "Linux"
            else "native_backend_not_integrated"
        ),
        "network_isolation": available,
        "cpu_memory_limits": False,
        "hint": "" if available else SandboxUnavailableError().user_hint,
    }


class SandboxExecutor:
    """Execute argv or an explicitly selected shell within the approved boundary."""

    _OUTPUT_LIMIT = 1_000_000
    _SYSTEM_MOUNTS = ("/usr", "/usr/local", "/bin", "/sbin", "/lib", "/lib64")

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        values = config or {}
        for key in ("workspace_root", "workdir"):
            if values.get(key):
                validate_windows_path(values[key])
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

    async def execute_command(
        self, command: str, timeout: int = 30, *, on_spawn: Any = None, on_exit: Any = None, interactive: bool = False,
        shell: str = "direct",
    ) -> SandboxExecutionResult:
        shell = resolve_command_shell(shell)
        if not command.strip() or "\x00" in command:
            raise ValueError("command must be non-empty text without NUL")
        if shell == "direct":
            try:
                args = shlex.split(command)
            except ValueError as exc:
                raise ValueError("command has invalid quoting") from exc
            if not args:
                raise ValueError("command must not be empty")
        else:
            args = powershell_argv(command, shell, interactive=interactive)

        return await self.execute_argv(args, timeout, on_spawn=on_spawn, on_exit=on_exit,
                                       interactive=interactive, shell=shell)

    async def execute_argv(
        self, args: list[str], timeout: int = 30, *, on_spawn: Any = None, on_exit: Any = None,
        interactive: bool = False, shell: str = "direct",
    ) -> SandboxExecutionResult:
        """Run already-separated arguments without a shell or a POSIX quoting round trip."""
        if not args or not args[0] or any(not isinstance(arg, str) or "\x00" in arg for arg in args):
            raise ValueError("argv must contain an executable and NUL-free text arguments")
        if timeout <= 0:
            raise ValueError("command timeout must be positive")

        # Namespace availability can take up to two seconds to probe. Keep the
        # API event loop responsive while checking it, before starting any tool.
        argv, sandboxed, executable = await asyncio.to_thread(self._build_argv, args)
        start = time.monotonic()
        # Only command tools request durable workspace logs. Search subprocesses
        # retain their existing temporary output and do not create artifacts.
        def output_file():
            if self.output_directory is None:
                return tempfile.TemporaryFile()
            return tempfile.NamedTemporaryFile(mode="w+b", prefix="command_", suffix=".log",
                                               dir=self.output_directory, delete=False)
        with output_file() as stdout_file, output_file() as stderr_file:
            spawning = asyncio.create_task(asyncio.create_subprocess_exec(
                *argv,
                stdin=asyncio.subprocess.PIPE if interactive else asyncio.subprocess.DEVNULL,
                stdout=stdout_file,
                stderr=stderr_file,
                cwd=str(self.workdir),
                env=self._minimal_environment(),
                start_new_session=os.name == "posix",
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            ))
            # Cancellation during CreateProcess/fork must still acquire the
            # process handle so the same owner can stop and reap the child.
            try:
                process = await asyncio.shield(spawning)
            except asyncio.CancelledError:
                process = await spawning
                await self._stop_and_wait(process)
                raise
            timed_out = False
            try:
                if on_spawn is not None:
                    on_spawn(process, stdout_file, stderr_file, self._kill_process_group)
                await asyncio.wait_for(process.wait(), timeout)
            except asyncio.TimeoutError:
                timed_out = True
            finally:
                try:
                    # On POSIX, a normally exiting parent can leave children in
                    # its process group. Stop those too before releasing logs.
                    await self._stop_and_wait(process)
                finally:
                    if on_exit is not None:
                        on_exit()

            stdout_file.seek(0)
            stderr_file.seek(0)
            stdout_bytes = stdout_file.read(self.output_limit + 1)
            stderr_bytes = stderr_file.read(self.output_limit + 1)
            stdout_path = str(stdout_file.name) if self.output_directory is not None else ""
            stderr_path = str(stderr_file.name) if self.output_directory is not None else ""

        stdout, stdout_error = _decode_preview(stdout_bytes, self.output_limit)
        stderr, stderr_error = _decode_preview(stderr_bytes, self.output_limit)
        return SandboxExecutionResult(
            exit_code=-1 if timed_out else int(process.returncode or 0),
            stdout=stdout,
            stderr=stderr or ("command timed out" if timed_out else ""),
            duration_ms=(time.monotonic() - start) * 1000,
            timed_out=timed_out,
            output_truncated=(
                len(stdout_bytes) > self.output_limit or len(stderr_bytes) > self.output_limit
            ),
            sandboxed=sandboxed,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            shell=shell,
            executable=executable,
            output_decoding_errors=stdout_error or stderr_error,
        )

    async def execute_python(
        self, code: str, timeout: int = 30
    ) -> SandboxExecutionResult:
        # Workspace environments take priority; Core's interpreter is not a project runtime.
        executable = None
        for name in ("python", "python3"):
            try:
                executable = self._resolve_argv([name])[0]
                break
            except FileNotFoundError:
                continue
        if executable is None:
            raise RuntimeError("Python executable is unavailable in the workspace execution PATH")
        return await self.execute_argv([executable, "-c", code], timeout)

    def set_limits(self, cpu_seconds: float, memory_mb: int) -> None:
        """Reject unsupported quotas instead of acknowledging an unenforced limit."""
        if cpu_seconds < 0 or memory_mb < 0:
            raise ValueError("sandbox limits must not be negative")
        if cpu_seconds or memory_mb:
            raise NotImplementedError("CPU and memory quotas are not implemented; only wall-clock timeouts are enforced")

    def _build_argv(self, args: list[str]) -> tuple[list[str], bool, str]:
        if self.mode == "danger_full_access":
            if not self.allow_network:
                raise PermissionError("Host execution requires explicit network authorization; no command was started")
            resolved = self._resolve_argv(args)
            return resolved, False, resolved[0]
        bubblewrap = shutil.which("bwrap") if platform.system() == "Linux" else None
        if bubblewrap and _bubblewrap_works(bubblewrap, self.allow_network):
            resolved = self._resolve_argv(args)
            if not self._visible_in_sandbox(Path(resolved[0]).resolve()):
                raise SandboxUnavailableError("Executable is outside the sandbox mounts. No command was started.")
            return self._bubblewrap_argv(bubblewrap, resolved), True, resolved[0]
        raise SandboxUnavailableError(
            f"Restricted process sandbox unavailable on {platform.system()}. No command was started."
        )

    def _resolve_argv(self, args: list[str]) -> list[str]:
        """Resolve against the tool PATH, never Windows' implicit current-directory search."""
        executable = Path(args[0])
        if executable.is_absolute() or any(separator in args[0] for separator in (os.sep, os.altsep) if separator):
            candidates = [executable if executable.is_absolute() else self.workdir / executable]
        else:
            candidates = [Path(directory) / executable for directory in self._execution_path().split(os.pathsep)
                          if directory]
        for candidate in candidates:
            resolved = shutil.which(str(candidate))
            if resolved:
                if os.name == "nt" and Path(resolved).suffix.casefold() in {".cmd", ".bat"}:
                    raise ValueError("Windows batch files require shell=powershell or shell=pwsh; direct argv cannot safely quote cmd.exe syntax")
                return [resolved, *args[1:]]
        raise FileNotFoundError(f"Executable not found in the tool PATH: {args[0]}")

    def _bubblewrap_argv(self, binary: str, args: list[str]) -> list[str]:
        command = [
            binary,
            "--die-with-parent",
            "--new-session",
            "--unshare-all",
            "--unshare-user",
            "--disable-userns",
            "--cap-drop", "ALL",
        ]
        if self.allow_network:
            command.append("--share-net")
        command.extend(["--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp"])

        for source in self._SYSTEM_MOUNTS:
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
                self._execution_path(),
                "--setenv",
                "LANG",
                os.environ.get("LANG", "C.UTF-8"),
                "--setenv",
                "LC_ALL",
                os.environ.get("LC_ALL", "C.UTF-8"),
                "--setenv",
                "TMPDIR",
                "/tmp",
                "--setenv", "PYTHONUTF8", "1",
                "--setenv", "PYTHONIOENCODING", "utf-8",
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

    def _visible_in_sandbox(self, directory: Path) -> bool:
        return directory.is_relative_to(self.workspace_root) or any(
            directory.is_relative_to(Path(root)) for root in self._SYSTEM_MOUNTS
        )

    def _execution_path(self) -> str:
        environment_bin = Path(".venv") / ("Scripts" if os.name == "nt" else "bin")
        candidates = [str(root / environment_bin) for root in (self.workdir, self.workspace_root)]
        candidates.extend(os.environ.get("PATH", os.defpath).split(os.pathsep))
        directories: list[str] = []
        for candidate in candidates:
            if not candidate:
                continue
            if os.name == "nt":
                candidate = candidate.strip('"')
            directory = Path(candidate).expanduser()
            if not directory.is_absolute():
                directory = self.workdir / directory
            if not directory.is_dir() or is_sensitive_path(directory):
                continue
            # Changing PATH must not widen the mount boundary to arbitrary home directories.
            if self.mode != "danger_full_access" and not self._visible_in_sandbox(directory.resolve()):
                continue
            value = str(directory)
            if value not in directories:
                directories.append(value)
        return os.pathsep.join(directories)

    def _minimal_environment(self) -> dict[str, str]:
        temporary_directory = tempfile.gettempdir()
        environment = {
            "PATH": self._execution_path(),
            "HOME": temporary_directory,
            "LANG": os.environ.get("LANG", "C.UTF-8"),
            "LC_ALL": os.environ.get("LC_ALL", "C.UTF-8"),
            "TMPDIR": temporary_directory,
            "TMP": temporary_directory,
            "TEMP": temporary_directory,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_PAGER": "cat",
            "PYTHONUTF8": "1",
            "PYTHONIOENCODING": "utf-8",
            "NoDefaultCurrentDirectoryInExePath": "1",
        }
        if os.name == "nt":
            for key in ("SYSTEMROOT", "WINDIR", "PATHEXT"):
                if value := os.environ.get(key):
                    environment[key] = value
        return environment

    @classmethod
    async def _stop_and_wait(cls, process: asyncio.subprocess.Process) -> None:
        try:
            await cls._kill_process_group(process)
        finally:
            await process.wait()

    @staticmethod
    async def _kill_process_group(process: asyncio.subprocess.Process) -> None:
        if os.name == "posix":
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        else:
            if process.returncode is not None:
                return
            # Use Windows' maintained process-tree operation, not a PID walker.
            # This is cleanup, not a sandbox/Job Object or a detached-job API.
            root = os.environ.get("SYSTEMROOT")
            if not root:
                process.kill()
                await process.wait()
                raise RuntimeError("SystemRoot unavailable; only the direct process could be stopped")
            killer = None
            try:
                killer = await asyncio.create_subprocess_exec(
                    str(Path(root) / "System32" / "taskkill.exe"), "/PID", str(process.pid), "/T", "/F",
                    stdin=asyncio.subprocess.DEVNULL,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
                await asyncio.wait_for(killer.wait(), timeout=10)
            except BaseException:
                if killer is not None:
                    if killer.returncode is None:
                        killer.kill()
                    await killer.wait()
                if process.returncode is None:
                    process.kill()
                await process.wait()
                raise
            if killer.returncode:
                if process.returncode is None:
                    process.kill()
                await process.wait()
                raise RuntimeError("Windows process-tree cleanup could not be confirmed; the direct process has exited")

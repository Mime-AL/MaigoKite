"""Fixed ripgrep operations for Windows read tools, separate from shell execution.

Ripgrep discovers names with its ignore/glob engine. Content searches run on a
bounded snapshot made through the handle-anchored file reader, so ripgrep never
opens live content paths that can be swapped for junctions. This trusts the
installed ripgrep executable; it is not an OS process sandbox.
"""
from __future__ import annotations

import asyncio
import json
import os
import shutil
import tempfile
from dataclasses import replace
from pathlib import Path

from agent.security.sensitive_paths import is_sensitive_path, search_exclusions, validate_windows_path
from agent.security.workspace_fs import read_file, windows_directory
from agent.utils.sandbox import SandboxExecutionResult, SandboxExecutor

_MAX_FILES = 2000
_FILE_BYTES = 2 * 1024 * 1024
_SNAPSHOT_BYTES = 32 * 1024 * 1024


def _ripgrep(root: Path, workspace: Path) -> str:
    # Never run a workspace-provided rg.exe with the backend user's authority.
    for directory in os.environ.get("PATH", "").split(os.pathsep):
        candidate = Path(directory.strip('"'))
        if not candidate.is_absolute():
            continue
        executable = (candidate / "rg.exe").resolve()
        if (not executable.drive.startswith("\\\\")
                and not executable.is_relative_to(root) and not executable.is_relative_to(workspace)
                and shutil.which(str(executable))):
            return str(executable)
    raise FileNotFoundError("Install a trusted ripgrep on PATH outside the workspace and searched directory")


async def search(
    root: Path, *, workspace: Path, pattern: str, files_only: bool, target: Path | None = None,
    ignore_case: bool = False, context_lines: int = 0,
) -> SandboxExecutionResult:
    """Accept product search fields, never arbitrary argv, environment or an executable."""
    if os.name != "nt":
        raise RuntimeError("Windows search backend used on another platform")
    if not pattern or "\0" in pattern or not 0 <= context_lines <= 20:
        raise ValueError("invalid search pattern or context line limit")
    root = root.resolve(strict=True)
    if root.drive.startswith("\\\\"):
        raise PermissionError("read-only search requires a local Windows directory")
    if is_sensitive_path(root):
        raise PermissionError("protected credential directory")
    executable = _ripgrep(root, workspace.resolve())
    common = [executable, "--no-config", "--no-follow", "--no-ignore-parent", "--no-ignore-global"]
    async with asyncio.timeout(30):
        # Ripgrep may read in-tree ignore rules but cannot be configured with
        # --pre, --search-zip, extra paths or a shell. A fresh cwd also keeps
        # workspace DLLs and .venv/Scripts out of Windows' loader search path.
        with windows_directory(root), tempfile.TemporaryDirectory(prefix="maigokite-search-") as directory:
            temporary = Path(directory)
            snapshot = temporary / "files"
            snapshot.mkdir()
            executor = SandboxExecutor({"workspace_root": temporary, "workdir": temporary})
            if target is not None and not target.exists():
                return SandboxExecutionResult(exit_code=2, stderr="Search target does not exist.")
            if target is not None and target.is_file():
                candidates = [str(target.relative_to(root))]
                discovery = SandboxExecutionResult(exit_code=0)
            else:
                argv = [*common, "--files", "--null", "--sort", "path",
                        *(["--glob", pattern] if files_only else []), *search_exclusions(), "--", str(root)]
                discovery = await executor._capture(argv, 30, sandboxed=False, executable=executable)
                if discovery.timed_out or discovery.exit_code not in {0, 1}:
                    # Parser diagnostics can contain ignore-file contents.
                    return replace(discovery, stderr="File discovery failed; check directory access and ignore rules.")
                candidates = [str(Path(name).relative_to(root)) for name in discovery.stdout.split("\0")[:-1]]
            limited = discovery.output_truncated or len(candidates) > _MAX_FILES
            names: list[str] = []
            total = 0
            for name in candidates[:_MAX_FILES]:
                await asyncio.sleep(0)
                relative = Path(name)
                if relative.is_absolute() or ".." in relative.parts or is_sensitive_path(relative):
                    limited = True
                    continue
                try:
                    validate_windows_path(relative)
                    if is_sensitive_path((root / relative).resolve()):
                        limited = True
                        continue
                    data, info = read_file(root, str(relative), 0 if files_only else _FILE_BYTES)
                except (OSError, ValueError):
                    limited = True
                    continue
                names.append(relative.as_posix())
                if files_only:
                    continue
                if info.st_size > _FILE_BYTES or len(data) > _FILE_BYTES:
                    limited = True
                    continue
                if total + len(data) > _SNAPSHOT_BYTES:
                    limited = True
                    break
                destination = snapshot / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(data)
                total += len(data)
            if files_only:
                return replace(discovery, stdout="".join(name + "\0" for name in names), stderr="",
                               output_truncated=limited)
            # Selection already applied ignores. Staged ignore files must
            # not change that selection when searching the snapshot.
            argv = [*common, "--json", "--no-ignore", "--hidden", "--sort", "path",
                    "--context", str(context_lines), *(["--ignore-case"] if ignore_case else []),
                    "--", pattern, "files"]
            result = await executor._capture(argv, 30, sandboxed=False, executable=executable)
            rows = []
            for line in result.stdout.splitlines():
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    if result.output_truncated:
                        break
                    raise
                path = event.get("data", {}).get("path", {})
                if isinstance(path.get("text"), str):
                    path["text"] = Path(path["text"]).relative_to("files").as_posix()
                rows.append(json.dumps(event, ensure_ascii=False))
            return replace(result, stdout="\n".join(rows), output_truncated=result.output_truncated or limited,
                           stderr="Content search failed; check the pattern." if result.exit_code not in {0, 1} else "")

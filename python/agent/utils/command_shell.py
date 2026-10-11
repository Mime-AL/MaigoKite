"""PowerShell CLI glue, not a shell parser or an authorization boundary."""

from __future__ import annotations

import base64
import os
import shutil
from pathlib import Path


def powershell_executable(shell: str) -> str:
    if shell == "powershell":
        if os.name != "nt":
            raise FileNotFoundError(
                "Windows PowerShell 5.1 is only available on Windows; use shell=pwsh for PowerShell 7"
            )
        root = os.environ.get("SYSTEMROOT")
        if root:
            candidate = Path(root) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"
            if candidate.is_file():
                return str(candidate)
    elif shell != "pwsh":
        raise ValueError("expected powershell or pwsh")
    # Do not let an executable in the task's cwd shadow the selected shell.
    candidates = os.environ.get("PATH", os.defpath).split(os.pathsep)
    if shell == "pwsh":
        for value in candidates:
            if not value or not Path(value).is_absolute():
                continue
            candidate = Path(value) / ("pwsh.exe" if os.name == "nt" else "pwsh")
            executable = shutil.which(str(candidate))
            if executable:
                return str(Path(executable).resolve())
    raise FileNotFoundError(f"{shell} is not installed or not available in PATH")


def resolve_command_shell(shell: str) -> str:
    """Resolve auto before approval so the selected dialect is part of its hash."""
    if shell not in {"auto", "direct", "powershell", "pwsh"}:
        raise ValueError("shell must be auto, direct, powershell (Windows 5.1), or pwsh (7+)")
    if shell != "auto":
        return shell
    if os.name != "nt":
        return "direct"
    try:
        powershell_executable("pwsh")
    except FileNotFoundError:
        return "powershell"
    return "pwsh"


def powershell_argv(command: str, shell: str, *, interactive: bool = False) -> list[str]:
    """Both editions accept UTF-16LE EncodedCommand; all product text I/O is UTF-8.

    Encoding is transport only. PermissionPolicy sees the original script. Do
    not change file cmdlet defaults, execution policy, or the user's profile.
    """
    executable = powershell_executable(shell)
    version_check = (
        "$PSVersionTable.PSVersion.Major -lt 7" if shell == "pwsh"
        else "$PSVersionTable.PSVersion.Major -ne 5 -or $PSVersionTable.PSVersion.Minor -lt 1"
    )
    script = (
        "$ErrorActionPreference = 'Stop'\n"
        "$ProgressPreference = 'SilentlyContinue'\n"
        "[Console]::InputEncoding = New-Object System.Text.UTF8Encoding($false)\n"
        "[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)\n"
        "$OutputEncoding = [Console]::OutputEncoding\n"
        f"if ({version_check}) {{ [Console]::Error.WriteLine('Unsupported PowerShell version'); exit 1 }}\n"
        "if (Test-Path variable:PSStyle) { $PSStyle.OutputRendering = 'PlainText' }\n"
        "$global:LASTEXITCODE = 0\n"
        "try {\n& {\n" + command + "\n}\n"
        "if (-not $?) { if ($LASTEXITCODE) { exit $LASTEXITCODE }; exit 1 }\n"
        "exit $LASTEXITCODE\n"
        "} catch { [Console]::Error.WriteLine($_.ToString()); exit 1 }\n"
    )
    encoded = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
    argv = [executable, "-NoLogo", "-NoProfile", "-InputFormat", "Text", "-OutputFormat", "Text"]
    if not interactive:
        argv.append("-NonInteractive")
    argv.extend(["-EncodedCommand", encoded])
    # Windows CreateProcess has a 32767 UTF-16 code-unit command-line limit.
    # Leave room for quoting and the executable path, including emoji/surrogates.
    if os.name == "nt" and sum(len(arg.encode("utf-16-le")) // 2 + 3 for arg in argv) >= 32_767:
        raise ValueError("PowerShell command is too long; use a workspace script file and a short invocation")
    return argv

"""Format failures for model messages, persisted task records and UI events.

SDK exception strings may contain credentials, request bodies or local paths.
Only explicitly authored product diagnostics may cross these boundaries intact.
"""

from __future__ import annotations


class UserFacingError(ValueError):
    """A product-authored diagnostic containing no third-party exception text."""


def public_error(error: BaseException) -> str:
    """Preserve actionable product errors without exposing arbitrary exception text."""
    while isinstance(error, BaseExceptionGroup) and len(error.exceptions) == 1:
        error = error.exceptions[0]
    if isinstance(error, UserFacingError):
        return str(error)
    status = getattr(error, "status_code", None)
    if type(status) is int and 400 <= status <= 599:
        if status in {401, 403}:
            return f"服务拒绝访问（HTTP {status}），请检查凭证与访问权限。"
        if status == 429:
            return "服务请求受限（HTTP 429），请稍后重试或检查服务状态。"
        return f"服务请求失败（HTTP {status}），请检查接口地址、参数与服务状态。"
    if isinstance(error, FileNotFoundError):
        return "目标文件或程序不存在，请检查所选路径与安装情况。"
    if isinstance(error, PermissionError):
        return "操作被拒绝，请检查工作区、文件访问权限或当前授权。"
    if isinstance(error, TimeoutError):
        return "操作超时，请检查服务连接或缩小任务范围。"
    if isinstance(error, (ConnectionError, OSError)):
        return "无法访问文件、程序或服务，请检查路径、权限和连接。"
    # Keep the exception type for diagnosis; args/body/response are untrusted.
    return f"操作失败（{type(error).__name__}），请检查服务配置和输入。"

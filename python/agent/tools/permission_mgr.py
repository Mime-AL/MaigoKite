"""ToolPolicy implementation for phase one."""
from __future__ import annotations
import re
import shlex
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path
from typing import Any

class RiskLevel(IntEnum):
    L1=1; L2=2; L3=3; L4=4; L5=5

@dataclass(frozen=True)
class PolicyDecision:
    outcome: str
    risk: RiskLevel
    reason: str
    arguments: dict[str, Any]

class PermissionRequired(PermissionError):
    def __init__(self, decision: PolicyDecision) -> None:
        super().__init__(decision.reason)
        self.decision = decision

class PermissionManager:
    BASE_RISK = {
        "file_read":RiskLevel.L1,"glob":RiskLevel.L1,"grep":RiskLevel.L1,
        "todo_write":RiskLevel.L2,"sleep":RiskLevel.L2,
        "web_search":RiskLevel.L3,"web_fetch":RiskLevel.L3,"bash":RiskLevel.L3,
        "file_write":RiskLevel.L4,"file_edit":RiskLevel.L4,
    }
    MODES={"read_only","workspace","full_access"}
    LEGACY_MODES={
        "plan":"read_only","manual":"read_only",
        "accept_edits":"workspace","auto":"full_access",
    }
    _HARD_DENY=re.compile(r"(^|\s)(rm\s+-rf\s+/($|\s)|mkfs(?:\.|\s)|shutdown($|\s)|reboot($|\s)|:\(\)\s*\{)",re.I)
    _LOW_RISK_COMMANDS={"pwd","ls","cat","head","tail","wc","rg","grep","git"}

    @classmethod
    def normalize_mode(cls, mode:str)->str:
        normalized=cls.LEGACY_MODES.get(mode,mode)
        if normalized not in cls.MODES: raise ValueError(f"invalid permission mode: {mode}")
        return normalized

    def __init__(self, mode: str="workspace", workspace_root: str|Path=".") -> None:
        self.mode=self.normalize_mode(mode); self.workspace_root=Path(workspace_root).expanduser().resolve()
        if self.workspace_root == Path(self.workspace_root.anchor):
            raise ValueError("workspace root must not be a filesystem root")
        self._grants:dict[str,set[str]]={}
    def grant(self, tool_name:str, permission:str)->None: self._grants.setdefault(tool_name,set()).add(permission)
    def revoke(self, tool_name:str, permission:str)->None: self._grants.get(tool_name,set()).discard(permission)
    def check(self, tool_name:str, permission:str)->bool: return permission in self._grants.get(tool_name,set())
    def set_scope(self, tool_name:str, scope:dict[str,Any])->None: self._grants.setdefault(tool_name,set()).add(f"scope:{scope}")
    def get_permissions(self, tool_name:str)->set[str]: return set(self._grants.get(tool_name,set()))

    def evaluate(
        self, tool_name:str, arguments:dict[str,Any], approved:bool=False,
        risk_override:int|None=None, mode:str|None=None
    )->PolicyDecision:
        try: effective_mode = self.normalize_mode(mode or self.mode)
        except ValueError:
            return PolicyDecision("deny",RiskLevel.L5,"invalid permission mode",arguments)
        if tool_name not in self.BASE_RISK and risk_override is None: return PolicyDecision("deny",RiskLevel.L5,"unknown capability",arguments)
        base_risk=self.BASE_RISK.get(tool_name,RiskLevel(risk_override or 5))
        risk=RiskLevel(max(int(base_risk), int(risk_override or base_risk)))
        normalized=dict(arguments)
        if tool_name.startswith("file_") or tool_name in {"glob","grep"}:
            key="root_dir" if tool_name=="glob" else "path"
            if key in normalized:
                resolved=Path(str(normalized[key])).expanduser()
                if not resolved.is_absolute(): resolved=self.workspace_root/resolved
                resolved=resolved.resolve()
                try: resolved.relative_to(self.workspace_root)
                except ValueError: return PolicyDecision("deny",RiskLevel.L5,"path is outside workspace",normalized)
                normalized[key]=str(resolved)
        if tool_name=="bash":
            command=str(normalized.get("command",""))
            if self._HARD_DENY.search(command): return PolicyDecision("deny",RiskLevel.L5,"command matches hard-deny policy",normalized)
            try: parts=shlex.split(command)
            except ValueError: return PolicyDecision("deny",RiskLevel.L5,"command has invalid quoting",normalized)
            if not parts: return PolicyDecision("deny",RiskLevel.L5,"command must not be empty",normalized)
            executable=Path(parts[0]).name
            if executable not in self._LOW_RISK_COMMANDS or any(t in command for t in (">","|",";","&&","||","`","$(")): risk=RiskLevel.L5
            if executable=="git" and (len(parts)<2 or parts[1] not in {"status","diff","log","show"}): risk=RiskLevel.L5
            dangerous_options={"--pre","--pre-glob","--ext-diff","--textconv","--output","-o"}
            if any(argument in dangerous_options or any(argument.startswith(prefix+"=") for prefix in dangerous_options) for argument in parts[1:]): risk=RiskLevel.L5
            for argument in parts[1:]:
                path_argument=argument
                if argument.startswith("-") and "=" in argument:
                    path_argument=argument.split("=",1)[1]
                elif argument.startswith("-") and "/" in argument:
                    path_argument=argument[argument.index("/"):]
                elif argument.startswith("-"):
                    continue
                if not ("/" in path_argument or path_argument.startswith(".")):
                    continue
                candidate=Path(path_argument).expanduser()
                if not candidate.is_absolute(): candidate=self.workspace_root/candidate
                try: candidate.resolve().relative_to(self.workspace_root)
                except ValueError: return PolicyDecision("deny",RiskLevel.L5,"command path is outside workspace",normalized)
            if "workdir" in normalized and normalized["workdir"] is not None:
                workdir=Path(str(normalized["workdir"])).expanduser()
                if not workdir.is_absolute(): workdir=self.workspace_root/workdir
                workdir=workdir.resolve()
                try: workdir.relative_to(self.workspace_root)
                except ValueError: return PolicyDecision("deny",RiskLevel.L5,"workdir is outside workspace",normalized)
                normalized["workdir"]=str(workdir)
            else:
                normalized["workdir"]=str(self.workspace_root)
        auto=risk==RiskLevel.L1
        auto=auto or (effective_mode=="workspace" and (
            risk<=RiskLevel.L2 or (risk==RiskLevel.L4 and tool_name in {"file_write","file_edit"})
            or (risk<=RiskLevel.L3 and tool_name=="bash")
        ))
        auto=auto or (effective_mode=="full_access" and risk<=RiskLevel.L4)
        if risk==RiskLevel.L5: auto=False
        if approved or auto: return PolicyDecision("allow",risk,"allowed by policy",normalized)
        return PolicyDecision("approval_required",risk,"explicit approval required",normalized)

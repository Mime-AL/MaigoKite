"""Tool execution pipeline: validate, authorize, execute, audit."""
from __future__ import annotations
from typing import Any
from agent.repository import SQLiteRepository
from agent.tools.base import ExecutionContext, ToolResult, ToolResultStream
from agent.tools.permission_mgr import PermissionManager, PermissionRequired, PolicyDecision, RiskLevel
from agent.tools.tool_registry import ToolRegistry
from agent.security.injection_filter import InjectionFilter

class ExecutionEngine:
    def __init__(self, registry:ToolRegistry, policy:PermissionManager, repository:SQLiteRepository) -> None:
        self.registry=registry; self.policy=policy; self.repository=repository; self._cancelled:set[str]=set(); self.input_filter=InjectionFilter()

    async def execute_step(self, step_config:dict[str,Any], context:ExecutionContext)->ToolResult|ToolResultStream:
        return await self.execute_tool(step_config["tool"],step_config.get("arguments",{}),context)

    async def authorize_tool(
        self, tool_name:str, arguments:dict[str,Any], context:ExecutionContext
    )->PolicyDecision:
        """Validate and authorize a call without starting the tool."""
        workspace_id=str(context.metadata.get("workspace_id","personal"))
        actor=str(context.metadata.get("principal_id","local-user"))
        tool=self.registry.get(tool_name)
        enabled=context.metadata.get("enabled_tools")
        selected_name="exec_command" if tool_name=="bash" else tool_name
        if enabled is not None and selected_name not in enabled:
            await self.repository.record_audit(
                workspace_id,actor,"tool.denied",tool_name,"denied",
                {"reason":"tool is not enabled"},
            )
            raise PermissionError("tool is not enabled")
        if tool is None:
            decision=PolicyDecision("deny",RiskLevel.L5,"unknown capability",dict(arguments))
            await self.repository.record_audit(
                workspace_id,actor,"tool.denied",tool_name,"denied",
                {"reason":decision.reason,"risk":decision.risk.name},
            )
            raise PermissionError(decision.reason)
        clean=self.input_filter.sanitize_arguments(self.registry.validator.sanitize(tool_name,arguments))
        # Same trusted tool metadata as the LangGraph path. Workspace settings
        # and request metadata cannot supply a second permission matrix.
        risk_override=getattr(tool,"risk_level",None)
        policy=self.policy.for_workspace(context.metadata.get("workspace_root",self.policy.workspace_root))
        decision=policy.evaluate(
            tool_name,clean,bool(context.metadata.get("approved")),risk_override,
            str(context.metadata.get("permission_mode") or self.policy.mode),
        )
        if decision.outcome=="deny":
            await self.repository.record_audit(workspace_id,actor,"tool.denied",tool_name,"denied",{"reason":decision.reason,"risk":decision.risk.name})
            raise PermissionError(decision.reason)
        if decision.outcome=="approval_required":
            await self.repository.record_audit(workspace_id,actor,"tool.approval_required",tool_name,"pending",{"risk":decision.risk.name})
            raise PermissionRequired(decision)
        return decision

    async def execute_authorized(
        self, tool_name:str, decision:PolicyDecision, context:ExecutionContext
    )->ToolResult|ToolResultStream:
        """Execute a previously authorized, normalized tool call."""
        if decision.outcome!="allow": raise PermissionError("tool call is not authorized")
        if context.task_id in self._cancelled or context.cancellation_token: raise RuntimeError("task cancelled")
        workspace_id=str(context.metadata.get("workspace_id","personal")); actor=str(context.metadata.get("principal_id","local-user"))
        try:
            result=await self.registry.invoke(tool_name,decision.arguments,context)
            if isinstance(result,ToolResultStream): result=await result.collect()
        except Exception as exc:
            await self.repository.record_audit(workspace_id,actor,"tool.failed",tool_name,"failed",{"error_type":type(exc).__name__})
            raise
        succeeded=bool(getattr(result,"success",True))
        await self.repository.record_audit(
            workspace_id,actor,"tool.completed" if succeeded else "tool.failed",tool_name,
            "success" if succeeded else "failed",
            {"risk":decision.risk.name,"summary":getattr(result,"summary","")[:500],
             **({"error_code":getattr(result,"error_code",None)} if not succeeded else {})},
        )
        return result

    async def execute_tool(self, tool_name:str, arguments:dict[str,Any], context:ExecutionContext)->ToolResult|ToolResultStream:
        decision=await self.authorize_tool(tool_name,arguments,context)
        return await self.execute_authorized(tool_name,decision,context)

    async def cancel(self, task_id:str|None=None)->None:
        if task_id: self._cancelled.add(task_id)

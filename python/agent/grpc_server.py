"""Python gRPC service; all domain writes delegate to AgentCore."""
from __future__ import annotations
import asyncio,json
from typing import Any,AsyncIterator
import grpc
from agent.grpc_generated import agent_pb2,agent_pb2_grpc
from agent.models.runtime import ChatModelSettings

class AgentServiceServicer(agent_pb2_grpc.AgentServiceServicer):
    def __init__(self,agent_core,event_bus,observability)->None:self._core=agent_core;self._event_bus=event_bus;self._obs=observability
    @staticmethod
    def _conversation(item:dict[str,Any])->agent_pb2.Conversation:
        return agent_pb2.Conversation(id=item["id"],workspace_id=item["workspace_id"],title=item["title"],model_id=item["model_id"],permission_mode=item["permission_mode"],response_mode=item.get("response_mode","balanced"),created_at=item["created_at"],updated_at=item["updated_at"],message_count=int(item.get("message_count",0)))
    @staticmethod
    def _message(item:dict[str,Any])->agent_pb2.Message:return agent_pb2.Message(**item)
    @staticmethod
    def _approval(item:dict[str,Any])->agent_pb2.Approval:
        arguments=item.get("arguments",{})
        scope=arguments.get("path") or arguments.get("workdir") or arguments.get("url") or "current workspace"
        return agent_pb2.Approval(
            id=item["id"],workspace_id=item["workspace_id"],conversation_id=item["conversation_id"],
            task_id=item["task_id"],tool_call_id=item["tool_call_id"],tool_name=item["tool_name"],
            arguments_json=json.dumps(arguments,ensure_ascii=False),resource_scope=str(scope),
            risk_level=item["risk_level"],status=item["status"],version=int(item["version"]),expires_at=item["expires_at"],
        )
    @staticmethod
    def _event(kind:str,payload:dict[str,Any])->agent_pb2.AgentEvent:
        return agent_pb2.AgentEvent(type=kind,task_id=str(payload.get("task_id","")),conversation_id=str(payload.get("conversation_id","")),content=str(payload.get("content","")),payload_json=json.dumps(payload,ensure_ascii=False,default=str))

    async def ProcessMessage(self,request,context)->AsyncIterator[agent_pb2.AgentEvent]:
        if not request.conversation_id:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT,"conversation_id is required")
            return
        try:
            await self._core.get_conversation(request.workspace_id or "personal",request.conversation_id)
        except KeyError:
            await context.abort(grpc.StatusCode.NOT_FOUND,"conversation not found")
            return
        queue:asyncio.Queue[tuple[str,dict[str,Any]]]=asyncio.Queue()
        async def receive(kind:str,payload:dict[str,Any])->None:
            if str(payload.get("conversation_id", "")) == request.conversation_id:
                await queue.put((kind,payload))
        self._event_bus.subscribe("*",receive)
        metadata={"conversation_id":request.conversation_id,"workspace_id":request.workspace_id or "personal","principal_id":request.principal_id or "local-user","attachments":[{"type":a.type,"path":a.path,"url":a.url} for a in request.attachments]}
        task=asyncio.create_task(self._core.run(request.content,metadata))
        try:
            while not task.done() or not queue.empty():
                try:kind,payload=await asyncio.wait_for(queue.get(),0.05)
                except asyncio.TimeoutError:continue
                yield self._event(kind,payload)
            result=await task
            if error:=result.get("error"):
                yield agent_pb2.AgentEvent(type="error",task_id=result.get("task_id",""),conversation_id=result.get("conversation_id",""),code=result.get("error_code","AGENT_ERROR"),message=error,retryable=bool(result.get("retryable")),payload_json=json.dumps(result))
        finally:
            self._event_bus.unsubscribe("*",receive)
            if context.cancelled() and not task.done():task.cancel()

    async def CreateConversation(self,request,context):
        try:item=await self._core.create_conversation(request.workspace_id or "personal",request.title,request.model_id,request.permission_mode or None,request.response_mode or "balanced")
        except (KeyError,ValueError) as exc:await context.abort(grpc.StatusCode.INVALID_ARGUMENT,str(exc))
        return self._conversation(item)
    async def GetConversation(self,request,context):
        try:return self._conversation(await self._core.get_conversation(request.workspace_id or "personal",request.conversation_id))
        except KeyError:await context.abort(grpc.StatusCode.NOT_FOUND,"conversation not found")
    async def ListConversations(self,request,context):return agent_pb2.ConversationList(conversations=[self._conversation(i) for i in await self._core.list_conversations(request.workspace_id or "personal")])
    async def DeleteConversation(self,request,context):
        try:await self._core.delete_conversation(request.workspace_id or "personal",request.conversation_id)
        except KeyError:await context.abort(grpc.StatusCode.NOT_FOUND,"conversation not found")
        return agent_pb2.Empty()
    async def UpdateConversationPermission(self,request,context):
        try:item=await self._core.update_conversation_permission(request.workspace_id or "personal",request.conversation_id,request.permission_mode)
        except KeyError:await context.abort(grpc.StatusCode.NOT_FOUND,"conversation not found")
        except ValueError as exc:await context.abort(grpc.StatusCode.INVALID_ARGUMENT,str(exc))
        return self._conversation(item)
    async def UpdateConversationSettings(self,request,context):
        try:item=await self._core.update_conversation_settings(
            request.workspace_id or "personal",request.conversation_id,
            model_id=request.model_id if request.HasField("model_id") else None,
            response_mode=request.response_mode if request.HasField("response_mode") else None,
            permission_mode=request.permission_mode if request.HasField("permission_mode") else None,
        )
        except KeyError:await context.abort(grpc.StatusCode.NOT_FOUND,"conversation or model not found")
        except ValueError as exc:await context.abort(grpc.StatusCode.INVALID_ARGUMENT,str(exc))
        return self._conversation(item)
    async def ListMessages(self,request,context):
        try:items=await self._core.list_messages(request.conversation_id,request.workspace_id or "personal")
        except KeyError:await context.abort(grpc.StatusCode.NOT_FOUND,"conversation not found")
        return agent_pb2.MessageList(messages=[self._message(i) for i in items])
    async def ListApprovals(self,request,context):
        items=await self._core.repository.list_approvals(request.workspace_id or "personal",request.conversation_id or None)
        return agent_pb2.ApprovalList(approvals=[self._approval(item) for item in items])
    async def DecideApproval(self,request,context)->AsyncIterator[agent_pb2.AgentEvent]:
        workspace_id=request.workspace_id or "personal"
        try:pending=await self._core.repository.get_approval(workspace_id,request.approval_id)
        except KeyError:
            await context.abort(grpc.StatusCode.NOT_FOUND,"approval not found")
            return
        queue:asyncio.Queue[tuple[str,dict[str,Any]]]=asyncio.Queue()
        async def receive(kind:str,payload:dict[str,Any])->None:
            if (
                str(payload.get("conversation_id",""))==pending["conversation_id"]
                and str(payload.get("task_id",""))==pending["task_id"]
            ):
                await queue.put((kind,payload))
        self._event_bus.subscribe("*",receive)
        task=asyncio.create_task(self._core.decide_approval(
            workspace_id,request.approval_id,request.principal_id or "local-user",request.decision,int(request.version)
        ))
        try:
            while not task.done() or not queue.empty():
                try:kind,payload=await asyncio.wait_for(queue.get(),0.05)
                except asyncio.TimeoutError:continue
                yield self._event(kind,payload)
            try:await task
            except (ValueError,PermissionError) as exc:
                yield agent_pb2.AgentEvent(type="error",conversation_id=pending["conversation_id"],task_id=pending["task_id"],code="APPROVAL_INVALID",message=str(exc),payload_json=json.dumps({"message":str(exc)}))
            except Exception as exc:
                yield agent_pb2.AgentEvent(type="error",conversation_id=pending["conversation_id"],task_id=pending["task_id"],code="AGENT_ERROR",message=str(exc),payload_json=json.dumps({"message":str(exc)}))
        finally:
            self._event_bus.unsubscribe("*",receive)
            if context.cancelled() and not task.done():task.cancel()
    async def Health(self,request,context):return agent_pb2.HealthResponse(status="serving",version="0.1.0")
    async def CheckWorkspaceAccess(self,request,context):
        role=await self._core.repository.check_workspace_access(request.workspace_id,request.principal_id)
        return agent_pb2.WorkspaceAccessResponse(allowed=role is not None,role=role or "")
    async def ListAuditEvents(self,request,context):
        items=await self._core.repository.list_audit_events(request.workspace_id or "personal")
        return agent_pb2.AuditEventList(events=[agent_pb2.AuditEvent(**item) for item in items])
    async def RecordAuditEvent(self,request,context):
        await self._core.repository.record_audit(request.workspace_id,request.actor,request.action,request.resource,request.result,{})
        return agent_pb2.Empty()
    @staticmethod
    def _chat_model_settings(item:ChatModelSettings)->agent_pb2.ChatModelSettings:
        return agent_pb2.ChatModelSettings(id=item.id,name=item.name,provider=item.provider,model=item.model,base_url=item.base_url,temperature=item.temperature,max_tokens=item.max_tokens,timeout_seconds=item.timeout_seconds,is_default=item.is_default)
    @staticmethod
    def _chat_model_settings_value(item)->ChatModelSettings:
        return ChatModelSettings(id=item.id,name=item.name,provider=item.provider,model=item.model,base_url=item.base_url,temperature=item.temperature,max_tokens=item.max_tokens,timeout_seconds=item.timeout_seconds,is_default=item.is_default)
    async def GetChatModelSettings(self,request,context):
        return self._chat_model_settings(await self._core.get_chat_model_settings(request.workspace_id or "personal"))
    async def UpdateChatModelSettings(self,request,context):
        try:item=await self._core.update_chat_model_settings(request.workspace_id or "personal",self._chat_model_settings_value(request.settings))
        except ValueError as exc:await context.abort(grpc.StatusCode.INVALID_ARGUMENT,str(exc))
        return self._chat_model_settings(item)
    async def ListChatModels(self,request,context):
        items,default_id=await self._core.list_chat_models(request.workspace_id or "personal")
        return agent_pb2.ChatModelList(models=[self._chat_model_settings(item) for item in items],default_model_id=default_id)
    async def UpsertChatModel(self,request,context):
        try:item=await self._core.upsert_chat_model(request.workspace_id or "personal",self._chat_model_settings_value(request.settings))
        except ValueError as exc:await context.abort(grpc.StatusCode.INVALID_ARGUMENT,str(exc))
        return self._chat_model_settings(item)
    async def DeleteChatModel(self,request,context):
        try:await self._core.delete_chat_model(request.workspace_id or "personal",request.model_id)
        except KeyError:await context.abort(grpc.StatusCode.NOT_FOUND,"model profile not found")
        return agent_pb2.Empty()
    async def SetDefaultChatModel(self,request,context):
        try:items,default_id=await self._core.set_default_chat_model(request.workspace_id or "personal",request.model_id)
        except KeyError:await context.abort(grpc.StatusCode.NOT_FOUND,"model profile not found")
        return agent_pb2.ChatModelList(models=[self._chat_model_settings(item) for item in items],default_model_id=default_id)
    async def ValidateChatModel(self,request,context):
        try:
            await self._core.validate_chat_model(self._chat_model_settings_value(request.settings),request.api_key)
            return agent_pb2.ModelValidationResponse(ok=True,message="connection successful",model=request.settings.model)
        except Exception as exc:
            return agent_pb2.ModelValidationResponse(ok=False,message=str(exc),model=request.settings.model)
    async def SetChatModelCredential(self,request,context):
        await self._core.set_chat_model_credential(request.workspace_id or "personal",request.provider,request.api_key,request.model_id)
        return agent_pb2.Empty()
    async def GetUserPreferences(self,request,context):
        item=await self._core.get_user_preferences(request.workspace_id or "personal",request.subject_user_id or "local-user")
        return agent_pb2.UserPreferences(**item)
    async def UpdateUserPreferences(self,request,context):
        try:item=await self._core.update_user_preferences(request.workspace_id or "personal",request.subject_user_id or "local-user",request.preferences.assistant_name)
        except ValueError as exc:await context.abort(grpc.StatusCode.INVALID_ARGUMENT,str(exc))
        return agent_pb2.UserPreferences(**item)
    async def GetPermissionSettings(self,request,context):
        item=await self._core.get_permission_settings(request.workspace_id or "personal")
        return agent_pb2.PermissionSettings(default_mode=item["default_mode"],tool_levels=item["tool_levels"])
    async def UpdatePermissionSettings(self,request,context):
        try:item=await self._core.update_permission_settings(request.workspace_id or "personal",request.settings.default_mode,dict(request.settings.tool_levels))
        except ValueError as exc:await context.abort(grpc.StatusCode.INVALID_ARGUMENT,str(exc))
        return agent_pb2.PermissionSettings(default_mode=item["default_mode"],tool_levels=item["tool_levels"])

from __future__ import annotations
import asyncio
import json
import shutil
import pytest
from agent.models.chat_provider import ChatResponse,ChatStreamChunk,IChatProvider,ToolCallChunk
from agent.models.runtime import ChatModelSettings
from agent.security.whitelist import Whitelist
from agent.tools.base import ExecutionContext
from agent.tools.permission_mgr import PermissionManager,RiskLevel
from agent.utils.sandbox import _bubblewrap_works


class ToolCallingProvider(IChatProvider):
    @property
    def model_name(self):
        return "tool-fake"

    async def chat(self, messages, **kwargs):
        return ChatResponse("unused")

    async def stream(self, messages, **kwargs):
        if messages[-1].role == "tool":
            yield ChatStreamChunk(content="文件内容是 hello")
            return
        yield ChatStreamChunk(content="我先读取文件。")
        yield ChatStreamChunk(tool_call_chunks=[ToolCallChunk(
            index=0, id="call_read", name="file_read", arguments='{"path":"note.txt"',
        )])
        yield ChatStreamChunk(tool_call_chunks=[ToolCallChunk(index=0, arguments="}")])


class MultiToolApprovalProvider(IChatProvider):
    def __init__(self):
        self.received_tool_ids = []

    @property
    def model_name(self):
        return "multi-tool-fake"

    async def chat(self, messages, **kwargs):
        return ChatResponse("unused")

    async def stream(self, messages, **kwargs):
        tool_messages = [item for item in messages if item.role == "tool"]
        if tool_messages:
            self.received_tool_ids = [item.metadata.get("tool_call_id") for item in tool_messages]
            yield ChatStreamChunk(content="两个工具都已完成")
            return
        yield ChatStreamChunk(tool_call_chunks=[
            ToolCallChunk(
                index=0, id="call_write_first", name="file_write",
                arguments='{"path":"created.txt","content":"created"}',
            ),
            ToolCallChunk(
                index=1, id="call_read_second", name="file_read",
                arguments='{"path":"note.txt"}',
            ),
        ])

@pytest.mark.asyncio
async def test_conversation_and_message_round_trip(core):
    conversation=await core.create_conversation(title="test")
    result=await core.run("你好",{"conversation_id":conversation["id"]})
    assert result["response"]=="reply:你好"
    assert [item["role"] for item in await core.list_messages(conversation["id"])]==["user","assistant"]


@pytest.mark.asyncio
async def test_conversation_uses_selected_model_profile_and_fast_token_budget(core):
    observed = []

    class OptionProvider(IChatProvider):
        def __init__(self, **options): self.options = options
        @property
        def model_name(self): return self.options["model"]
        async def chat(self, messages, **kwargs): return ChatResponse("unused")
        async def stream(self, messages, **kwargs):
            observed.append((self.model_name, kwargs.get("max_tokens")))
            yield ChatStreamChunk(content="fast reply")

    core.provider = None
    core.models._provider_factory = OptionProvider
    profile = await core.upsert_chat_model("personal", ChatModelSettings(
        id="model_fast", name="Fast", provider="ollama", model="qwen",
        base_url="http://127.0.0.1:11434", max_tokens=12000, is_default=True,
    ))
    conversation = await core.create_conversation(
        title="profile", model_id=profile.id, response_mode="fast"
    )
    result = await core.run("hello", {"conversation_id": conversation["id"]})

    assert result["response"] == "fast reply"
    assert observed == [("qwen", 2048)]
    assert conversation["model_id"] == profile.id
    assert conversation["response_mode"] == "fast"

@pytest.mark.asyncio
async def test_read_only_write_requires_approval_and_approved_write_stays_in_workspace(core,tmp_path):
    conversation=await core.create_conversation(title="tool")
    command="/tool file_write "+json.dumps({"path":"result.txt","content":"ok"})
    blocked=await core.run(command,{"conversation_id":conversation["id"]})
    assert blocked["status"]=="waiting_approval"
    approval=blocked["approval"]
    allowed=await core.decide_approval(
        "personal",approval["approval_id"],"local-user","allow",approval["version"]
    )
    assert "Wrote" in allowed["response"] and (tmp_path/"result.txt").read_text()=="ok"
    with pytest.raises(ValueError,match="already been decided"):
        await core.decide_approval(
            "personal",approval["approval_id"],"local-user","allow",approval["version"]
        )


@pytest.mark.asyncio
async def test_approval_event_order_and_consumed_state(core,tmp_path):
    conversation=await core.create_conversation(title="event order")
    events=[]
    async def capture(kind,payload):events.append((kind,payload))
    core.event_bus.subscribe("*",capture)

    blocked=await core.run(
        "/tool file_write "+json.dumps({"path":"ordered.txt","content":"ok"}),
        {"conversation_id":conversation["id"]},
    )

    kinds=[kind for kind,_ in events]
    assert "tool.started" not in kinds
    assert kinds.index("tool.proposed") < kinds.index("task.waiting_approval")
    assert kinds.index("task.waiting_approval") < kinds.index("approval.requested")
    approval=blocked["approval"]
    await core.decide_approval(
        "personal",approval["approval_id"],"local-user","allow",approval["version"]
    )
    decided=await core.repository.get_approval("personal",approval["approval_id"])
    assert decided["status"]=="consumed"
    assert [kind for kind,_ in events].index("approval.decided") < [kind for kind,_ in events].index("tool.started")
    assert (tmp_path/"ordered.txt").read_text(encoding="utf-8")=="ok"


@pytest.mark.asyncio
async def test_multi_tool_batch_resumes_all_calls_after_approval(core,tmp_path):
    (tmp_path/"note.txt").write_text("note",encoding="utf-8")
    provider=MultiToolApprovalProvider()
    core.provider=provider
    conversation=await core.create_conversation(title="multi tool",permission_mode="read_only")

    blocked=await core.run("写文件后读取 note.txt",{"conversation_id":conversation["id"]})
    assert blocked["status"]=="waiting_approval"
    approval=blocked["approval"]
    result=await core.decide_approval(
        "personal",approval["approval_id"],"local-user","allow",approval["version"]
    )

    assert result["status"]=="succeeded"
    assert result["response"]=="两个工具都已完成"
    assert provider.received_tool_ids==["call_write_first","call_read_second"]
    assert (await core.repository.get_tool_call("call_write_first"))["status"]=="succeeded"
    assert (await core.repository.get_tool_call("call_read_second"))["status"]=="succeeded"
    assert (tmp_path/"created.txt").read_text(encoding="utf-8")=="created"


@pytest.mark.asyncio
async def test_client_approved_metadata_cannot_bypass_read_only_mode(core,tmp_path):
    conversation=await core.create_conversation(title="tool")
    command="/tool file_write "+json.dumps({"path":"bypass.txt","content":"no"})
    blocked=await core.run(command,{"conversation_id":conversation["id"],"approved":True})
    assert blocked["status"]=="waiting_approval"
    assert not (tmp_path/"bypass.txt").exists()


@pytest.mark.asyncio
async def test_approval_is_invalidated_if_normalized_arguments_change(core,tmp_path):
    conversation=await core.create_conversation(title="tamper")
    blocked=await core.run(
        "/tool file_write "+json.dumps({"path":"original.txt","content":"safe"}),
        {"conversation_id":conversation["id"]},
    )
    approval=blocked["approval"]
    core.repository._db().execute(
        "UPDATE tool_calls SET arguments_json=? WHERE id=?",
        (json.dumps({"path":str(tmp_path/"changed.txt"),"content":"changed"}),approval["tool_call_id"]),
    )
    core.repository._db().commit()
    with pytest.raises(PermissionError,match="no longer match"):
        await core.decide_approval(
            "personal",approval["approval_id"],"local-user","allow",approval["version"]
        )
    assert not (tmp_path/"original.txt").exists()
    assert not (tmp_path/"changed.txt").exists()


@pytest.mark.asyncio
async def test_expired_approval_disappears_from_pending_snapshot(core):
    conversation=await core.create_conversation(title="expiry")
    await core.repository.create_task_state("task-expired","personal",conversation["id"],"expired","running")
    await core.repository.create_tool_call(
        "call-expired","personal",conversation["id"],"task-expired","file_write",{"path":"expired.txt"}
    )
    approval=await core.repository.create_approval(
        "personal",conversation["id"],"local-user","task-expired","call-expired",
        {"path":"expired.txt"},"L4",ttl_minutes=-1,
    )
    assert await core.list_approvals("personal",conversation["id"])==[]
    assert (await core.repository.get_approval("personal",approval["id"]))["status"]=="expired"


@pytest.mark.asyncio
async def test_model_can_call_tool_and_continue_with_result(core,tmp_path):
    (tmp_path/"note.txt").write_text("hello",encoding="utf-8")
    core.provider=ToolCallingProvider()
    conversation=await core.create_conversation(title="agent loop")
    events=[]
    async def capture(kind,payload):events.append((kind,payload))
    core.event_bus.subscribe("*",capture)
    result=await core.run("读取 note.txt",{"conversation_id":conversation["id"]})
    assert result["status"]=="succeeded"
    assert result["response"]=="文件内容是 hello"
    call=await core.repository.get_tool_call("call_read")
    assert call["status"]=="succeeded"
    reasoning=[payload for kind,payload in events if kind=="reasoning.completed"]
    visible=[payload["content"] for kind,payload in events if kind=="message.delta"]
    assert reasoning[0]["summary"]=="我先读取文件。"
    assert visible==["文件内容是 hello"]


@pytest.mark.asyncio
async def test_provider_reasoning_and_think_blocks_are_not_final_message_content(core):
    class ReasoningProvider(IChatProvider):
        @property
        def model_name(self): return "reasoning-fake"
        async def chat(self, messages, **kwargs): return ChatResponse("unused")
        async def stream(self, messages, **kwargs):
            yield ChatStreamChunk(reasoning="检查上下文。")
            yield ChatStreamChunk(content="<think>规划回答。</think>最终答案。")

    core.provider=ReasoningProvider()
    conversation=await core.create_conversation(title="reasoning")
    events=[]
    async def capture(kind,payload):events.append((kind,payload))
    core.event_bus.subscribe("*",capture)

    result=await core.run("开始",{"conversation_id":conversation["id"]})

    summaries=[payload["summary"] for kind,payload in events if kind=="reasoning.completed"]
    visible=[payload["content"] for kind,payload in events if kind=="message.delta"]
    assert result["response"]=="最终答案。"
    assert summaries==["检查上下文。\n\n规划回答。"]
    assert visible==["最终答案。"]


@pytest.mark.asyncio
async def test_conversation_permission_overrides_global_default(core,tmp_path):
    core._policy.mode="full_access"
    conversation=await core.create_conversation(title="read only",permission_mode="read_only")
    command="/tool file_write "+json.dumps({"path":"read-only.txt","content":"no"})
    blocked=await core.run(command,{"conversation_id":conversation["id"]})
    assert blocked["status"]=="waiting_approval"
    assert not (tmp_path/"read-only.txt").exists()


@pytest.mark.asyncio
async def test_bash_runs_in_normalized_workspace_after_approval(core,tmp_path):
    conversation=await core.create_conversation(title="bash",permission_mode="read_only")
    blocked=await core.run(
        "/tool bash "+json.dumps({"command":"pwd"}),
        {"conversation_id":conversation["id"]},
    )
    approval=blocked["approval"]
    result=await asyncio.wait_for(core.decide_approval(
        "personal",approval["approval_id"],"local-user","allow",approval["version"]
    ),timeout=5)
    assert result["response"].strip()==str(tmp_path)


@pytest.mark.asyncio
async def test_bash_sandbox_blocks_host_reads_but_allows_workspace_writes(core,tmp_path):
    bubblewrap=shutil.which("bwrap")
    if not bubblewrap or not _bubblewrap_works(bubblewrap):
        pytest.skip("bubblewrap is unavailable; arbitrary commands fail closed on this platform")

    conversation=await core.create_conversation(title="sandbox",permission_mode="read_only")
    blocked=await core.run(
        "/tool bash "+json.dumps({"command":"python3 -c 'print(open(\"/etc/passwd\").read())'"}),
        {"conversation_id":conversation["id"]},
    )
    approval=blocked["approval"]
    denied_read=await core.decide_approval(
        "personal",approval["approval_id"],"local-user","allow",approval["version"]
    )
    assert "root:" not in denied_read["response"]
    assert "FileNotFoundError" in denied_read["response"]

    blocked=await core.run(
        "/tool bash "+json.dumps({"command":"python3 -c 'open(\"sandbox.txt\",\"w\").write(\"ok\")'"}),
        {"conversation_id":conversation["id"]},
    )
    approval=blocked["approval"]
    await core.decide_approval(
        "personal",approval["approval_id"],"local-user","allow",approval["version"]
    )
    assert (tmp_path/"sandbox.txt").read_text(encoding="utf-8")=="ok"


@pytest.mark.asyncio
async def test_read_only_mode_allows_workspace_reads(core,tmp_path):
    (tmp_path/"note.txt").write_text("read me",encoding="utf-8")
    conversation=await core.create_conversation(title="read",permission_mode="read_only")
    result=await core.run(
        "/tool file_read "+json.dumps({"path":"note.txt"}),
        {"conversation_id":conversation["id"]},
    )
    assert "read me" in result["response"]
    assert await core.list_approvals("personal",conversation["id"])==[]


@pytest.mark.asyncio
async def test_glob_and_grep_defaults_are_scoped_to_workspace(core,tmp_path):
    (tmp_path/"workspace-only.txt").write_text("workspace needle",encoding="utf-8")
    conversation=await core.create_conversation(title="scoped search",permission_mode="read_only")

    glob_result=await core.run(
        "/tool glob "+json.dumps({"pattern":"workspace-only.txt"}),
        {"conversation_id":conversation["id"]},
    )
    grep_result=await core.run(
        "/tool grep "+json.dumps({"pattern":"workspace needle"}),
        {"conversation_id":conversation["id"]},
    )

    assert "workspace-only.txt" in glob_result["response"]
    assert "workspace-only.txt" in grep_result["response"]


@pytest.mark.asyncio
async def test_remaining_phase_one_native_tools_execute_through_policy(core,tmp_path,monkeypatch):
    (tmp_path/"edit.txt").write_text("before",encoding="utf-8")
    search_tool=core.tool_registry.get("web_search")
    assert search_tool is not None

    async def fake_search(query,max_results):
        return [{"title":"Result","url":"https://example.com","snippet":query}]

    monkeypatch.setattr(search_tool,"_duckduckgo_search",fake_search)
    conversation=await core.create_conversation(title="native tools",permission_mode="full_access")

    edited=await core.run(
        "/tool file_edit "+json.dumps({
            "path":"edit.txt","old_string":"before","new_string":"after",
        }),
        {"conversation_id":conversation["id"]},
    )
    slept=await core.run(
        "/tool sleep "+json.dumps({"seconds":0.001}),
        {"conversation_id":conversation["id"]},
    )
    searched=await core.run(
        "/tool web_search "+json.dumps({"query":"阶段一","engine":"duckduckgo"}),
        {"conversation_id":conversation["id"]},
    )
    fetched=await core.run(
        "/tool web_fetch "+json.dumps({"url":"file:///etc/passwd"}),
        {"conversation_id":conversation["id"]},
    )

    assert "1 replacement(s)" in edited["response"]
    assert (tmp_path/"edit.txt").read_text(encoding="utf-8")=="after"
    assert "slept" in slept["response"]
    assert "example.com" in searched["response"]
    assert "URL must start" in fetched["response"]


@pytest.mark.asyncio
async def test_web_search_failure_emits_actionable_tool_event(core,monkeypatch):
    search_tool=core.tool_registry.get("web_search")
    assert search_tool is not None

    async def failed_search(query,max_results):
        raise RuntimeError("provider offline")

    monkeypatch.setattr(search_tool,"_duckduckgo_search",failed_search)
    conversation=await core.create_conversation(title="search failure",permission_mode="full_access")
    events=[]
    async def capture(kind,payload):events.append((kind,payload))
    core.event_bus.subscribe("*",capture)

    result=await core.run(
        "/tool web_search "+json.dumps({"query":"NS Conjecture mathematics"}),
        {"conversation_id":conversation["id"]},
    )

    assert result["status"]=="succeeded"
    failed=[payload for kind,payload in events if kind=="tool.failed"]
    assert len(failed)==1
    assert failed[0]["code"]=="SEARCH_PROVIDER_UNAVAILABLE"
    assert "设置 → 联网工具" in failed[0]["user_hint"]
    assert failed[0]["action"]=={"label":"配置联网工具","to":"/settings?tab=tools"}
    assert not [payload for kind,payload in events if kind=="tool.completed"]


@pytest.mark.asyncio
async def test_web_search_uses_workspace_tool_credential(core,monkeypatch):
    search_tool=core.tool_registry.get("web_search")
    assert search_tool is not None
    observed=[]

    async def fake_tavily(query,api_key,max_results):
        observed.append((query,api_key,max_results))
        return [{"title":"Result","url":"https://example.com","snippet":"ok"}]

    monkeypatch.setattr(search_tool,"_tavily_search",fake_tavily)
    await core.set_tool_credential("personal","tavily","secret-tavily-key")
    conversation=await core.create_conversation(title="configured search",permission_mode="full_access")
    result=await core.run(
        "/tool web_search "+json.dumps({"query":"configured provider","max_results":3}),
        {"conversation_id":conversation["id"]},
    )

    assert result["status"]=="succeeded"
    assert observed==[("configured provider","secret-tavily-key",3)]
    assert "example.com" in result["response"]


@pytest.mark.asyncio
async def test_web_search_rejects_incomplete_google_credential(core):
    await core.set_tool_credential("personal","google","google-api-key-without-cx")
    conversation=await core.create_conversation(title="invalid search credential",permission_mode="full_access")
    events=[]
    async def capture(kind,payload):events.append((kind,payload))
    core.event_bus.subscribe("*",capture)

    result=await core.run(
        "/tool web_search "+json.dumps({"query":"configured provider","engine":"google"}),
        {"conversation_id":conversation["id"]},
    )

    assert result["status"]=="succeeded"
    failed=[payload for kind,payload in events if kind=="tool.failed"]
    assert failed[0]["code"]=="SEARCH_PROVIDER_INVALID_CONFIGURATION"
    assert failed[0]["action"]["to"]=="/settings?tab=tools"


@pytest.mark.asyncio
async def test_unknown_tool_is_denied_before_started_event(core):
    conversation=await core.create_conversation(title="unknown tool")
    events=[]
    async def capture(kind,payload):events.append((kind,payload))
    core.event_bus.subscribe("*",capture)

    result=await core.run("/tool missing_tool {}",{"conversation_id":conversation["id"]})

    assert "Tool denied" in result["response"]
    assert "tool.started" not in [kind for kind,_ in events]
    failed=[payload for kind,payload in events if kind=="tool.failed"]
    assert failed and failed[0]["denied"] is True
    audit=await core.repository.list_audit_events("personal")
    assert any(item["action"]=="tool.denied" and item["resource"]=="missing_tool" for item in audit)


@pytest.mark.asyncio
async def test_approved_tool_failure_marks_task_failed_and_emits_terminal_event(core):
    conversation=await core.create_conversation(title="approved failure")
    events=[]
    async def capture(kind,payload):events.append((kind,payload))
    core.event_bus.subscribe("*",capture)
    blocked=await core.run(
        "/tool file_write "+json.dumps({"path":".","content":"cannot write a directory"}),
        {"conversation_id":conversation["id"]},
    )
    approval=blocked["approval"]

    with pytest.raises(IsADirectoryError):
        await core.decide_approval(
            "personal",approval["approval_id"],"local-user","allow",approval["version"]
        )

    task=await core.task_manager.get_task(blocked["task_id"])
    assert task is not None and task.status.value=="failed"
    assert "task.failed" in [kind for kind,_ in events]


@pytest.mark.asyncio
async def test_file_read_reports_binary_input_cleanly(core,tmp_path):
    (tmp_path/"binary.dat").write_bytes(b"abc\x00def")
    conversation=await core.create_conversation(title="binary")
    result=await core.run(
        "/tool file_read "+json.dumps({"path":"binary.dat"}),
        {"conversation_id":conversation["id"]},
    )
    assert "Binary file is not supported" in result["response"]


@pytest.mark.asyncio
async def test_todos_are_persistent_and_can_be_completed(core):
    tool=core.tool_registry.get("todo_write")
    assert tool is not None
    context=ExecutionContext("trace","task","step",metadata={"workspace_id":"personal"})
    added=await tool.execute(context,{"operation":"add","text":"完成第一阶段"})
    todo_id=added.data["items"][0]["id"]
    completed=await tool.execute(context,{"operation":"update","id":todo_id,"done":True})
    assert completed.data["items"][0]["done"] is True
    listed=await tool.execute(context,{"operation":"list"})
    assert listed.data["items"]==completed.data["items"]

def test_policy_matrix_and_hard_deny(tmp_path):
    read_only=PermissionManager("read_only",tmp_path)
    assert read_only.evaluate("file_read",{"path":"a.txt"}).outcome=="allow"
    assert read_only.evaluate("file_write",{"path":"a.txt"}).outcome=="approval_required"
    assert read_only.evaluate("bash",{"command":"rm -rf /"},approved=True).outcome=="deny"
    assert read_only.evaluate("file_read",{"path":"../outside"}).risk==RiskLevel.L5
    workspace=PermissionManager("workspace",tmp_path)
    assert workspace.evaluate("file_write",{"path":"a.txt"}).outcome=="allow"
    assert workspace.evaluate("bash",{"command":"git status"}).outcome=="allow"
    assert workspace.evaluate("bash",{"command":"git diff --output=/tmp/leak"}).outcome=="deny"
    full_access=PermissionManager("full_access",tmp_path)
    assert full_access.evaluate("web_search",{"query":"test"}).outcome=="allow"
    assert read_only.evaluate("fixture__echo",{"text":"ok"}).outcome=="deny"
    assert read_only.evaluate("fixture__echo",{"text":"ok"},risk_override=1).outcome=="allow"

    configured=PermissionManager("full_access",tmp_path,blocked_patterns=["dd if="])
    assert configured.evaluate(
        "bash",{"command":"dd if=input.bin of=output.bin"},approved=True,
    ).outcome=="deny"

def test_allowlist_narrows_tools_commands_and_workspace_paths(tmp_path):
    docs=tmp_path/"docs";docs.mkdir()
    allowlist=Whitelist(
        tools={"file_read","bash"},
        command_prefixes={"git status"},
        allowed_paths={str(docs)},
    )
    policy=PermissionManager("workspace",tmp_path,allowlist)

    assert policy.evaluate("file_read",{"path":"docs/note.txt"}).outcome=="allow"
    assert policy.evaluate("file_read",{"path":"private.txt"}).outcome=="deny"
    assert policy.evaluate("file_write",{"path":"docs/note.txt"}).outcome=="deny"
    assert policy.evaluate("bash",{"command":"git status","workdir":"docs"}).outcome=="allow"
    assert policy.evaluate("bash",{"command":"pwd"}).outcome=="deny"


@pytest.mark.asyncio
async def test_core_loads_allowlist_configuration(tmp_path):
    from agent.config_manager import ConfigManager
    from agent.core import AgentCore
    from agent.event_bus import EventBus
    from agent.observability import Observability
    from agent.repository import SQLiteRepository

    config=ConfigManager()
    config.set("workspace.root",str(tmp_path))
    config.set("permissions.allowlist",{
        "tools":["file_read"],"command_prefixes":[],"paths":["docs"],
    })
    configured=AgentCore(config,EventBus(),Observability(),repository=SQLiteRepository(":memory:"))
    try:
        assert configured._policy.evaluate("file_read",{"path":"docs/a.txt"}).outcome=="allow"
        assert configured._policy.evaluate("grep",{"pattern":"a"}).outcome=="deny"
    finally:
        await configured.shutdown()

def test_legacy_permission_modes_migrate_conservatively(tmp_path):
    assert PermissionManager("plan",tmp_path).mode=="read_only"
    assert PermissionManager("manual",tmp_path).mode=="read_only"
    assert PermissionManager("accept_edits",tmp_path).mode=="workspace"
    assert PermissionManager("auto",tmp_path).mode=="full_access"


def test_filesystem_root_cannot_be_used_as_workspace():
    with pytest.raises(ValueError,match="filesystem root"):
        PermissionManager("workspace","/")

@pytest.mark.asyncio
async def test_workspace_conversations_are_isolated(core):
    await core.repository.ensure_workspace("team-a","A","team")
    item=await core.create_conversation("team-a","shared")
    assert [x["id"] for x in await core.list_conversations("team-a")]==[item["id"]]
    assert await core.list_conversations("personal")==[]

@pytest.mark.asyncio
async def test_workspace_membership_is_default_deny(core):
    assert await core.repository.check_workspace_access("personal", "local-user") == "owner"
    assert await core.repository.check_workspace_access("personal", "unknown-user") is None

@pytest.mark.asyncio
async def test_assistant_name_is_persisted_per_user(core):
    assert await core.get_user_preferences("personal", "local-user") == {"assistant_name": "助手"}
    saved=await core.update_user_preferences("personal", "local-user", "  小七  Agent  ")
    assert saved == {"assistant_name": "小七 Agent"}
    assert await core.get_user_preferences("personal", "local-user") == saved
    assert await core.get_user_preferences("personal", "another-user") == {"assistant_name": "助手"}

@pytest.mark.asyncio
async def test_assistant_name_validation(core):
    with pytest.raises(ValueError, match="required"):
        await core.update_user_preferences("personal", "local-user", "   ")
    with pytest.raises(ValueError, match="32"):
        await core.update_user_preferences("personal", "local-user", "x"*33)

from __future__ import annotations
import pytest
from agent.config_manager import ConfigManager
from agent.core import AgentCore
from agent.event_bus import EventBus
from agent.models.chat_provider import ChatResponse,ChatStreamChunk,IChatProvider
from agent.observability import Observability
from agent.repository import SQLiteRepository

class FakeProvider(IChatProvider):
    @property
    def model_name(self)->str:return "fake"
    async def chat(self,messages,**kwargs):return ChatResponse(f"reply:{messages[-1].content}")
    async def stream(self,messages,**kwargs):
        yield ChatStreamChunk(content=f"reply:{messages[-1].content}")

@pytest.fixture
async def core(tmp_path):
    config=ConfigManager();config.set("workspace.root",str(tmp_path));config.set("permissions.default_mode","read_only")
    instance=AgentCore(config,EventBus(),Observability(),FakeProvider(),SQLiteRepository(":memory:"));await instance.initialize()
    yield instance
    await instance.shutdown()

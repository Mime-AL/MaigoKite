from __future__ import annotations

import pytest

from agent.config_manager import ConfigManager
from agent.models.chat_adapter import ChatAdapter
from agent.models.chat_provider import ChatMessage, ChatResponse, IChatProvider
from agent.models.runtime import ChatModelRuntime, ChatModelSettings
from agent.repository import SQLiteRepository
from langchain_core.messages import AIMessage


class RecordingProvider(IChatProvider):
    def __init__(self, **kwargs):
        self.options = kwargs

    @property
    def model_name(self) -> str:
        return str(self.options["model"])

    async def chat(self, messages, **kwargs):
        return ChatResponse(f"reply:{messages[-1].content}")

    async def stream(self, messages, **kwargs):
        yield "unused"


@pytest.mark.asyncio
async def test_workspace_model_settings_are_persisted_and_use_scoped_credential():
    repository = SQLiteRepository(":memory:")
    await repository.open()
    runtime = ChatModelRuntime(ConfigManager(), repository, RecordingProvider)
    settings = ChatModelSettings(
        provider="openai",
        model="gpt-test",
        base_url="https://models.example.test/v1",
        temperature=0.2,
        max_tokens=512,
        timeout_seconds=15,
    )

    saved = await runtime.update_settings("personal", settings)
    await runtime.set_credential("personal", "anthropic", "wrong-provider-key")
    await runtime.set_credential("personal", "openai", "correct-provider-key")
    provider = await runtime.get_provider("personal")

    assert isinstance(provider, RecordingProvider)
    assert provider.options == {
        "provider": "openai",
        "model": "gpt-test",
        "api_key": "correct-provider-key",
        "base_url": "https://models.example.test/v1",
        "temperature": 0.2,
        "max_tokens": 512,
        "timeout": 15,
    }
    assert await runtime.get_settings("personal") == saved
    await repository.close()


@pytest.mark.asyncio
async def test_multiple_model_profiles_have_one_default_and_isolated_credentials():
    repository = SQLiteRepository(":memory:")
    await repository.open()
    runtime = ChatModelRuntime(ConfigManager(), repository, RecordingProvider)
    first = await runtime.upsert_settings("personal", ChatModelSettings(
        id="model_first", name="First", provider="openai", model="gpt-first", is_default=True,
    ))
    second = await runtime.upsert_settings("personal", ChatModelSettings(
        id="model_second", name="Second", provider="openai", model="gpt-second",
    ))
    await runtime.set_credential("personal", "openai", "first-key", first.id)
    await runtime.set_credential("personal", "openai", "second-key", second.id)

    default_provider = await runtime.get_provider("personal")
    second_provider = await runtime.get_provider("personal", second.id)
    profiles, default_id = await runtime.list_settings("personal")

    assert default_id == first.id
    assert [item.id for item in profiles] == [first.id, second.id]
    assert default_provider.options["api_key"] == "first-key"
    assert second_provider.options["api_key"] == "second-key"

    await runtime.set_default("personal", second.id)
    assert (await runtime.get_settings("personal")).id == second.id
    await runtime.delete_settings("personal", second.id)
    assert (await runtime.get_settings("personal")).id == first.id
    await repository.close()


@pytest.mark.asyncio
async def test_changing_a_profile_endpoint_drops_its_in_memory_credential():
    repository = SQLiteRepository(":memory:")
    await repository.open()
    runtime = ChatModelRuntime(ConfigManager(), repository, RecordingProvider)
    profile = await runtime.upsert_settings("personal", ChatModelSettings(
        id="model_private", name="Private", provider="openai_compatible", model="one",
        base_url="https://old.example/v1", is_default=True,
    ))
    await runtime.set_credential("personal", profile.provider, "old-secret", profile.id)
    await runtime.upsert_settings("personal", ChatModelSettings(
        id=profile.id, name="Private", provider="openai_compatible", model="two",
        base_url="https://new.example/v1", is_default=True,
    ))

    provider = await runtime.get_provider("personal", profile.id)
    assert provider.options["api_key"] == ""
    await repository.close()


@pytest.mark.asyncio
async def test_local_compatible_endpoint_never_receives_cloud_environment_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "cloud-secret")
    repository = SQLiteRepository(":memory:")
    await repository.open()
    runtime = ChatModelRuntime(ConfigManager(), repository, RecordingProvider)
    settings = ChatModelSettings(
        provider="openai_compatible",
        model="local-model",
        base_url="http://127.0.0.1:1234/v1",
    )

    await runtime.update_settings("personal", settings)
    provider = await runtime.get_provider("personal")

    assert isinstance(provider, RecordingProvider)
    assert provider.options["api_key"] == ""
    adapter = ChatAdapter(
        provider="openai_compatible",
        model="local-model",
        base_url="http://127.0.0.1:1234/v1",
    )
    assert adapter._llm.openai_api_key.get_secret_value() == "local-no-key"
    await repository.close()


@pytest.mark.asyncio
async def test_compatible_endpoint_accepts_only_its_scoped_optional_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "cloud-secret")
    repository = SQLiteRepository(":memory:")
    await repository.open()
    runtime = ChatModelRuntime(ConfigManager(), repository, RecordingProvider)
    settings = ChatModelSettings(
        provider="openai_compatible",
        model="secured-local-model",
        base_url="http://127.0.0.1:8000/v1",
    )

    await runtime.update_settings("personal", settings)
    await runtime.set_credential("personal", "openai_compatible", "local-endpoint-key")
    provider = await runtime.get_provider("personal")

    assert isinstance(provider, RecordingProvider)
    assert provider.options["api_key"] == "local-endpoint-key"
    await repository.close()


def test_model_settings_normalize_alias_and_reject_embedded_credentials():
    assert ChatModelSettings.from_dict({"provider": "lm_studio", "model": "local"}).provider == "openai_compatible"
    with pytest.raises(ValueError, match="must not contain credentials"):
        ChatModelSettings(
            provider="openai_compatible",
            model="local",
            base_url="http://user:password@127.0.0.1:1234/v1",
        ).validate()
    with pytest.raises(ValueError, match="requires base_url"):
        ChatModelSettings(provider="openai_compatible", model="local").validate()


@pytest.mark.asyncio
async def test_lm_studio_default_port_adds_openai_v1_prefix():
    settings = ChatModelSettings.from_dict({
        "provider": "openai_compatible",
        "model": "Gemma 4 E4B",
        "base_url": "http://127.0.0.1:1234",
    })
    assert settings.base_url == "http://127.0.0.1:1234/v1"

    repository = SQLiteRepository(":memory:")
    await repository.open()
    runtime = ChatModelRuntime(ConfigManager(), repository, RecordingProvider)
    try:
        saved = await runtime.upsert_settings("personal", ChatModelSettings(
            name="LM Studio",
            provider="openai_compatible",
            model="Gemma 4 E4B",
            base_url="http://127.0.0.1:1234",
        ))
        provider = await runtime.get_provider("personal", saved.id)
        assert saved.base_url == "http://127.0.0.1:1234/v1"
        assert provider.options["base_url"] == "http://127.0.0.1:1234/v1"
    finally:
        await runtime.close()
        await repository.close()

    adapter = ChatAdapter(
        provider="openai_compatible",
        model=settings.model,
        base_url="http://127.0.0.1:1234",
    )
    try:
        endpoint = adapter._llm.root_async_client._prepare_url("/chat/completions")
        assert str(endpoint) == "http://127.0.0.1:1234/v1/chat/completions"
    finally:
        await adapter.aclose()


def test_chat_adapter_ignores_non_numeric_usage_details():
    response = ChatAdapter._from_langchain(
        AIMessage(
            content="ok",
            response_metadata={
                "token_usage": {
                    "prompt_tokens": 2,
                    "completion_tokens": 1,
                    "prompt_tokens_details": None,
                }
            },
        )
    )
    assert response.usage == {"prompt_tokens": 2, "completion_tokens": 1}


def test_chat_adapter_normalizes_streamed_tool_call_fragments():
    chunk = type("Chunk", (), {
        "content": "",
        "tool_call_chunks": [{"index": 0, "id": "call-1", "name": "file_read", "args": '{"path":"a.txt"}'}],
        "response_metadata": {"finish_reason": "tool_calls"},
        "usage_metadata": {"input_tokens": 5},
    })()
    result = ChatAdapter._stream_chunk(chunk)
    assert result.tool_call_chunks[0].name == "file_read"
    assert result.tool_call_chunks[0].arguments == '{"path":"a.txt"}'
    assert result.usage == {"input_tokens": 5}


def test_chat_adapter_keeps_provider_reasoning_separate_from_answer_text():
    chunk = type("Chunk", (), {
        "content": "final answer",
        "additional_kwargs": {"reasoning_content": "public reasoning summary"},
        "tool_call_chunks": [],
        "response_metadata": {},
        "usage_metadata": {},
    })()

    result = ChatAdapter._stream_chunk(chunk)

    assert result.content == "final answer"
    assert result.reasoning == "public reasoning summary"


@pytest.mark.asyncio
async def test_chat_adapter_uses_configured_generation_parameters():
    class FakeLLM:
        options = None

        async def ainvoke(self, messages, **kwargs):
            self.options = kwargs
            return AIMessage(content="ok")

    adapter = object.__new__(ChatAdapter)
    adapter.temperature = 0.25
    adapter.max_tokens = 321
    adapter._llm = FakeLLM()
    adapter._fallback_llm = None

    await adapter.chat([ChatMessage("user", "hello")])

    assert adapter._llm.options == {"temperature": 0.25, "max_tokens": 321}

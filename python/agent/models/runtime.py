"""Workspace-scoped chat model settings and provider lifecycle."""

from __future__ import annotations

import os
import re
import uuid
from dataclasses import asdict, dataclass, replace
from typing import Any, Callable
from urllib.parse import urlparse

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage

from agent.config_manager import ConfigManager
from agent.models.native_model import build_chat_model, close_chat_models, normalize_openai_compatible_base_url
from agent.models.chat_provider import ChatMessage, IChatProvider
from agent.repository import SQLiteRepository


_PROVIDER_ALIASES = {
    "lm_studio": "openai_compatible",
    "lm-studio": "openai_compatible",
    "vllm": "openai_compatible",
    "openai-compatible": "openai_compatible",
    "local": "openai_compatible",
}
_SUPPORTED_PROVIDERS = {"openai", "anthropic", "openai_compatible", "ollama"}


@dataclass(frozen=True, slots=True)
class ChatModelSettings:
    id: str = ""
    name: str = ""
    provider: str = ""
    model: str = ""
    base_url: str = ""
    temperature: float = 0.7
    max_tokens: int = 4096
    timeout_seconds: int = 60
    is_default: bool = False

    @classmethod
    def from_dict(cls, value: dict[str, Any] | None) -> "ChatModelSettings":
        value = value or {}
        provider = str(value.get("provider", "")).strip().lower()
        provider = _PROVIDER_ALIASES.get(provider, provider)
        return cls(
            id=str(value.get("id", "")).strip(),
            name=str(value.get("name", "")).strip(),
            provider=provider,
            model=str(value.get("model", value.get("default", ""))).strip(),
            base_url=normalize_openai_compatible_base_url(
                provider, value.get("base_url", value.get("endpoint", ""))
            ),
            temperature=float(value.get("temperature", 0.7)),
            max_tokens=int(value.get("max_tokens", 4096)),
            timeout_seconds=int(value.get("timeout_seconds", value.get("timeout", 60))),
            is_default=bool(value.get("is_default", False)),
        )

    def validate(self) -> None:
        if self.provider not in _SUPPORTED_PROVIDERS:
            choices = ", ".join(sorted(_SUPPORTED_PROVIDERS))
            raise ValueError(f"unsupported chat provider '{self.provider}'; choose one of: {choices}")
        if not self.model:
            raise ValueError("chat model name is required")
        if self.id and not re.fullmatch(r"model_[A-Za-z0-9_-]{1,80}", self.id):
            raise ValueError("model profile id is invalid")
        if len(self.name) > 80:
            raise ValueError("model profile name must not exceed 80 characters")
        if self.provider == "openai_compatible" and not self.base_url:
            raise ValueError("openai_compatible provider requires base_url")
        if not 0 <= self.temperature <= 2:
            raise ValueError("temperature must be between 0 and 2")
        if not 1 <= self.max_tokens <= 65536:
            raise ValueError("max_tokens must be between 1 and 65536")
        if not 1 <= self.timeout_seconds <= 600:
            raise ValueError("timeout_seconds must be between 1 and 600")
        if self.base_url:
            parsed = urlparse(self.base_url)
            if parsed.scheme not in {"http", "https"} or not parsed.hostname:
                raise ValueError("base_url must be an absolute HTTP(S) URL")
            if parsed.username or parsed.password:
                raise ValueError("base_url must not contain credentials")
            if parsed.query or parsed.fragment:
                raise ValueError("base_url must not contain a query or fragment")

    @property
    def requires_api_key(self) -> bool:
        return self.provider in {"openai", "anthropic"}

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


ProviderFactory = Callable[..., IChatProvider]


class ChatModelRuntime:
    """Loads settings from the domain repository and keeps secrets in memory."""

    _SETTING_KEY = "models.chat"
    _CATALOG_KEY = "models.chat.catalog"

    def __init__(
        self,
        config: ConfigManager,
        repository: SQLiteRepository,
        provider_factory: ProviderFactory | None = None,
    ) -> None:
        self._config = config
        self._repository = repository
        self._provider_factory = provider_factory
        self._credentials: dict[tuple[str, str], str] = {}
        self._providers: dict[tuple[str, str], tuple[ChatModelSettings, IChatProvider]] = {}
        self._retired_providers: list[IChatProvider] = []
        self._native_models: dict[tuple[str, str], tuple[ChatModelSettings, BaseChatModel]] = {}
        self._retired_models: list[BaseChatModel] = []

    def _defaults(self) -> ChatModelSettings:
        raw = self._config.get("models.chat", {})
        if not isinstance(raw, dict):
            raw = {}
        model = str(raw.get("default", "")).strip()
        provider = str(raw.get("provider", "")).strip()
        if ":" in model:
            prefix, candidate = model.split(":", 1)
            if prefix.lower() in _SUPPORTED_PROVIDERS | set(_PROVIDER_ALIASES):
                provider, model = prefix, candidate
        if not provider:
            provider = "ollama"
        if provider.lower() == "ollama" and not raw.get("base_url") and not raw.get("endpoint"):
            raw = {**raw, "base_url": "http://127.0.0.1:11434"}
        return ChatModelSettings.from_dict({
            **raw, "id": "model_default", "name": model or "默认模型",
            "provider": provider, "model": model, "is_default": True,
        })

    async def list_settings(self, workspace_id: str) -> tuple[list[ChatModelSettings], str]:
        stored = await self._repository.get_workspace_setting(workspace_id, self._CATALOG_KEY)
        if isinstance(stored, dict) and isinstance(stored.get("profiles"), list):
            profiles = [ChatModelSettings.from_dict(item) for item in stored["profiles"] if isinstance(item, dict)]
            default_id = str(stored.get("default_model_id", ""))
            if default_id not in {item.id for item in profiles}:
                default_id = profiles[0].id if profiles else ""
            return [replace(item, is_default=item.id == default_id) for item in profiles], default_id

        legacy = await self._repository.get_workspace_setting(workspace_id, self._SETTING_KEY)
        settings = ChatModelSettings.from_dict(legacy) if isinstance(legacy, dict) else self._defaults()
        if not settings.model:
            return [], ""
        profile = replace(
            settings,
            id=settings.id or "model_default",
            name=settings.name or settings.model,
            is_default=True,
        )
        return [profile], profile.id

    async def _save_catalog(
        self, workspace_id: str, profiles: list[ChatModelSettings], default_id: str
    ) -> None:
        await self._repository.save_workspace_setting(workspace_id, self._CATALOG_KEY, {
            "default_model_id": default_id,
            "profiles": [replace(item, is_default=item.id == default_id).to_dict() for item in profiles],
        })

    async def get_profile(self, workspace_id: str, model_id: str = "") -> ChatModelSettings:
        profiles, default_id = await self.list_settings(workspace_id)
        selected_id = model_id or default_id
        for item in profiles:
            if item.id == selected_id:
                return item
        if model_id:
            raise KeyError(model_id)
        return self._defaults()

    async def get_settings(self, workspace_id: str) -> ChatModelSettings:
        return await self.get_profile(workspace_id)

    async def update_settings(self, workspace_id: str, settings: ChatModelSettings) -> ChatModelSettings:
        profiles, default_id = await self.list_settings(workspace_id)
        profile_id = settings.id or default_id or "model_default"
        saved = await self.upsert_settings(workspace_id, replace(settings, id=profile_id, is_default=True))
        await self._repository.save_workspace_setting(workspace_id, self._SETTING_KEY, saved.to_dict())
        return saved

    async def upsert_settings(self, workspace_id: str, settings: ChatModelSettings) -> ChatModelSettings:
        profile_id = settings.id or f"model_{uuid.uuid4().hex}"
        normalized = replace(
            settings,
            id=profile_id,
            name=settings.name.strip() or settings.model,
            base_url=normalize_openai_compatible_base_url(
                settings.provider, settings.base_url
            ),
        )
        normalized.validate()
        profiles, default_id = await self.list_settings(workspace_id)
        previous = next((item for item in profiles if item.id == profile_id), None)
        if previous is not None and (
            previous.provider != normalized.provider or previous.base_url != normalized.base_url
        ):
            self._credentials.pop((workspace_id, profile_id), None)
        if not any(item.id == profile_id for item in profiles) and len(profiles) >= 32:
            raise ValueError("a workspace may configure at most 32 chat models")
        profiles = [normalized if item.id == profile_id else item for item in profiles]
        if not any(item.id == profile_id for item in profiles):
            profiles.append(normalized)
        if not default_id or normalized.is_default:
            default_id = profile_id
        await self._save_catalog(workspace_id, profiles, default_id)
        self._invalidate_provider(workspace_id, profile_id)
        return replace(normalized, is_default=profile_id == default_id)

    async def delete_settings(self, workspace_id: str, model_id: str) -> None:
        profiles, default_id = await self.list_settings(workspace_id)
        if not any(item.id == model_id for item in profiles):
            raise KeyError(model_id)
        remaining = [item for item in profiles if item.id != model_id]
        if default_id == model_id:
            default_id = remaining[0].id if remaining else ""
        await self._save_catalog(workspace_id, remaining, default_id)
        await self._repository.replace_conversation_model(workspace_id, model_id, default_id)
        self._credentials.pop((workspace_id, model_id), None)
        self._invalidate_provider(workspace_id, model_id)

    async def set_default(self, workspace_id: str, model_id: str) -> tuple[list[ChatModelSettings], str]:
        profiles, _ = await self.list_settings(workspace_id)
        if not any(item.id == model_id for item in profiles):
            raise KeyError(model_id)
        await self._save_catalog(workspace_id, profiles, model_id)
        return [replace(item, is_default=item.id == model_id) for item in profiles], model_id

    async def set_credential(
        self, workspace_id: str, provider: str, api_key: str, model_id: str = ""
    ) -> None:
        provider = _PROVIDER_ALIASES.get(provider.lower(), provider.lower())
        credential_key = (workspace_id, model_id or provider)
        if self._credentials.get(credential_key, "") == api_key:
            return
        if api_key:
            self._credentials[credential_key] = api_key
        else:
            self._credentials.pop(credential_key, None)
        self._invalidate_provider(workspace_id, model_id)

    def _invalidate_provider(self, workspace_id: str, model_id: str = "") -> None:
        keys = [key for key in self._providers if key[0] == workspace_id and (not model_id or key[1] == model_id)]
        for key in keys:
            cached = self._providers.pop(key)
            self._retired_providers.append(cached[1])
        for key in list(self._native_models):
            if key[0] == workspace_id and (not model_id or key[1] == model_id):
                self._retired_models.append(self._native_models.pop(key)[1])

    async def close(self) -> None:
        providers = [item[1] for item in self._providers.values()] + self._retired_providers
        self._providers.clear()
        self._retired_providers = []
        models = [item[1] for item in self._native_models.values()] + self._retired_models
        self._native_models.clear()
        self._retired_models = []
        for provider in providers:
            close = getattr(provider, "aclose", None)
            if close is not None:
                await close()
        await close_chat_models(models)
        self._credentials.clear()

    def _model_options(self, settings: ChatModelSettings, api_key: str = "") -> dict[str, Any]:
        settings.validate()
        base_url = normalize_openai_compatible_base_url(
            settings.provider, settings.base_url
        )
        if settings.provider == "openai":
            key = api_key or os.getenv("OPENAI_API_KEY", "")
        elif settings.provider == "anthropic":
            key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
        elif settings.provider == "openai_compatible":
            # Compatible endpoints commonly need no key, but vLLM and remote
            # gateways may enable bearer authentication.  Only an explicitly
            # workspace-scoped key is allowed here; never borrow a cloud key.
            key = api_key
        else:
            key = ""
        if settings.requires_api_key and not key:
            raise RuntimeError(f"provider '{settings.provider}' requires an API key")
        return dict(
            provider=settings.provider,
            model=settings.model,
            api_key=key,
            base_url=base_url or None,
            temperature=settings.temperature,
            max_tokens=settings.max_tokens,
            timeout=settings.timeout_seconds,
        )

    def _build_provider(self, settings: ChatModelSettings, api_key: str = "") -> IChatProvider:
        # Only the legacy entry imports its protocol wrapper.
        factory = self._provider_factory
        if factory is None:
            from agent.models.chat_adapter import ChatAdapter
            factory = ChatAdapter
        return factory(**self._model_options(settings, api_key))

    def _profile_key(self, workspace_id: str, settings: ChatModelSettings) -> str:
        key = self._credentials.get((workspace_id, settings.id), "")
        if not key and settings.id in {"", "model_default"}:
            key = self._credentials.get((workspace_id, settings.provider), "")
        return key

    async def get_provider(self, workspace_id: str, model_id: str = "") -> IChatProvider:
        settings = await self.get_profile(workspace_id, model_id)
        cache_key = (workspace_id, settings.id or settings.provider)
        cached = self._providers.get(cache_key)
        if cached and cached[0] == settings:
            return cached[1]
        provider = self._build_provider(settings, self._profile_key(workspace_id, settings))
        if cached:
            self._retired_providers.append(cached[1])
        self._providers[cache_key] = (settings, provider)
        return provider

    async def get_langchain_model(
        self, workspace_id: str, model_id: str = ""
    ) -> tuple[str, BaseChatModel]:
        """Return the Core-owned native model used by the LangGraph runtime."""
        settings = await self.get_profile(workspace_id, model_id)
        cache_key = (workspace_id, settings.id)
        cached = self._native_models.get(cache_key)
        if cached and cached[0] == settings:
            model = cached[1]
        else:
            model = build_chat_model(**self._model_options(settings, self._profile_key(workspace_id, settings)))
            if cached:
                self._retired_models.append(cached[1])
            self._native_models[cache_key] = (settings, model)
        # Credential replacement retires the old provider even when settings are
        # identical. Do not reuse a compiled graph holding that obsolete client.
        return f"{workspace_id}:{settings.id}:{hash(settings)}:{id(model)}", model

    async def validate_connection(
        self,
        settings: ChatModelSettings,
        api_key: str = "",
    ) -> str:
        if self._provider_factory is None:
            options = self._model_options(replace(settings, temperature=0, max_tokens=min(settings.max_tokens, 8)), api_key)
            model = build_chat_model(**options)
            try:
                native_response = await model.ainvoke([HumanMessage(content="Reply with OK.")])
                return str(native_response.text)
            finally:
                await close_chat_models([model])
        # Preserve explicitly injected legacy providers during the migration.
        provider = self._build_provider(settings, api_key)
        try:
            response = await provider.chat(
                [ChatMessage("user", "Reply with OK.")],
                temperature=0,
                max_tokens=min(settings.max_tokens, 8),
            )
            return response.content
        finally:
            close = getattr(provider, "aclose", None)
            if close is not None:
                await close()

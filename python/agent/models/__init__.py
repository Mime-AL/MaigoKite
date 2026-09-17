"""Models package — LangChain adapters for LLM / Embedding / Image providers.

This layer wraps LangChain's provider implementations so the rest of the
Agent Core can talk to a single, stable interface while benefiting from
LangChain's model routing, streaming, and tool-binding features.

Self-built modules (TaskManager, ExecutionEngine, ToolRegistry, etc.)
remain untouched — they consume these adapters through the same
IChatProvider / IEmbeddingProvider / IImageProvider contracts.
"""

__all__ = ["ChatAdapter", "EmbeddingAdapter", "ImageAdapter"]


def __getattr__(name: str):
    """Load provider integrations only when requested."""
    if name == "ChatAdapter":
        from agent.models.chat_adapter import ChatAdapter
        return ChatAdapter
    if name == "EmbeddingAdapter":
        from agent.models.embedding_adapter import EmbeddingAdapter
        return EmbeddingAdapter
    if name == "ImageAdapter":
        from agent.models.image_adapter import ImageAdapter
        return ImageAdapter
    raise AttributeError(name)

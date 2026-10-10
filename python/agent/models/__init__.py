"""Native chat model construction and optional embedding/image integrations."""

__all__ = ["EmbeddingAdapter", "ImageAdapter"]


def __getattr__(name: str):
    """Load provider integrations only when requested."""
    if name == "EmbeddingAdapter":
        from agent.models.embedding_adapter import EmbeddingAdapter
        return EmbeddingAdapter
    if name == "ImageAdapter":
        from agent.models.image_adapter import ImageAdapter
        return ImageAdapter
    raise AttributeError(name)

"""Compatibility surface for the completed LangGraph migration spike.

The implementation promoted to production lives in :mod:`agent.runtime`;
these names keep the original acceptance tests and opt-in provider probes.
"""

from agent.runtime_spike.adapter import (
    NanamiEvent,
    NanamiRuntimeAdapter,
    ProductToolSpec,
    RunHandle,
    SpikeRunRequest,
)
from agent.runtime_spike.model_factory import build_chat_model

__all__ = [
    "NanamiEvent",
    "NanamiRuntimeAdapter",
    "ProductToolSpec",
    "RunHandle",
    "SpikeRunRequest",
    "build_chat_model",
]

"""LLM provider abstraction (ports & adapters).

The rest of the system depends only on the ``LLMClient`` protocol, never on a
concrete SDK. This lets us swap OpenAI ↔ Claude ↔ Bedrock, and run fully offline
with ``FakeLLM`` for tests and local dev.
"""

from .base import LLMClient, LLMError, Usage
from .fake_client import FakeLLM
from .router import build_llm

__all__ = ["LLMClient", "LLMError", "Usage", "FakeLLM", "build_llm"]

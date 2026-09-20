from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional, List, Dict, Any

class BaseLLMClient(ABC):
    """Abstract Base Class for LLM providers."""

    def __init__(self, model_name: str):
        self.model_name = model_name

    @property
    @abstractmethod
    def provider(self) -> str:
        """Provider name (e.g. 'ollama', 'openai', 'gemini')."""
        pass

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = 4096,
    ) -> str:
        """Generate a complete text response asynchronously."""
        pass

    @abstractmethod
    async def generate_stream(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = 4096,
    ) -> AsyncIterator[str]:
        """Stream response tokens asynchronously."""
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        """Check if provider is online and reachable."""
        pass

import json
from typing import AsyncIterator, Optional, List, Dict, Any
import httpx
from agent.llm.base import BaseLLMClient
from agent.config import settings

class OllamaClient(BaseLLMClient):
    """Client for local Ollama instances."""

    def __init__(self, model_name: str = "auto", base_url: Optional[str] = None):
        super().__init__(model_name)
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self._resolved_model: Optional[str] = None if model_name == "auto" else model_name

    @property
    def provider(self) -> str:
        return "ollama"

    async def _resolve_model(self) -> str:
        """Resolve 'auto' model to the best available local model."""
        if self._resolved_model:
            return self._resolved_model

        models = await self.list_models()
        if not models:
            raise RuntimeError(
                f"No local Ollama models found at {self.base_url}. "
                "Please run 'ollama pull llama3.1' or 'ollama pull qwen2.5:7b'."
            )

        # Preference priority for fast & high quality research
        preferred = [
            "llama3.2", "llama3.1", "qwen2.5:7b", "hermes3", 
            "deepseek-r1", "qwen3.6", "gemma4:12b", "gemma2:2b", 
            "llama3", "phi3"
        ]
        
        for pref in preferred:
            for m in models:
                if pref in m.lower():
                    self._resolved_model = m
                    return m

        # Fallback to the first available model
        self._resolved_model = models[0]
        return self._resolved_model

    async def is_available(self) -> bool:
        """Check if Ollama service is reachable."""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(f"{self.base_url}/api/tags")
                return res.status_code == 200
        except Exception:
            return False

    @staticmethod
    async def list_models(base_url: Optional[str] = None) -> List[str]:
        """List all locally installed Ollama models."""
        url = (base_url or settings.ollama_base_url).rstrip("/")
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(f"{url}/api/tags")
                if res.status_code == 200:
                    data = res.json()
                    return [m["name"] for m in data.get("models", [])]
        except Exception:
            pass
        return []

    async def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = 4096,
    ) -> str:
        model = await self._resolve_model()
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens or 4096,
            }
        }

        async with httpx.AsyncClient(timeout=180.0) as client:
            res = await client.post(f"{self.base_url}/api/chat", json=payload)
            res.raise_for_status()
            data = res.json()
            return data.get("message", {}).get("content", "").strip()

    async def generate_stream(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = 4096,
    ) -> AsyncIterator[str]:
        model = await self._resolve_model()
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens or 4096,
            }
        }

        async with httpx.AsyncClient(timeout=180.0) as client:
            async with client.stream("POST", f"{self.base_url}/api/chat", json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line)
                        content = chunk.get("message", {}).get("content", "")
                        if content:
                            yield content
                    except Exception:
                        continue

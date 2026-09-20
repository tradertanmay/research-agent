import json
from typing import AsyncIterator, Optional, Dict, Any, List
import httpx
from agent.llm.base import BaseLLMClient

class OpenAICompatClient(BaseLLMClient):
    """Client for OpenAI-compatible APIs (OpenAI, Gemini, Groq, OpenRouter)."""

    def __init__(
        self,
        model_name: str,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        provider_name: str = "openai",
    ):
        super().__init__(model_name)
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self._provider = provider_name

    @property
    def provider(self) -> str:
        return self._provider

    async def is_available(self) -> bool:
        return bool(self.api_key and len(self.api_key) > 5)

    async def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = 4096,
    ) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens or 4096,
            "stream": False,
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            res = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            res.raise_for_status()
            data = res.json()
            return data["choices"][0]["message"]["content"].strip()

    async def generate_stream(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = 4096,
    ) -> AsyncIterator[str]:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens or 4096,
            "stream": True,
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    data_str = line[6:].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        delta = chunk["choices"][0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content
                    except Exception:
                        continue

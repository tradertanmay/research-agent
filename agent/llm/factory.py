import os
from typing import Dict, Any, List, Optional
from agent.config import settings
from agent.llm.base import BaseLLMClient
from agent.llm.ollama_client import OllamaClient
from agent.llm.openai_compat import OpenAICompatClient

async def list_available_models() -> List[Dict[str, Any]]:
    """List all available models (local Ollama + configured cloud providers)."""
    results = []

    # 1. Local Ollama Models
    try:
        ollama_models = await OllamaClient.list_models()
        for m in ollama_models:
            results.append({
                "id": f"ollama:{m}",
                "name": f"Ollama: {m}",
                "provider": "ollama",
                "local": True,
                "badge": "Free / Local",
            })
    except Exception:
        pass

    # 2. Cloud Providers
    if settings.gemini_api_key or os.getenv("GEMINI_API_KEY"):
        results.extend([
            {"id": "gemini:gemini-2.5-flash", "name": "Google Gemini 2.5 Flash", "provider": "gemini", "local": False, "badge": "Cloud"},
            {"id": "gemini:gemini-2.5-pro", "name": "Google Gemini 2.5 Pro", "provider": "gemini", "local": False, "badge": "Cloud"},
        ])

    if settings.openai_api_key or os.getenv("OPENAI_API_KEY"):
        results.extend([
            {"id": "openai:gpt-4o", "name": "OpenAI GPT-4o", "provider": "openai", "local": False, "badge": "Cloud"},
            {"id": "openai:gpt-4o-mini", "name": "OpenAI GPT-4o Mini", "provider": "openai", "local": False, "badge": "Cloud"},
        ])

    if settings.groq_api_key or os.getenv("GROQ_API_KEY"):
        results.extend([
            {"id": "groq:llama-3.3-70b-versatile", "name": "Groq: Llama 3.3 70B", "provider": "groq", "local": False, "badge": "Ultra-Fast"},
        ])

    if settings.openrouter_api_key or os.getenv("OPENROUTER_API_KEY"):
        results.append(
            {"id": "openrouter:auto", "name": "OpenRouter (Auto)", "provider": "openrouter", "local": False, "badge": "Cloud"}
        )

    if settings.custom_llm_url or os.getenv("CUSTOM_LLM_URL"):
        custom_model = settings.custom_llm_model or os.getenv("CUSTOM_LLM_MODEL", "custom-model")
        results.append({
            "id": f"custom:{custom_model}",
            "name": f"Custom: {custom_model}",
            "provider": "custom",
            "local": True,
            "badge": "Custom API",
        })

    return results

def get_llm_client(model_id: Optional[str] = None) -> BaseLLMClient:
    """Factory to retrieve the appropriate LLM client."""
    target = model_id or settings.default_model or "auto"

    if target == "auto":
        # Check if Ollama is accessible
        return OllamaClient(model_name="auto")

    if target.startswith("ollama:"):
        model_name = target.replace("ollama:", "", 1)
        return OllamaClient(model_name=model_name)

    if target.startswith("gemini:"):
        model_name = target.replace("gemini:", "", 1)
        api_key = settings.gemini_api_key or os.getenv("GEMINI_API_KEY", "")
        return OpenAICompatClient(
            model_name=model_name,
            api_key=api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            provider_name="gemini",
        )

    if target.startswith("openai:"):
        model_name = target.replace("openai:", "", 1)
        api_key = settings.openai_api_key or os.getenv("OPENAI_API_KEY", "")
        return OpenAICompatClient(
            model_name=model_name,
            api_key=api_key,
            base_url="https://api.openai.com/v1",
            provider_name="openai",
        )

    if target.startswith("groq:"):
        model_name = target.replace("groq:", "", 1)
        api_key = settings.groq_api_key or os.getenv("GROQ_API_KEY", "")
        return OpenAICompatClient(
            model_name=model_name,
            api_key=api_key,
            base_url="https://api.groq.com/openai/v1",
            provider_name="groq",
        )

    if target.startswith("openrouter:"):
        model_name = target.replace("openrouter:", "", 1)
        api_key = settings.openrouter_api_key or os.getenv("OPENROUTER_API_KEY", "")
        return OpenAICompatClient(
            model_name=model_name,
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
            provider_name="openrouter",
        )

    if target.startswith("custom:"):
        model_name = target.replace("custom:", "", 1)
        api_key = settings.custom_llm_api_key or os.getenv("CUSTOM_LLM_API_KEY", "not-needed")
        base_url = settings.custom_llm_url or os.getenv("CUSTOM_LLM_URL", "http://localhost:1234/v1")
        return OpenAICompatClient(
            model_name=model_name,
            api_key=api_key,
            base_url=base_url,
            provider_name="custom",
        )

    # Default to Ollama with the provided string as model name
    return OllamaClient(model_name=target)

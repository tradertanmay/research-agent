import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings

PROJECT_ROOT = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    # Ollama settings (Local first)
    ollama_base_url: str = "http://localhost:11434"
    default_model: str = "auto"

    # Optional Cloud API keys
    openai_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    openrouter_api_key: Optional[str] = None

    # Custom / OpenAI-Compatible Endpoint (LM Studio, vLLM, LocalAI, etc.)
    custom_llm_url: Optional[str] = None
    custom_llm_model: Optional[str] = None
    custom_llm_api_key: Optional[str] = "not-needed"

    # Storage settings
    vault_dir: Path = PROJECT_ROOT / "vault"
    reports_dir: Path = PROJECT_ROOT / "vault" / "reports"

    # Server settings
    host: str = "0.0.0.0"
    port: int = 8080
    access_password: Optional[str] = None
    guest_password: Optional[str] = None

    # Search defaults
    max_search_results_per_query: int = 5
    max_crawl_pages_per_topic: int = 8
    request_timeout: float = 15.0

    class Config:
        env_file = str(PROJECT_ROOT / ".env")
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = Settings()

# Ensure vault directories exist
settings.vault_dir.mkdir(parents=True, exist_ok=True)
settings.reports_dir.mkdir(parents=True, exist_ok=True)

def save_api_keys(updates: dict) -> None:
    """Persist API keys and custom model settings to .env and update in-memory settings."""
    env_path = PROJECT_ROOT / ".env"
    lines = []
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

    existing_keys = set()
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            k, v = stripped.split("=", 1)
            k = k.strip()
            if k in updates:
                if updates[k]:
                    new_lines.append(f"{k}={updates[k]}\n")
                existing_keys.add(k)
                continue
        new_lines.append(line)

    for k, v in updates.items():
        if k not in existing_keys and v:
            new_lines.append(f"{k}={v}\n")

    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    # Update in-memory settings and os.environ
    for k, v in updates.items():
        attr_name = k.lower()
        if hasattr(settings, attr_name):
            setattr(settings, attr_name, v if v else None)
        if v:
            os.environ[k] = v
        elif k in os.environ:
            del os.environ[k]

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

    # Storage settings
    vault_dir: Path = PROJECT_ROOT / "vault"
    reports_dir: Path = PROJECT_ROOT / "vault" / "reports"

    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000
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

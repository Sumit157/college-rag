"""Centralised application configuration.

All runtime settings are read from environment variables (optionally via a
`.env` file). Model names and paths are never hard-coded outside this file.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "College RAG"
    api_prefix: str = "/api"

    # MongoDB
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_database: str = "college_rag"
    mongodb_timeout_ms: int = 5000

    # Ollama / local LLM
    ollama_base_url: str = "http://localhost:11434"
    llm_model: str = "llama3.2:3b"
    embedding_model: str = "nomic-embed-text"
    llm_temperature: float = 0.2
    ollama_timeout_s: float = 60.0

    # Frontend origins allowed to call the API
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

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
    # First Ollama call after a model was unloaded can block while the model
    # reloads (cold load), so allow generous time before giving up.
    ollama_timeout_s: float = 180.0

    # Frontend origins allowed to call the API
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Ingestion
    max_upload_size_mb: int = 20
    chunk_size_tokens: int = 600
    chunk_overlap_tokens: int = 80

    # Retrieval
    retrieval_top_k: int = 5
    # Dimensions of the configured embedding model (nomic-embed-text=768,
    # bge-m3=1024). Must match EMBEDDING_MODEL or the vector index breaks.
    embedding_dims: int = 768
    # "auto": use MongoDB $vectorSearch when available, fall back to local
    # cosine scoring. "vector": require $vectorSearch. "local": in-process only.
    vector_search_mode: str = "auto"

    # RAG / generation
    # Evidence below this relevance (cosine) is rejected as irrelevant.
    relevance_threshold: float = 0.5
    # Token budget for retrieved context handed to the LLM.
    context_max_tokens: int = 3000

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

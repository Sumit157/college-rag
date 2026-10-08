"""Ollama adapter: health and model checks.

Generation and streaming arrive in Phase 3; this module only exposes the
connectivity surface required by the foundation phase.
"""

from __future__ import annotations

import httpx

from app.core.config import get_settings


class OllamaError(Exception):
    """Raised when Ollama cannot be reached or returns an error."""


class OllamaProvider:
    """Adapter for the local Ollama runtime."""

    def __init__(
        self,
        base_url: str | None = None,
        timeout_s: float | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        settings = get_settings()
        self._base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self._timeout_s = timeout_s or settings.ollama_timeout_s
        self._transport = transport

    @property
    def base_url(self) -> str:
        return self._base_url

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(timeout=self._timeout_s, transport=self._transport)

    async def ping(self) -> bool:
        """Return True when the Ollama API answers."""
        try:
            async with self._client() as client:
                response = await client.get(f"{self._base_url}/api/tags")
                return response.status_code == 200
        except httpx.HTTPError:
            return False

    async def list_models(self) -> list[str]:
        """Return the names of locally available models."""
        try:
            async with self._client() as client:
                response = await client.get(f"{self._base_url}/api/tags")
                response.raise_for_status()
                payload = response.json()
        except httpx.HTTPError as exc:
            raise OllamaError(f"Ollama is unreachable at {self._base_url}") from exc
        return [model.get("name", "") for model in payload.get("models", [])]

    async def health(self) -> dict:
        """Structured health report used by the health endpoint."""
        reachable = await self.ping()
        if not reachable:
            return {"status": "unavailable", "url": self._base_url, "models": []}
        try:
            models = await self.list_models()
        except OllamaError:
            return {"status": "unavailable", "url": self._base_url, "models": []}
        settings = get_settings()
        configured_ready = any(
            model == settings.llm_model or model.split(":")[0] == settings.llm_model.split(":")[0]
            for model in models
        )
        return {
            "status": "ok",
            "url": self._base_url,
            "models": models,
            "llm_model": settings.llm_model,
            "embedding_model": settings.embedding_model,
            "configured_model_available": configured_ready,
        }

"""Ollama adapter: health, model checks, chat generation and streaming."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

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

    async def chat(
        self,
        messages: list[dict],
        temperature: float | None = None,
    ) -> str:
        """One-shot chat completion; returns the assistant message text."""
        settings = get_settings()
        payload = {
            "model": settings.llm_model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": (
                    temperature if temperature is not None else settings.llm_temperature
                )
            },
        }
        try:
            async with self._client() as client:
                response = await client.post(f"{self._base_url}/api/chat", json=payload)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as exc:
            raise OllamaError("Ollama generation failed") from exc
        content = (data.get("message") or {}).get("content")
        if not isinstance(content, str) or not content.strip():
            raise OllamaError("Ollama returned an empty response")
        return content

    async def chat_stream(
        self,
        messages: list[dict],
        temperature: float | None = None,
    ) -> AsyncIterator[str]:
        """Stream assistant message deltas as they are generated."""
        settings = get_settings()
        payload = {
            "model": settings.llm_model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": (
                    temperature if temperature is not None else settings.llm_temperature
                )
            },
        }
        try:
            async with self._client() as client:
                async with client.stream(
                    "POST", f"{self._base_url}/api/chat", json=payload
                ) as response:
                    if response.status_code >= 400:
                        raise OllamaError("Ollama generation failed")
                    async for line in response.aiter_lines():
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            data = json.loads(line)
                        except ValueError:
                            continue
                        if data.get("error"):
                            raise OllamaError("Ollama generation failed")
                        content = (data.get("message") or {}).get("content")
                        if isinstance(content, str) and content:
                            yield content
                        if data.get("done"):
                            break
        except httpx.HTTPError as exc:
            raise OllamaError("Ollama generation failed") from exc


_llm: OllamaProvider | None = None


def get_llm_provider() -> OllamaProvider:
    """Application-wide LLM provider (lazy singleton)."""
    global _llm
    if _llm is None:
        _llm = OllamaProvider()
    return _llm

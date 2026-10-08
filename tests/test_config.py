"""Configuration tests."""

from app.core.config import Settings, get_settings


def test_defaults() -> None:
    settings = Settings(_env_file=None)
    assert settings.api_prefix == "/api"
    assert settings.mongodb_database == "college_rag"
    assert settings.llm_temperature == 0.2


def test_env_overrides(monkeypatch) -> None:
    monkeypatch.setenv("MONGODB_DATABASE", "custom_db")
    monkeypatch.setenv("LLM_MODEL", "my-local-model")
    monkeypatch.setenv("EMBEDDING_MODEL", "my-embed-model")

    get_settings.cache_clear()
    try:
        settings = get_settings()
        assert settings.mongodb_database == "custom_db"
        assert settings.llm_model == "my-local-model"
        assert settings.embedding_model == "my-embed-model"
    finally:
        get_settings.cache_clear()


def test_cors_origin_list_parsing() -> None:
    settings = Settings(
        cors_origins="http://localhost:5173 , http://127.0.0.1:5173,",
        _env_file=None,
    )
    assert settings.cors_origin_list == [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]


def test_settings_never_hardcode_model_names() -> None:
    """Model names come from settings, not call sites."""
    import inspect

    from app.api.routes import health

    source = inspect.getsource(health)
    assert "llama3.2" not in source
    assert "nomic-embed" not in source

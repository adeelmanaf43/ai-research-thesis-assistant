from pathlib import Path

import pytest

from backend.app.core.config import Settings, get_settings
from backend.app.services import (
    LOCAL_PROVIDER_MODE as EXPORTED_LOCAL_PROVIDER_MODE,
)
from backend.app.services import (
    get_llm_provider as exported_get_llm_provider,
)
from backend.app.services import (
    select_llm_provider as exported_select_llm_provider,
)
from backend.app.services.llm import get_llm_provider
from backend.app.services.llm.factory import (
    LOCAL_PROVIDER_MODE,
    OLLAMA_PROVIDER_MODE,
    SUPPORTED_PROVIDER_MODES,
    ProviderConfigurationError,
    normalize_provider_mode,
    select_llm_provider,
)
from backend.app.services.llm.local_provider import LocalLLMProvider


def _settings(provider_mode: str) -> Settings:
    return Settings(
        app_name="Test App",
        app_version="0.1.0",
        environment="test",
        data_dir=Path("data"),
        upload_dir=Path("data/uploads"),
        export_dir=Path("data/exports"),
        database_url="sqlite:///data/test.db",
        provider_mode=provider_mode,
    )


def test_select_llm_provider_uses_local_by_default() -> None:
    selection = select_llm_provider(settings=_settings("local"))

    assert selection.requested_mode == "local"
    assert selection.resolved_mode == "local"
    assert isinstance(selection.provider, LocalLLMProvider)
    assert selection.used_fallback is False
    assert "No external model" in selection.message


def test_select_llm_provider_normalizes_provider_mode() -> None:
    selection = select_llm_provider(" LOCAL ")

    assert selection.requested_mode == LOCAL_PROVIDER_MODE
    assert selection.provider.provider_name == "local"


def test_select_llm_provider_reads_default_settings_when_no_arguments(monkeypatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("PROVIDER_MODE", "local")

    try:
        selection = select_llm_provider()
    finally:
        get_settings.cache_clear()

    assert selection.requested_mode == LOCAL_PROVIDER_MODE
    assert isinstance(selection.provider, LocalLLMProvider)
    assert selection.used_fallback is False


def test_explicit_provider_mode_overrides_settings() -> None:
    selection = select_llm_provider("local", settings=_settings("ollama"))

    assert selection.requested_mode == LOCAL_PROVIDER_MODE
    assert selection.resolved_mode == LOCAL_PROVIDER_MODE
    assert selection.used_fallback is False


def test_select_llm_provider_falls_back_for_future_ollama_mode() -> None:
    selection = select_llm_provider(settings=_settings("ollama"))

    assert selection.requested_mode == OLLAMA_PROVIDER_MODE
    assert selection.resolved_mode == LOCAL_PROVIDER_MODE
    assert isinstance(selection.provider, LocalLLMProvider)
    assert selection.used_fallback is True
    assert "Falling back to local provider" in selection.message


def test_get_llm_provider_returns_selected_provider() -> None:
    provider = get_llm_provider("local")

    assert isinstance(provider, LocalLLMProvider)
    assert provider.health_check().available is True


def test_get_llm_provider_returns_local_for_future_ollama_fallback() -> None:
    provider = get_llm_provider(settings=_settings("ollama"))

    assert isinstance(provider, LocalLLMProvider)
    assert provider.provider_name == "local"


def test_service_package_re_exports_provider_factory_helpers() -> None:
    selection = exported_select_llm_provider("local")
    provider = exported_get_llm_provider("local")

    assert EXPORTED_LOCAL_PROVIDER_MODE == "local"
    assert selection.provider.provider_name == "local"
    assert isinstance(provider, LocalLLMProvider)


def test_provider_selection_serializes_without_provider_object() -> None:
    payload = select_llm_provider("ollama").to_dict()

    assert payload == {
        "requested_mode": "ollama",
        "resolved_mode": "local",
        "provider_name": "local",
        "used_fallback": True,
        "message": (
            "Ollama provider is optional and not implemented in this milestone. "
            "Falling back to local provider."
        ),
    }


def test_normalize_provider_mode_rejects_empty_mode() -> None:
    with pytest.raises(ProviderConfigurationError, match="cannot be empty"):
        normalize_provider_mode("   ")


def test_select_llm_provider_rejects_unknown_mode() -> None:
    with pytest.raises(ProviderConfigurationError, match="Unsupported provider mode"):
        select_llm_provider("cloud")


def test_supported_provider_modes_are_explicit() -> None:
    assert SUPPORTED_PROVIDER_MODES == {"local", "ollama"}

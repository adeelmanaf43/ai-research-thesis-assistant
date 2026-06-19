from dataclasses import dataclass

from backend.app.core.config import Settings, get_settings
from backend.app.services.llm.base import BaseLLMProvider
from backend.app.services.llm.local_provider import LocalLLMProvider

LOCAL_PROVIDER_MODE = "local"
OLLAMA_PROVIDER_MODE = "ollama"
SUPPORTED_PROVIDER_MODES = {LOCAL_PROVIDER_MODE, OLLAMA_PROVIDER_MODE}


class ProviderConfigurationError(ValueError):
    """Raised when provider configuration cannot be resolved safely."""


@dataclass(frozen=True)
class ProviderSelection:
    requested_mode: str
    resolved_mode: str
    provider: BaseLLMProvider
    used_fallback: bool
    message: str

    def to_dict(self) -> dict[str, str | bool]:
        return {
            "requested_mode": self.requested_mode,
            "resolved_mode": self.resolved_mode,
            "provider_name": self.provider.provider_name,
            "used_fallback": self.used_fallback,
            "message": self.message,
        }


def normalize_provider_mode(provider_mode: str | None) -> str:
    normalized_mode = (provider_mode or LOCAL_PROVIDER_MODE).strip().lower()
    if not normalized_mode:
        raise ProviderConfigurationError("Provider mode cannot be empty.")
    return normalized_mode


def select_llm_provider(
    provider_mode: str | None = None,
    *,
    settings: Settings | None = None,
) -> ProviderSelection:
    requested_mode = normalize_provider_mode(
        provider_mode if provider_mode is not None else (settings or get_settings()).provider_mode
    )

    if requested_mode == LOCAL_PROVIDER_MODE:
        return ProviderSelection(
            requested_mode=requested_mode,
            resolved_mode=LOCAL_PROVIDER_MODE,
            provider=LocalLLMProvider(),
            used_fallback=False,
            message="Using local provider. No external model is required.",
        )

    if requested_mode == OLLAMA_PROVIDER_MODE:
        return ProviderSelection(
            requested_mode=requested_mode,
            resolved_mode=LOCAL_PROVIDER_MODE,
            provider=LocalLLMProvider(),
            used_fallback=True,
            message=(
                "Ollama provider is optional and not implemented in this milestone. "
                "Falling back to local provider."
            ),
        )

    supported_modes = ", ".join(sorted(SUPPORTED_PROVIDER_MODES))
    raise ProviderConfigurationError(
        f"Unsupported provider mode '{requested_mode}'. Supported modes: {supported_modes}."
    )


def get_llm_provider(
    provider_mode: str | None = None,
    *,
    settings: Settings | None = None,
) -> BaseLLMProvider:
    return select_llm_provider(provider_mode, settings=settings).provider

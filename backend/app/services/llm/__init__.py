"""LLM provider boundary for optional future local and cloud integrations."""

from backend.app.services.llm.base import (
    BaseLLMProvider,
    ProviderHealth,
    ProviderResponse,
)
from backend.app.services.llm.factory import (
    LOCAL_PROVIDER_MODE,
    OLLAMA_PROVIDER_MODE,
    SUPPORTED_PROVIDER_MODES,
    ProviderConfigurationError,
    ProviderSelection,
    get_llm_provider,
    normalize_provider_mode,
    select_llm_provider,
)
from backend.app.services.llm.local_provider import (
    LocalAnswer,
    LocalLLMProvider,
    SourceSnippet,
    answer_question,
)

__all__ = [
    "BaseLLMProvider",
    "get_llm_provider",
    "LOCAL_PROVIDER_MODE",
    "LocalAnswer",
    "LocalLLMProvider",
    "normalize_provider_mode",
    "OLLAMA_PROVIDER_MODE",
    "ProviderConfigurationError",
    "ProviderHealth",
    "ProviderResponse",
    "ProviderSelection",
    "select_llm_provider",
    "SourceSnippet",
    "SUPPORTED_PROVIDER_MODES",
    "answer_question",
]

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class ProviderHealth:
    provider: str
    available: bool
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ProviderResponse:
    provider: str
    content: str
    model: str | None = None
    source_chunks: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    limitations: list[str] = field(default_factory=list)
    used_fallback: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class BaseLLMProvider(ABC):
    """Contract for optional AI providers.

    Providers must operate on bounded inputs supplied by local services. This
    keeps the app useful in local mode and prevents future providers from
    becoming a hidden requirement for core document processing.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the stable provider identifier used in logs and responses."""

    @abstractmethod
    def generate_summary(
        self,
        text: str,
        *,
        max_words: int = 150,
    ) -> ProviderResponse:
        """Generate or rewrite a short summary from bounded text."""

    @abstractmethod
    def answer_question(
        self,
        question: str,
        context_chunks: list[dict[str, Any]],
        *,
        max_answer_sentences: int = 3,
    ) -> ProviderResponse:
        """Answer using only supplied source chunks."""

    @abstractmethod
    def extract_research_info(
        self,
        text: str,
        *,
        sections: list[dict[str, Any]] | None = None,
    ) -> ProviderResponse:
        """Extract structured research information from bounded text."""

    @abstractmethod
    def health_check(self) -> ProviderHealth:
        """Return provider availability without raising for normal outages."""

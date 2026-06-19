import pytest

from backend.app.services.llm.base import (
    BaseLLMProvider,
    ProviderHealth,
    ProviderResponse,
)


class FakeProvider(BaseLLMProvider):
    @property
    def provider_name(self) -> str:
        return "fake"

    def generate_summary(
        self,
        text: str,
        *,
        max_words: int = 150,
    ) -> ProviderResponse:
        return ProviderResponse(
            provider=self.provider_name,
            content=" ".join(text.split()[:max_words]),
            model=None,
            limitations=["Fake provider is used only for interface tests."],
        )

    def answer_question(
        self,
        question: str,
        context_chunks: list[dict],
        *,
        max_answer_sentences: int = 3,
    ) -> ProviderResponse:
        return ProviderResponse(
            provider=self.provider_name,
            content=f"Question: {question}",
            source_chunks=context_chunks[:max_answer_sentences],
        )

    def extract_research_info(
        self,
        text: str,
        *,
        sections: list[dict] | None = None,
    ) -> ProviderResponse:
        return ProviderResponse(
            provider=self.provider_name,
            content="research_info",
            metadata={
                "text_length": len(text),
                "section_count": len(sections or []),
            },
        )

    def health_check(self) -> ProviderHealth:
        return ProviderHealth(
            provider=self.provider_name,
            available=True,
            message="Fake provider is available.",
        )


class MissingHealthProvider(BaseLLMProvider):
    @property
    def provider_name(self) -> str:
        return "missing-health"

    def generate_summary(
        self,
        text: str,
        *,
        max_words: int = 150,
    ) -> ProviderResponse:
        return ProviderResponse(provider=self.provider_name, content=text)

    def answer_question(
        self,
        question: str,
        context_chunks: list[dict],
        *,
        max_answer_sentences: int = 3,
    ) -> ProviderResponse:
        return ProviderResponse(provider=self.provider_name, content=question)

    def extract_research_info(
        self,
        text: str,
        *,
        sections: list[dict] | None = None,
    ) -> ProviderResponse:
        return ProviderResponse(provider=self.provider_name, content=text)


def test_base_llm_provider_cannot_be_instantiated_directly() -> None:
    with pytest.raises(TypeError):
        BaseLLMProvider()


def test_incomplete_provider_cannot_be_instantiated() -> None:
    with pytest.raises(TypeError):
        MissingHealthProvider()


def test_provider_response_defaults_are_not_shared_between_instances() -> None:
    first_response = ProviderResponse(provider="local", content="First")
    second_response = ProviderResponse(provider="local", content="Second")

    first_response.source_chunks.append({"chunk_id": 1})
    first_response.metadata["mode"] = "local"
    first_response.limitations.append("Local only.")

    assert second_response.source_chunks == []
    assert second_response.metadata == {}
    assert second_response.limitations == []


def test_provider_health_defaults_are_not_shared_between_instances() -> None:
    first_health = ProviderHealth(provider="local", available=True, message="ok")
    second_health = ProviderHealth(provider="ollama", available=False, message="offline")

    first_health.details["requires_network"] = False

    assert second_health.details == {}


def test_provider_response_serializes_for_api_boundaries() -> None:
    response = ProviderResponse(
        provider="local",
        content="Short answer.",
        model=None,
        source_chunks=[{"chunk_id": 1, "score": 0.8}],
        metadata={"mode": "local"},
        limitations=["Uses supplied context only."],
        used_fallback=True,
    )

    payload = response.to_dict()

    assert payload["provider"] == "local"
    assert payload["content"] == "Short answer."
    assert payload["source_chunks"][0]["chunk_id"] == 1
    assert payload["metadata"]["mode"] == "local"
    assert payload["limitations"] == ["Uses supplied context only."]
    assert payload["used_fallback"] is True


def test_provider_health_serializes_for_status_checks() -> None:
    health = ProviderHealth(
        provider="ollama",
        available=False,
        message="Ollama is not running.",
        details={"timeout_seconds": 5},
    )

    payload = health.to_dict()

    assert payload == {
        "provider": "ollama",
        "available": False,
        "message": "Ollama is not running.",
        "details": {"timeout_seconds": 5},
    }


def test_concrete_provider_implements_required_contract() -> None:
    provider = FakeProvider()

    summary = provider.generate_summary("alpha beta gamma", max_words=2)
    answer = provider.answer_question(
        "What was found?",
        [{"chunk_id": 10, "text": "The study found better retrieval."}],
    )
    research_info = provider.extract_research_info(
        "The objective was local-first analysis.",
        sections=[{"section_name": "Introduction"}],
    )
    health = provider.health_check()

    assert provider.provider_name == "fake"
    assert summary.content == "alpha beta"
    assert answer.source_chunks[0]["chunk_id"] == 10
    assert research_info.metadata == {"text_length": 39, "section_count": 1}
    assert health.available is True

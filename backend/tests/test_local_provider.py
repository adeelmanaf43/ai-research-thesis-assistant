import pytest

from backend.app.services.llm.base import BaseLLMProvider
from backend.app.services.llm.local_provider import (
    LocalAnswer,
    LocalLLMProvider,
    SourceSnippet,
    answer_question,
)
from backend.app.services.retrieval import RetrievalResult


def _result(
    text: str,
    *,
    chunk_id: int = 1,
    chunk_index: int = 0,
    section_name: str = "Results",
    score: float = 0.8,
) -> RetrievalResult:
    return RetrievalResult(
        chunk_id=chunk_id,
        document_id=10,
        chunk_index=chunk_index,
        section_name=section_name,
        page_start=2,
        page_end=3,
        score=score,
        text=text,
    )


def test_answer_question_returns_extractive_answer_from_retrieved_chunks() -> None:
    chunks = [
        _result(
            "The methodology used a survey sample of 120 postgraduate students. "
            "The survey measured citation confidence and review time.",
            section_name="Methodology",
        )
    ]

    answer = answer_question("What sample did the methodology use?", chunks)

    assert isinstance(answer, LocalAnswer)
    assert answer.answer_found is True
    assert answer.provider == "local"
    assert answer.answer == "The methodology used a survey sample of 120 postgraduate students."
    assert len(answer.source_snippets) == 1
    assert isinstance(answer.source_snippets[0], SourceSnippet)
    assert answer.source_snippets[0].section_name == "Methodology"
    assert answer.source_snippets[0].snippet == answer.answer
    assert "extractive" in answer.limitations[0]


def test_answer_question_uses_multiple_source_sentences_when_needed() -> None:
    chunks = [
        _result(
            "Retrieval improved citation confidence. "
            "Students completed literature reviews faster with source evidence.",
            chunk_id=1,
            chunk_index=0,
        ),
        _result(
            "The conclusion discussed future report export workflows.",
            chunk_id=2,
            chunk_index=1,
            section_name="Conclusion",
            score=0.5,
        ),
    ]

    answer = answer_question(
        "What improved citation confidence and literature reviews?",
        chunks,
        max_answer_sentences=2,
    )

    assert answer.answer_found is True
    assert "Retrieval improved citation confidence." in answer.answer
    assert "Students completed literature reviews faster" in answer.answer
    assert len(answer.source_snippets) == 2


def test_answer_question_says_when_answer_is_not_found() -> None:
    chunks = [
        _result(
            "The conclusion discussed future report export workflows.",
            section_name="Conclusion",
        )
    ]

    answer = answer_question("What sample size was used?", chunks)

    assert answer.answer_found is False
    assert answer.answer.startswith("I could not find the answer")
    assert answer.source_snippets[0].snippet == (
        "The conclusion discussed future report export workflows."
    )


def test_answer_question_ignores_numbered_heading_fragments() -> None:
    chunks = [
        _result(
            "2.1.3 Fatty Acid Nomenclature. "
            "2.2 Classification of Fatty Acids. "
            "The literature review explains that fatty acids are classified by "
            "saturation level and molecular structure.",
            section_name="Literature Review",
        )
    ]

    answer = answer_question("What does the document say about fatty acids?", chunks)

    assert answer.answer_found is True
    assert answer.answer == (
        "The literature review explains that fatty acids are classified by "
        "saturation level and molecular structure."
    )
    assert "2.1.3" not in answer.answer


def test_answer_question_trims_numbered_heading_prefix_from_sentence() -> None:
    chunks = [
        _result(
            "2.12.2 European Union Regulation on Trans Fatty Acids "
            "In the European Union, industrially produced trans fatty acids "
            "are regulated by quantitative restrictions.",
            section_name="Literature Review",
        )
    ]

    answer = answer_question("What does the document say about trans fatty acids?", chunks)

    assert answer.answer_found is True
    assert answer.answer.startswith("In the European Union")
    assert "2.12.2" not in answer.answer


def test_answer_question_handles_no_retrieved_chunks() -> None:
    answer = answer_question("What did the study find?", [])

    assert answer.answer_found is False
    assert answer.source_snippets == []
    assert "could not find" in answer.answer


def test_answer_question_limits_source_snippets() -> None:
    chunks = [
        _result("Retrieval improved citation confidence.", chunk_id=1, chunk_index=0),
        _result("Retrieval improved review speed.", chunk_id=2, chunk_index=1),
        _result("Retrieval improved source tracking.", chunk_id=3, chunk_index=2),
    ]

    answer = answer_question("What did retrieval improve?", chunks, max_source_snippets=2)

    assert len(answer.source_snippets) == 2
    assert [snippet.chunk_id for snippet in answer.source_snippets] == [1, 2]


def test_answer_question_serializes_for_api_use() -> None:
    answer = answer_question(
        "What improved citation confidence?",
        [_result("Retrieval improved citation confidence.", chunk_id=7)],
    )

    payload = answer.to_dict()

    assert payload["answer"] == "Retrieval improved citation confidence."
    assert payload["answer_found"] is True
    assert payload["provider"] == "local"
    assert payload["source_snippets"][0]["chunk_id"] == 7
    assert payload["limitations"] == answer.limitations


def test_local_llm_provider_implements_base_interface() -> None:
    provider = LocalLLMProvider()

    assert isinstance(provider, BaseLLMProvider)
    assert provider.provider_name == "local"


def test_local_llm_provider_generates_extractive_summary() -> None:
    provider = LocalLLMProvider()

    response = provider.generate_summary(
        "The study evaluates local document retrieval for thesis writing. "
        "The results show improved source tracking and faster literature review work.",
        max_words=25,
    )

    assert response.provider == "local"
    assert "local document retrieval" in response.content
    assert response.metadata["method"] == "extractive_sentence_scoring"
    assert response.metadata["selected_sentence_count"] >= 1
    assert response.used_fallback is False
    assert "No external model" in response.limitations[1]


def test_local_llm_provider_answers_from_context_chunks() -> None:
    provider = LocalLLMProvider()

    response = provider.answer_question(
        "What sample did the methodology use?",
        [
            {
                "chunk_id": 5,
                "document_id": 2,
                "chunk_index": 0,
                "section_name": "Methodology",
                "page_start": 4,
                "page_end": 5,
                "score": 0.91,
                "text": (
                    "The methodology used a survey sample of 120 postgraduate students. "
                    "The survey measured citation confidence."
                ),
            }
        ],
    )

    assert response.provider == "local"
    assert response.metadata["answer_found"] is True
    assert response.content == "The methodology used a survey sample of 120 postgraduate students."
    assert response.source_chunks[0]["chunk_id"] == 5


def test_local_llm_provider_extracts_research_info_locally() -> None:
    provider = LocalLLMProvider()

    response = provider.extract_research_info(
        "",
        sections=[
            {
                "section_name": "Introduction",
                "section_type": "introduction",
                "text": "The objective of this study is to improve local thesis analysis.",
            }
        ],
    )

    objective = response.metadata["fields"]["objectives"]

    assert response.provider == "local"
    assert response.content == "local_research_info"
    assert objective["source_section"] == "Introduction"
    assert "objective" in objective["extracted_text"].lower()


def test_local_llm_provider_health_check_is_always_available() -> None:
    provider = LocalLLMProvider()

    health = provider.health_check()

    assert health.provider == "local"
    assert health.available is True
    assert health.details == {"requires_network": False, "requires_ollama": False}


@pytest.mark.parametrize(
    ("question", "max_answer_sentences", "max_source_snippets", "message"),
    [
        ("   ", 2, 5, "Question"),
        ("What did retrieval improve?", 0, 5, "answer sentence"),
        ("What did retrieval improve?", 2, 0, "source snippet"),
    ],
)
def test_answer_question_validates_inputs(
    question: str,
    max_answer_sentences: int,
    max_source_snippets: int,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        answer_question(
            question,
            [_result("Retrieval improved citation confidence.")],
            max_answer_sentences=max_answer_sentences,
            max_source_snippets=max_source_snippets,
        )

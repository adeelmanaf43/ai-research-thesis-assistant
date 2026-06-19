import re
from dataclasses import asdict, dataclass
from typing import Any

from backend.app.services.llm.base import BaseLLMProvider, ProviderHealth, ProviderResponse
from backend.app.services.local_analysis import (
    SectionLike,
    extract_research_information,
    summarize_section,
)
from backend.app.services.retrieval import RetrievalResult

QUESTION_TOKEN_PATTERN = re.compile(r"\b[a-zA-Z][a-zA-Z'-]{2,}\b")
SENTENCE_PATTERN = re.compile(r"[^.!?]+[.!?]?")
DECIMAL_DOT_PLACEHOLDER = "<DOT>"
NUMBERED_HEADING_PREFIX_PATTERN = re.compile(
    r"^\s*\d+(?:\.\d+)+\s+.+?\b" r"((?:In|The|This|These|Those|A|An|Although|However)\s+[a-z].*)$"
)
QUESTION_STOPWORDS = {
    "about",
    "after",
    "also",
    "and",
    "are",
    "can",
    "did",
    "does",
    "for",
    "from",
    "has",
    "have",
    "how",
    "into",
    "is",
    "of",
    "on",
    "or",
    "paper",
    "study",
    "that",
    "the",
    "this",
    "use",
    "used",
    "using",
    "was",
    "were",
    "what",
    "when",
    "where",
    "which",
    "who",
    "why",
    "with",
}
DEFAULT_MAX_ANSWER_SENTENCES = 2
DEFAULT_MAX_SOURCE_SNIPPETS = 5
LOCAL_PROVIDER_NAME = "local"


@dataclass(frozen=True)
class SourceSnippet:
    chunk_id: int
    chunk_index: int
    section_name: str | None
    page_start: int | None
    page_end: int | None
    score: float
    snippet: str

    def to_dict(self) -> dict[str, int | str | float | None]:
        return asdict(self)


@dataclass(frozen=True)
class LocalAnswer:
    answer: str
    answer_found: bool
    provider: str
    source_snippets: list[SourceSnippet]
    limitations: list[str]

    def to_dict(
        self,
    ) -> dict[str, str | bool | list[dict[str, int | str | float | None]] | list[str]]:
        return {
            "answer": self.answer,
            "answer_found": self.answer_found,
            "provider": self.provider,
            "source_snippets": [snippet.to_dict() for snippet in self.source_snippets],
            "limitations": self.limitations,
        }


@dataclass(frozen=True)
class _ProviderSection:
    section_name: str
    section_type: str
    text: str


def _question_terms(question: str) -> set[str]:
    return {
        token.lower()
        for token in QUESTION_TOKEN_PATTERN.findall(question)
        if token.lower() not in QUESTION_STOPWORDS
    }


def _split_sentences(text: str) -> list[str]:
    protected_text = re.sub(r"(?<=\d)\.(?=\d)", DECIMAL_DOT_PLACEHOLDER, text)
    return [
        _clean_sentence(sentence.replace(DECIMAL_DOT_PLACEHOLDER, "."))
        for sentence in SENTENCE_PATTERN.findall(protected_text)
        if sentence.strip()
    ]


def _clean_sentence(sentence: str) -> str:
    cleaned = " ".join(sentence.split())
    heading_match = NUMBERED_HEADING_PREFIX_PATTERN.match(cleaned)
    if heading_match:
        candidate = heading_match.group(1).strip()
        if len(_question_terms(candidate)) >= 4:
            return candidate
    return cleaned


def _is_substantive_sentence(sentence: str) -> bool:
    terms = _question_terms(sentence)
    if len(terms) < 4:
        return False
    return bool(re.search(r"[.!?]$", sentence.strip()))


def _sentence_overlap_score(sentence: str, question_terms: set[str]) -> int:
    if not question_terms:
        return 0
    sentence_terms = _question_terms(sentence)
    return len(sentence_terms & question_terms)


def _best_source_snippet(chunk: RetrievalResult, question_terms: set[str]) -> SourceSnippet:
    sentences = [
        sentence for sentence in _split_sentences(chunk.text) if _is_substantive_sentence(sentence)
    ]
    if not sentences:
        sentences = _split_sentences(chunk.text)
    best_sentence = max(
        sentences,
        key=lambda sentence: (
            _sentence_overlap_score(sentence, question_terms),
            -len(sentence),
        ),
        default=" ".join(chunk.text.split()),
    )
    return SourceSnippet(
        chunk_id=chunk.chunk_id,
        chunk_index=chunk.chunk_index,
        section_name=chunk.section_name,
        page_start=chunk.page_start,
        page_end=chunk.page_end,
        score=chunk.score,
        snippet=best_sentence,
    )


def _context_chunk_to_retrieval_result(raw_chunk: dict[str, Any], index: int) -> RetrievalResult:
    return RetrievalResult(
        chunk_id=int(raw_chunk.get("chunk_id") or raw_chunk.get("id") or index + 1),
        document_id=int(raw_chunk.get("document_id") or 0),
        chunk_index=int(raw_chunk.get("chunk_index") or index),
        section_name=raw_chunk.get("section_name"),
        page_start=raw_chunk.get("page_start"),
        page_end=raw_chunk.get("page_end"),
        score=float(raw_chunk.get("score") or 0.0),
        text=str(
            raw_chunk.get("text") or raw_chunk.get("full_text") or raw_chunk.get("snippet") or ""
        ),
    )


def _section_from_text(text: str) -> _ProviderSection:
    return _ProviderSection(
        section_name="Provided Text",
        section_type="abstract",
        text=text,
    )


def _sections_from_payload(sections: list[dict[str, Any]] | None) -> list[SectionLike]:
    if not sections:
        return []

    parsed_sections: list[SectionLike] = []
    for section in sections:
        if not isinstance(section, dict):
            continue
        parsed_sections.append(
            _ProviderSection(
                section_name=str(section.get("section_name") or "Unknown"),
                section_type=str(section.get("section_type") or "unknown"),
                text=str(section.get("text") or ""),
            )
        )
    return parsed_sections


def answer_question(
    question: str | None,
    retrieved_chunks: list[RetrievalResult],
    *,
    max_answer_sentences: int = DEFAULT_MAX_ANSWER_SENTENCES,
    max_source_snippets: int = DEFAULT_MAX_SOURCE_SNIPPETS,
) -> LocalAnswer:
    cleaned_question = (question or "").strip()
    if not cleaned_question:
        raise ValueError("Question must not be empty.")
    if max_answer_sentences < 1:
        raise ValueError("Maximum answer sentence count must be a positive integer.")
    if max_source_snippets < 1:
        raise ValueError("Maximum source snippet count must be a positive integer.")

    question_terms = _question_terms(cleaned_question)
    source_snippets = [
        _best_source_snippet(chunk, question_terms)
        for chunk in retrieved_chunks[:max_source_snippets]
        if chunk.text and chunk.text.strip()
    ]

    answer_sentences: list[str] = []
    seen_sentences: set[str] = set()
    answer_candidates: list[tuple[int, int, int, str]] = []
    for chunk_position, chunk in enumerate(retrieved_chunks[:max_source_snippets]):
        for sentence_position, sentence in enumerate(_split_sentences(chunk.text)):
            if not _is_substantive_sentence(sentence):
                continue
            overlap_score = _sentence_overlap_score(sentence, question_terms)
            if overlap_score > 0:
                answer_candidates.append(
                    (-overlap_score, chunk_position, sentence_position, sentence)
                )

    for _score, _chunk_position, _sentence_position, sentence in sorted(answer_candidates):
        overlap_score = _sentence_overlap_score(sentence, question_terms)
        if overlap_score == 0:
            continue
        dedupe_key = sentence.lower()
        if dedupe_key in seen_sentences:
            continue
        seen_sentences.add(dedupe_key)
        answer_sentences.append(sentence)
        if len(answer_sentences) >= max_answer_sentences:
            break

    limitations = [
        "Local fallback answers are extractive and use only retrieved source chunks.",
        "If retrieved chunks do not contain the answer, the provider must say so.",
    ]

    if not answer_sentences:
        return LocalAnswer(
            answer=(
                "I could not find the answer in the retrieved source chunks. "
                "Review the source snippets below or try a more specific question."
            ),
            answer_found=False,
            provider=LOCAL_PROVIDER_NAME,
            source_snippets=source_snippets,
            limitations=limitations,
        )

    return LocalAnswer(
        answer=" ".join(answer_sentences),
        answer_found=True,
        provider=LOCAL_PROVIDER_NAME,
        source_snippets=source_snippets,
        limitations=limitations,
    )


class LocalLLMProvider(BaseLLMProvider):
    """Local provider implementation that never calls an external model."""

    @property
    def provider_name(self) -> str:
        return LOCAL_PROVIDER_NAME

    def generate_summary(
        self,
        text: str,
        *,
        max_words: int = 150,
    ) -> ProviderResponse:
        cleaned_text = (text or "").strip()
        if not cleaned_text:
            return ProviderResponse(
                provider=self.provider_name,
                content="",
                limitations=["No text was supplied for local summary generation."],
            )
        if max_words < 1:
            raise ValueError("Summary word limit must be a positive integer.")

        section = _section_from_text(cleaned_text)
        summary = summarize_section(section, max_words=max_words)
        content = summary.summary if summary else ""
        return ProviderResponse(
            provider=self.provider_name,
            content=content,
            metadata={
                "method": "extractive_sentence_scoring",
                "max_words": max_words,
                "selected_sentence_count": summary.selected_sentence_count if summary else 0,
            },
            limitations=[
                "Local summaries are extractive and use only the supplied text.",
                "No external model was called.",
            ],
        )

    def answer_question(
        self,
        question: str,
        context_chunks: list[dict[str, Any]],
        *,
        max_answer_sentences: int = 3,
    ) -> ProviderResponse:
        retrieved_chunks = [
            _context_chunk_to_retrieval_result(raw_chunk, index)
            for index, raw_chunk in enumerate(context_chunks or [])
            if isinstance(raw_chunk, dict)
        ]
        local_answer = answer_question(
            question,
            retrieved_chunks,
            max_answer_sentences=max_answer_sentences,
            max_source_snippets=max(len(retrieved_chunks), 1),
        )
        return ProviderResponse(
            provider=self.provider_name,
            content=local_answer.answer,
            source_chunks=[snippet.to_dict() for snippet in local_answer.source_snippets],
            metadata={"answer_found": local_answer.answer_found},
            limitations=local_answer.limitations,
        )

    def extract_research_info(
        self,
        text: str,
        *,
        sections: list[dict[str, Any]] | None = None,
    ) -> ProviderResponse:
        parsed_sections = _sections_from_payload(sections)
        research_info = extract_research_information(
            text or None,
            sections=parsed_sections or None,
        )
        return ProviderResponse(
            provider=self.provider_name,
            content="local_research_info",
            metadata=research_info.to_dict(),
            limitations=[
                "Local research information extraction is rule-based.",
                "Unknown fields are returned with null text and 0.0 confidence.",
            ],
        )

    def health_check(self) -> ProviderHealth:
        return ProviderHealth(
            provider=self.provider_name,
            available=True,
            message="Local provider is available. No external model is required.",
            details={"requires_network": False, "requires_ollama": False},
        )

import re
from dataclasses import asdict, dataclass

from backend.app.services.retrieval import RetrievalResult

QUESTION_TOKEN_PATTERN = re.compile(r"\b[a-zA-Z][a-zA-Z'-]{2,}\b")
SENTENCE_PATTERN = re.compile(r"[^.!?]+[.!?]?")
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


def _question_terms(question: str) -> set[str]:
    return {
        token.lower()
        for token in QUESTION_TOKEN_PATTERN.findall(question)
        if token.lower() not in QUESTION_STOPWORDS
    }


def _split_sentences(text: str) -> list[str]:
    return [
        " ".join(sentence.split())
        for sentence in SENTENCE_PATTERN.findall(text)
        if sentence.strip()
    ]


def _sentence_overlap_score(sentence: str, question_terms: set[str]) -> int:
    if not question_terms:
        return 0
    sentence_terms = _question_terms(sentence)
    return len(sentence_terms & question_terms)


def _best_source_snippet(chunk: RetrievalResult, question_terms: set[str]) -> SourceSnippet:
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
            provider="local",
            source_snippets=source_snippets,
            limitations=limitations,
        )

    return LocalAnswer(
        answer=" ".join(answer_sentences),
        answer_found=True,
        provider="local",
        source_snippets=source_snippets,
        limitations=limitations,
    )

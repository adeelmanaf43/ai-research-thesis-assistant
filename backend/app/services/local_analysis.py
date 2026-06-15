import math
import re
from collections import Counter
from dataclasses import asdict, dataclass
from typing import Protocol

TOKEN_PATTERN = re.compile(r"\b[a-zA-Z][a-zA-Z-]{2,}\b")
WORD_PATTERN = re.compile(r"\b[a-zA-Z][a-zA-Z'-]*\b")
SENTENCE_PATTERN = re.compile(r"[^.!?]+[.!?]?")
REFERENCE_ENTRY_PATTERN = re.compile(
    r"^\s*(?:\[\d+\]|\d+[\.)]|\w[\w'-]+,\s+(?:[A-Z]\.\s*)+|\w[\w'-]+\s+et\s+al\.)",
    re.IGNORECASE,
)
VOWEL_GROUP_PATTERN = re.compile(r"[aeiouy]+", re.IGNORECASE)
SUMMARY_SECTION_TYPES = {
    "abstract",
    "introduction",
    "methodology",
    "results",
    "discussion",
    "conclusion",
}
DEFAULT_SUMMARY_SENTENCE_LIMIT = 2
DEFAULT_SUMMARY_WORD_LIMIT = 90

STOPWORDS = {
    "able",
    "about",
    "above",
    "across",
    "after",
    "again",
    "against",
    "all",
    "almost",
    "also",
    "and",
    "another",
    "any",
    "are",
    "around",
    "based",
    "but",
    "although",
    "among",
    "can",
    "because",
    "been",
    "before",
    "being",
    "below",
    "between",
    "both",
    "for",
    "how",
    "into",
    "may",
    "not",
    "off",
    "one",
    "our",
    "out",
    "own",
    "per",
    "set",
    "she",
    "the",
    "too",
    "two",
    "use",
    "used",
    "uses",
    "using",
    "via",
    "cannot",
    "could",
    "did",
    "does",
    "doing",
    "during",
    "each",
    "from",
    "further",
    "his",
    "had",
    "has",
    "have",
    "having",
    "here",
    "hers",
    "herself",
    "himself",
    "its",
    "itself",
    "just",
    "more",
    "most",
    "nor",
    "now",
    "onto",
    "only",
    "other",
    "ought",
    "ours",
    "ourselves",
    "over",
    "same",
    "shall",
    "should",
    "some",
    "such",
    "than",
    "that",
    "their",
    "theirs",
    "them",
    "themselves",
    "then",
    "there",
    "these",
    "they",
    "this",
    "those",
    "through",
    "thus",
    "under",
    "until",
    "very",
    "was",
    "were",
    "what",
    "when",
    "where",
    "which",
    "while",
    "who",
    "whom",
    "why",
    "will",
    "with",
    "would",
    "your",
    "yours",
    "yourself",
    "yourselves",
    "abstract",
    "chapter",
    "figure",
    "paper",
    "section",
    "table",
}


@dataclass(frozen=True)
class KeywordScore:
    keyword: str
    score: float
    frequency: int

    def to_dict(self) -> dict[str, str | float | int]:
        return asdict(self)


class SectionLike(Protocol):
    section_name: str
    section_type: str
    text: str


class ChunkLike(Protocol):
    section_name: str | None


@dataclass(frozen=True)
class ReadabilityMetrics:
    sentence_count: int
    average_words_per_sentence: float
    average_syllables_per_word: float
    flesch_reading_ease: float | None

    def to_dict(self) -> dict[str, int | float | None]:
        return asdict(self)


@dataclass(frozen=True)
class DocumentStatistics:
    total_word_count: int
    word_count_by_section: dict[str, int]
    chunk_count_by_section: dict[str, int]
    reference_count_estimate: int
    readability: ReadabilityMetrics

    def to_dict(self) -> dict[str, int | dict[str, int] | dict[str, int | float | None]]:
        payload = asdict(self)
        payload["readability"] = self.readability.to_dict()
        return payload


@dataclass(frozen=True)
class SectionSummary:
    section_type: str
    section_name: str
    summary: str
    selected_sentence_count: int
    source_sentence_indexes: list[int]

    def to_dict(self) -> dict[str, str | int | list[int]]:
        return asdict(self)


def tokenize_keywords(text: str | None, *, min_word_length: int = 3) -> list[str]:
    if min_word_length < 1:
        raise ValueError("Minimum word length must be a positive integer.")
    if not text:
        return []

    tokens: list[str] = []
    for match in TOKEN_PATTERN.finditer(text.lower()):
        token = match.group(0).strip("-")
        if len(token) < min_word_length:
            continue
        if token in STOPWORDS:
            continue
        if token.replace("-", "").isdigit():
            continue
        tokens.append(token)
    return tokens


def _keyword_score(frequency: int, total_keywords: int) -> float:
    term_frequency = frequency / total_keywords
    frequency_weight = 1 + math.log(frequency)
    return round(term_frequency * frequency_weight, 6)


def extract_keywords(
    text: str | None,
    *,
    top_n: int = 10,
    min_word_length: int = 3,
) -> list[KeywordScore]:
    if top_n < 1:
        raise ValueError("Keyword limit must be a positive integer.")

    tokens = tokenize_keywords(text, min_word_length=min_word_length)
    if not tokens:
        return []

    frequencies = Counter(tokens)
    total_keywords = sum(frequencies.values())
    scored_keywords = [
        KeywordScore(
            keyword=keyword,
            score=_keyword_score(frequency, total_keywords),
            frequency=frequency,
        )
        for keyword, frequency in frequencies.items()
    ]

    return sorted(
        scored_keywords,
        key=lambda keyword_score: (
            -keyword_score.score,
            -keyword_score.frequency,
            keyword_score.keyword,
        ),
    )[:top_n]


def count_analysis_words(text: str | None) -> int:
    if not text:
        return 0
    return len(WORD_PATTERN.findall(text))


def count_words_by_section(sections: list[SectionLike] | None) -> dict[str, int]:
    if not sections:
        return {}

    section_counts: dict[str, int] = {}
    for section in sections:
        section_name = section.section_name.strip() or "Unknown"
        section_counts[section_name] = section_counts.get(section_name, 0) + count_analysis_words(
            section.text
        )
    return section_counts


def count_chunks_by_section(chunks: list[ChunkLike] | None) -> dict[str, int]:
    if not chunks:
        return {}

    chunk_counts: dict[str, int] = {}
    for chunk in chunks:
        section_name = (chunk.section_name or "Unknown").strip() or "Unknown"
        chunk_counts[section_name] = chunk_counts.get(section_name, 0) + 1
    return chunk_counts


def estimate_reference_count(
    text: str | None,
    *,
    sections: list[SectionLike] | None = None,
) -> int:
    reference_text = ""
    if sections:
        reference_parts = [
            section.text
            for section in sections
            if section.section_type == "references"
            or section.section_name.strip().lower() in {"references", "bibliography"}
        ]
        reference_text = "\n".join(reference_parts)

    candidate_text = reference_text or text or ""
    if not candidate_text.strip():
        return 0

    lines = [line.strip() for line in candidate_text.splitlines() if line.strip()]
    entry_count = sum(1 for line in lines if REFERENCE_ENTRY_PATTERN.match(line))
    if entry_count:
        return entry_count

    return len(re.findall(r"\([A-Z][A-Za-z'-]+,\s*(?:19|20)\d{2}\)", candidate_text))


def _split_sentences(text: str | None) -> list[str]:
    if not text:
        return []
    return [
        sentence.strip()
        for sentence in SENTENCE_PATTERN.findall(text)
        if count_analysis_words(sentence) > 0
    ]


def _sentence_score(sentence: str, keyword_frequencies: Counter[str], index: int) -> float:
    tokens = tokenize_keywords(sentence)
    if not tokens:
        return 0.0

    frequency_score = sum(keyword_frequencies[token] for token in tokens)
    length_penalty = max(len(tokens), 1)
    position_bonus = 0.1 / (index + 1)
    return round((frequency_score / length_penalty) + position_bonus, 6)


def _fit_sentences_to_word_limit(
    scored_sentences: list[tuple[int, str, float]],
    max_words: int,
) -> list[tuple[int, str, float]]:
    selected: list[tuple[int, str, float]] = []
    current_word_count = 0
    for sentence_index, sentence, score in scored_sentences:
        sentence_word_count = count_analysis_words(sentence)
        if sentence_word_count > max_words:
            continue
        if current_word_count + sentence_word_count > max_words:
            continue
        selected.append((sentence_index, sentence, score))
        current_word_count += sentence_word_count
    return selected


def summarize_section(
    section: SectionLike,
    *,
    max_sentences: int = DEFAULT_SUMMARY_SENTENCE_LIMIT,
    max_words: int = DEFAULT_SUMMARY_WORD_LIMIT,
) -> SectionSummary | None:
    if max_sentences < 1:
        raise ValueError("Summary sentence limit must be a positive integer.")
    if max_words < 1:
        raise ValueError("Summary word limit must be a positive integer.")

    if section.section_type not in SUMMARY_SECTION_TYPES:
        return None

    sentences = _split_sentences(section.text)
    if not sentences:
        return SectionSummary(
            section_type=section.section_type,
            section_name=section.section_name,
            summary="",
            selected_sentence_count=0,
            source_sentence_indexes=[],
        )

    keyword_frequencies = Counter(tokenize_keywords(section.text))
    if not keyword_frequencies:
        candidate_sentences = [(index, sentence, 0.0) for index, sentence in enumerate(sentences)]
    else:
        candidate_sentences = [
            (index, sentence, _sentence_score(sentence, keyword_frequencies, index))
            for index, sentence in enumerate(sentences)
        ]
        candidate_sentences.sort(key=lambda item: (-item[2], item[0]))

    selected = _fit_sentences_to_word_limit(candidate_sentences, max_words)[:max_sentences]
    selected.sort(key=lambda item: item[0])
    summary_sentences = [sentence for _, sentence, _ in selected]

    return SectionSummary(
        section_type=section.section_type,
        section_name=section.section_name,
        summary=" ".join(summary_sentences).strip(),
        selected_sentence_count=len(summary_sentences),
        source_sentence_indexes=[index for index, _, _ in selected],
    )


def summarize_sections(
    sections: list[SectionLike] | None,
    *,
    max_sentences_per_section: int = DEFAULT_SUMMARY_SENTENCE_LIMIT,
    max_words_per_section: int = DEFAULT_SUMMARY_WORD_LIMIT,
) -> list[SectionSummary]:
    if not sections:
        return []

    summaries: list[SectionSummary] = []
    for section in sections:
        summary = summarize_section(
            section,
            max_sentences=max_sentences_per_section,
            max_words=max_words_per_section,
        )
        if summary is not None:
            summaries.append(summary)
    return summaries


def _estimate_syllables(word: str) -> int:
    cleaned_word = re.sub(r"[^a-z]", "", word.lower())
    if not cleaned_word:
        return 0

    groups = VOWEL_GROUP_PATTERN.findall(cleaned_word)
    syllables = len(groups)
    if cleaned_word.endswith("e") and syllables > 1:
        syllables -= 1
    return max(syllables, 1)


def calculate_readability_metrics(text: str | None) -> ReadabilityMetrics:
    words = WORD_PATTERN.findall(text or "")
    sentences = _split_sentences(text)

    if not words or not sentences:
        return ReadabilityMetrics(
            sentence_count=len(sentences),
            average_words_per_sentence=0.0,
            average_syllables_per_word=0.0,
            flesch_reading_ease=None,
        )

    word_count = len(words)
    sentence_count = len(sentences)
    syllable_count = sum(_estimate_syllables(word) for word in words)
    average_words_per_sentence = round(word_count / sentence_count, 2)
    average_syllables_per_word = round(syllable_count / word_count, 2)
    flesch_reading_ease = round(
        206.835 - (1.015 * average_words_per_sentence) - (84.6 * average_syllables_per_word),
        2,
    )

    return ReadabilityMetrics(
        sentence_count=sentence_count,
        average_words_per_sentence=average_words_per_sentence,
        average_syllables_per_word=average_syllables_per_word,
        flesch_reading_ease=flesch_reading_ease,
    )


def build_document_statistics(
    text: str | None,
    *,
    sections: list[SectionLike] | None = None,
    chunks: list[ChunkLike] | None = None,
) -> DocumentStatistics:
    return DocumentStatistics(
        total_word_count=count_analysis_words(text),
        word_count_by_section=count_words_by_section(sections),
        chunk_count_by_section=count_chunks_by_section(chunks),
        reference_count_estimate=estimate_reference_count(text, sections=sections),
        readability=calculate_readability_metrics(text),
    )

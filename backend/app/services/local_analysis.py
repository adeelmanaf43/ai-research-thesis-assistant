import math
import re
from collections import Counter
from dataclasses import asdict, dataclass
from typing import Protocol

TOKEN_PATTERN = re.compile(r"\b[a-zA-Z][a-zA-Z-]{2,}\b")
WORD_PATTERN = re.compile(r"\b[a-zA-Z][a-zA-Z'-]*\b")
SENTENCE_PATTERN = re.compile(r"[^.!?]+[.!?]?")
DECIMAL_DOT_PLACEHOLDER = "<DOT>"
NUMBERED_HEADING_PREFIX_PATTERN = re.compile(
    r"^\s*\d+(?:\.\d+)+\s+.+?\b"
    r"((?:According|Although|Based|However|In|The|Thermal|This|These|Those|To|"
    r"Trans|A|An)\s+[a-z].*)$"
)
REFERENCE_ENTRY_PATTERN = re.compile(
    r"^\s*(?:\[\d+\]|\d+[\.)]|\w[\w'-]+,\s+(?:[A-Z]\.\s*)+|\w[\w'-]+\s+et\s+al\.)",
    re.IGNORECASE,
)
VOWEL_GROUP_PATTERN = re.compile(r"[aeiouy]+", re.IGNORECASE)
URL_PATTERN = re.compile(r"https?://\S+")
SUMMARY_SECTION_TYPES = {
    "abstract",
    "introduction",
    "literature_review",
    "methodology",
    "results",
    "discussion",
    "conclusion",
}
DEFAULT_SUMMARY_SENTENCE_LIMIT = 2
DEFAULT_SUMMARY_WORD_LIMIT = 90
RESEARCH_INFORMATION_FIELDS = (
    "research_problem",
    "objectives",
    "research_questions",
    "methodology",
    "dataset_sample",
    "variables",
    "findings",
    "limitations",
    "future_work",
)
RESEARCH_INFORMATION_RULES = {
    "research_problem": {
        "sections": {"abstract", "introduction", "unknown"},
        "keywords": (
            "problem",
            "challenge",
            "gap",
            "lack",
            "limited",
            "difficulty",
            "need",
            "issue",
        ),
    },
    "objectives": {
        "sections": {"abstract", "introduction", "methodology"},
        "keywords": (
            "objective",
            "objectives",
            "aim",
            "aims",
            "purpose",
            "goal",
            "seeks",
            "intends",
        ),
    },
    "research_questions": {
        "sections": {"abstract", "introduction", "methodology"},
        "keywords": (
            "research question",
            "rq",
            "question",
            "questions",
            "hypothesis",
            "hypotheses",
        ),
    },
    "methodology": {
        "sections": {"methodology", "methods"},
        "keywords": (
            "method",
            "methodology",
            "approach",
            "survey",
            "interview",
            "experiment",
            "regression",
            "qualitative",
            "quantitative",
            "mixed-method",
        ),
    },
    "dataset_sample": {
        "sections": {"methodology", "methods", "results"},
        "keywords": (
            "dataset",
            "data set",
            "sample",
            "participants",
            "respondents",
            "observations",
            "records",
            "cases",
        ),
    },
    "variables": {
        "sections": {"methodology", "methods", "results"},
        "keywords": (
            "variable",
            "variables",
            "dependent variable",
            "independent variable",
            "predictor",
            "outcome",
            "measure",
            "measures",
        ),
    },
    "findings": {
        "sections": {"results", "discussion", "conclusion"},
        "keywords": (
            "finding",
            "findings",
            "found",
            "results show",
            "results indicate",
            "showed",
            "revealed",
            "improved",
            "increase",
            "decrease",
        ),
    },
    "limitations": {
        "sections": {"discussion", "conclusion", "limitations"},
        "keywords": (
            "limitation",
            "limitations",
            "limited by",
            "constraint",
            "constraints",
            "threat",
            "bias",
        ),
    },
    "future_work": {
        "sections": {"discussion", "conclusion", "future_work"},
        "keywords": (
            "future work",
            "future research",
            "future studies",
            "further research",
            "should explore",
            "recommend",
            "recommendation",
        ),
    },
}

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


@dataclass(frozen=True)
class ResearchInfoItem:
    text: str
    source_section: str
    confidence: float
    matched_keywords: list[str]

    def to_dict(self) -> dict[str, str | float | list[str]]:
        return {
            "extracted_text": self.text,
            "source_section": self.source_section,
            "confidence": self.confidence,
            "matched_keywords": self.matched_keywords,
        }


@dataclass(frozen=True)
class ResearchInformationField:
    field: str
    extracted_text: str | None
    source_section: str | None
    confidence: float

    @classmethod
    def from_items(
        cls,
        field: str,
        items: list[ResearchInfoItem],
    ) -> "ResearchInformationField":
        if not items:
            return cls(
                field=field,
                extracted_text=None,
                source_section=None,
                confidence=0.0,
            )
        primary_item = items[0]
        return cls(
            field=field,
            extracted_text=primary_item.text,
            source_section=primary_item.source_section,
            confidence=primary_item.confidence,
        )

    def to_dict(self) -> dict[str, str | float | None]:
        return asdict(self)


@dataclass(frozen=True)
class ResearchInformation:
    research_problem: list[ResearchInfoItem]
    objectives: list[ResearchInfoItem]
    research_questions: list[ResearchInfoItem]
    methodology: list[ResearchInfoItem]
    dataset_sample: list[ResearchInfoItem]
    variables: list[ResearchInfoItem]
    findings: list[ResearchInfoItem]
    limitations: list[ResearchInfoItem]
    future_work: list[ResearchInfoItem]
    warnings: list[str]

    def to_dict(self) -> dict[str, dict[str, dict[str, str | float | None]] | list[str]]:
        fields = {
            field_name: ResearchInformationField.from_items(
                field_name,
                getattr(self, field_name),
            ).to_dict()
            for field_name in RESEARCH_INFORMATION_FIELDS
        }
        return {
            "fields": fields,
            "warnings": self.warnings,
        }


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
    protected_text = re.sub(r"(?<=\d)\.(?=\d)", DECIMAL_DOT_PLACEHOLDER, text)
    return [
        _clean_summary_sentence(sentence.replace(DECIMAL_DOT_PLACEHOLDER, "."))
        for sentence in SENTENCE_PATTERN.findall(protected_text)
        if count_analysis_words(sentence.replace(DECIMAL_DOT_PLACEHOLDER, ".")) > 0
    ]


def _clean_summary_sentence(sentence: str) -> str:
    cleaned = " ".join(URL_PATTERN.sub("", sentence).split())
    heading_match = NUMBERED_HEADING_PREFIX_PATTERN.match(cleaned)
    if heading_match:
        candidate = heading_match.group(1).strip()
        if count_analysis_words(candidate) >= 6:
            return candidate
    return cleaned


def _sentence_score(sentence: str, keyword_frequencies: Counter[str], index: int) -> float:
    tokens = tokenize_keywords(sentence)
    if not tokens:
        return 0.0

    frequency_score = sum(keyword_frequencies[token] for token in tokens)
    length_penalty = max(len(tokens), 1)
    position_bonus = 0.1 / (index + 1)
    return round((frequency_score / length_penalty) + position_bonus, 6)


def _is_summary_candidate(sentence: str) -> bool:
    if count_analysis_words(sentence) < 3:
        return False
    stripped = sentence.strip()
    lowered = stripped.lower()
    if stripped.startswith((",", ";", ":", ")", "]")):
        return False
    if "need to modify" in lowered or "modify it later" in lowered:
        return False
    if lowered.startswith(("figure ", "table ", "distribution of ", "appendix ")):
        return False
    if lowered.startswith("number of ") or "distribution of" in lowered:
        return False
    if "presented in figure" in lowered or re.search(r"\bfigure\s+x\b", lowered):
        return False
    if re.search(r"\b(?:doi|org|https?://|www\.)", stripped, re.IGNORECASE):
        return False
    if len(re.findall(r"\b\d+(?:\.\d+)+\s+[A-Z]", stripped)) >= 2:
        return False
    if stripped.count("\uf0b7") >= 2 or stripped.count("•") >= 2:
        return False
    if re.match(r"^\s*\d+(?:\.\d+)+\s+\S+(?:\s+\S+){0,5}\s*$", sentence):
        return False
    return True


def _fit_sentences_to_word_limit(
    scored_sentences: list[tuple[int, str, float]],
    max_words: int,
) -> list[tuple[int, str, float]]:
    selected: list[tuple[int, str, float]] = []
    current_word_count = 0
    for sentence_index, sentence, score in scored_sentences:
        if not _is_summary_candidate(sentence):
            continue
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


def _clean_research_unit(text: str) -> str:
    cleaned = re.sub(r"^\s*(?:[-*]|\d+[\.)]|[A-Z]{1,4}\d*[:.)])\s*", "", text)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" :-")
    return cleaned


def _research_candidate_units(text: str | None) -> list[str]:
    if not text:
        return []

    units: list[str] = []
    for line in text.splitlines():
        cleaned_line = _clean_research_unit(line)
        if count_analysis_words(cleaned_line) == 0:
            continue
        line_sentences = _split_sentences(cleaned_line)
        if len(line_sentences) > 1:
            units.extend(line_sentences)
            continue
        if len(cleaned_line) <= 180 and (
            ":" in cleaned_line
            or cleaned_line.endswith("?")
            or re.match(r"^(?:RQ|H)\d+", line.strip(), re.IGNORECASE)
        ):
            units.append(cleaned_line)
            continue
        units.extend(line_sentences)
    return [_clean_research_unit(unit) for unit in units if count_analysis_words(unit) > 0]


def _matched_research_keywords(candidate: str, keywords: tuple[str, ...]) -> list[str]:
    lowered_candidate = candidate.lower()
    matched_keywords = [
        keyword
        for keyword in keywords
        if re.search(rf"\b{re.escape(keyword)}\b", lowered_candidate)
    ]
    if "?" in candidate and "question" in keywords and "question" not in matched_keywords:
        matched_keywords.append("question")
    return matched_keywords


def _research_candidate_confidence(
    *,
    section_type: str,
    preferred_sections: set[str],
    matched_keywords: list[str],
    candidate: str,
) -> float:
    confidence = 0.35
    if section_type in preferred_sections:
        confidence += 0.25
    if matched_keywords:
        confidence += min(len(matched_keywords) * 0.1, 0.3)
    if ":" in candidate or "?" in candidate:
        confidence += 0.05
    return round(min(confidence, 0.95), 2)


def _dedupe_key(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _source_sections(
    text: str | None,
    sections: list[SectionLike] | None,
) -> list[tuple[str, str, str]]:
    if sections:
        return [
            (
                section.section_type.strip().lower() or "unknown",
                section.section_name.strip() or "Unknown",
                section.text,
            )
            for section in sections
            if section.text and section.text.strip()
        ]
    if text and text.strip():
        return [("unknown", "Full Document", text)]
    return []


def extract_research_information(
    text: str | None = None,
    *,
    sections: list[SectionLike] | None = None,
    max_items_per_field: int = 3,
) -> ResearchInformation:
    if max_items_per_field < 1:
        raise ValueError("Research information item limit must be a positive integer.")

    field_items: dict[str, list[ResearchInfoItem]] = {
        field_name: [] for field_name in RESEARCH_INFORMATION_FIELDS
    }
    seen_by_field: dict[str, set[str]] = {
        field_name: set() for field_name in RESEARCH_INFORMATION_FIELDS
    }
    warnings: list[str] = []
    source_sections = _source_sections(text, sections)

    if not source_sections:
        warnings.append("No text was available for research information extraction.")

    for section_type, section_name, section_text in source_sections:
        candidates = _research_candidate_units(section_text)
        for field_name, raw_rule in RESEARCH_INFORMATION_RULES.items():
            preferred_sections = set(raw_rule["sections"])
            keywords = tuple(raw_rule["keywords"])
            for candidate in candidates:
                matched_keywords = _matched_research_keywords(candidate, keywords)
                if not matched_keywords and section_type not in preferred_sections:
                    continue
                if not matched_keywords and field_name != "methodology":
                    continue

                dedupe_key = _dedupe_key(candidate)
                if dedupe_key in seen_by_field[field_name]:
                    continue
                seen_by_field[field_name].add(dedupe_key)
                field_items[field_name].append(
                    ResearchInfoItem(
                        text=candidate,
                        source_section=section_name,
                        confidence=_research_candidate_confidence(
                            section_type=section_type,
                            preferred_sections=preferred_sections,
                            matched_keywords=matched_keywords,
                            candidate=candidate,
                        ),
                        matched_keywords=matched_keywords,
                    )
                )

    for _field_name, items in field_items.items():
        items.sort(key=lambda item: (-item.confidence, item.source_section, item.text))
        del items[max_items_per_field:]

    if source_sections and not any(field_items.values()):
        warnings.append("No research information patterns were detected with local rules.")

    return ResearchInformation(
        research_problem=field_items["research_problem"],
        objectives=field_items["objectives"],
        research_questions=field_items["research_questions"],
        methodology=field_items["methodology"],
        dataset_sample=field_items["dataset_sample"],
        variables=field_items["variables"],
        findings=field_items["findings"],
        limitations=field_items["limitations"],
        future_work=field_items["future_work"],
        warnings=warnings,
    )


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

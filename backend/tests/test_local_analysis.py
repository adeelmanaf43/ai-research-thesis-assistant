import pytest

from backend.app.services.chunking import TextChunk
from backend.app.services.local_analysis import (
    DocumentStatistics,
    KeywordScore,
    ReadabilityMetrics,
    SectionSummary,
    build_document_statistics,
    calculate_readability_metrics,
    count_analysis_words,
    count_chunks_by_section,
    count_words_by_section,
    estimate_reference_count,
    extract_keywords,
    summarize_section,
    summarize_sections,
    tokenize_keywords,
)
from backend.app.services.section_detection import DetectedSection


def _section(section_type: str, section_name: str, text: str) -> DetectedSection:
    return DetectedSection(
        section_type=section_type,
        section_name=section_name,
        heading=section_name,
        detected_heading=section_name,
        text=text,
        start_index=0,
        end_index=len(text),
        confidence=1.0,
        start_line=0,
        end_line=1,
    )


def test_tokenize_keywords_filters_stopwords_short_words_and_normalizes_case() -> None:
    text = "The AI research method uses retrieval, Retrieval, and local-analysis in a PDF."

    tokens = tokenize_keywords(text)

    assert "the" not in tokens
    assert "and" not in tokens
    assert "uses" not in tokens
    assert "ai" not in tokens
    assert tokens == ["research", "method", "retrieval", "retrieval", "local-analysis", "pdf"]


def test_extract_keywords_returns_top_keywords_with_scores() -> None:
    text = (
        "retrieval retrieval retrieval chunking chunking " "summary evidence evidence local thesis"
    )

    keywords = extract_keywords(text, top_n=3)

    assert [keyword.keyword for keyword in keywords] == [
        "retrieval",
        "chunking",
        "evidence",
    ]
    assert [keyword.frequency for keyword in keywords] == [3, 2, 2]
    assert keywords[0].score > keywords[1].score
    assert keywords[1].score == keywords[2].score


def test_extract_keywords_uses_stable_alphabetical_tie_breaking() -> None:
    text = "zeta zeta alpha alpha beta beta"

    keywords = extract_keywords(text, top_n=3)

    assert [keyword.keyword for keyword in keywords] == ["alpha", "beta", "zeta"]


def test_extract_keywords_returns_empty_list_for_blank_or_stopword_only_text() -> None:
    assert extract_keywords("") == []
    assert extract_keywords(None) == []
    assert extract_keywords("the and for with this section paper") == []


def test_extract_keywords_respects_top_n_limit() -> None:
    text = "retrieval chunking evidence methodology thesis matrix"

    keywords = extract_keywords(text, top_n=2)

    assert len(keywords) == 2


def test_keyword_score_serializes_to_plain_dictionary() -> None:
    keyword = KeywordScore(keyword="retrieval", score=0.75, frequency=4)

    assert keyword.to_dict() == {
        "keyword": "retrieval",
        "score": 0.75,
        "frequency": 4,
    }


def test_extract_keywords_rejects_invalid_limits() -> None:
    with pytest.raises(ValueError, match="Keyword limit"):
        extract_keywords("retrieval", top_n=0)


def test_tokenize_keywords_rejects_invalid_minimum_word_length() -> None:
    with pytest.raises(ValueError, match="Minimum word length"):
        tokenize_keywords("retrieval", min_word_length=0)


def test_count_analysis_words_handles_empty_and_apostrophe_words() -> None:
    assert count_analysis_words("") == 0
    assert count_analysis_words(None) == 0
    assert count_analysis_words("Researcher's local-first method works.") == 4


def test_count_words_by_section_groups_duplicate_section_names() -> None:
    sections = [
        _section("introduction", "Introduction", "Local analysis improves search."),
        _section("introduction", "Introduction", "Students review source evidence."),
        _section("methodology", "Methodology", "Chunks support retrieval."),
    ]

    counts = count_words_by_section(sections)

    assert counts == {
        "Introduction": 8,
        "Methodology": 3,
    }


def test_count_chunks_by_section_groups_unknown_and_named_chunks() -> None:
    chunks = [
        TextChunk(0, "Introduction", 1, 1, "intro text", 2),
        TextChunk(1, "Introduction", 1, 2, "more intro", 2),
        TextChunk(2, "", 2, 2, "unknown text", 2),
        TextChunk(3, None, 2, 3, "unknown text", 2),
    ]

    counts = count_chunks_by_section(chunks)

    assert counts == {
        "Introduction": 2,
        "Unknown": 2,
    }


def test_estimate_reference_count_prefers_references_section_entries() -> None:
    sections = [
        _section(
            "references",
            "References",
            "[1] Smith, J. Local retrieval.\n"
            "2. Khan, A. Thesis workflows.\n"
            "Brown et al. Research tooling.",
        )
    ]

    assert estimate_reference_count("No inline references here.", sections=sections) == 3


def test_estimate_reference_count_falls_back_to_inline_citations() -> None:
    text = "Retrieval matters (Smith, 2023). Cleaning matters (Khan, 2024)."

    assert estimate_reference_count(text) == 2


def test_calculate_readability_metrics_returns_simple_local_metrics() -> None:
    metrics = calculate_readability_metrics("Local tools help students. Research improves.")

    assert metrics.sentence_count == 2
    assert metrics.average_words_per_sentence == 3.0
    assert metrics.average_syllables_per_word > 0
    assert metrics.flesch_reading_ease is not None


def test_calculate_readability_metrics_handles_empty_text() -> None:
    metrics = calculate_readability_metrics("")

    assert metrics == ReadabilityMetrics(
        sentence_count=0,
        average_words_per_sentence=0.0,
        average_syllables_per_word=0.0,
        flesch_reading_ease=None,
    )


def test_build_document_statistics_combines_counts_references_and_readability() -> None:
    text = (
        "Introduction\n"
        "Local analysis improves retrieval.\n"
        "References\n"
        "[1] Smith, J. Local retrieval."
    )
    sections = [
        _section("introduction", "Introduction", "Local analysis improves retrieval."),
        _section("references", "References", "[1] Smith, J. Local retrieval."),
    ]
    chunks = [
        TextChunk(0, "Introduction", 1, 1, "Local analysis improves retrieval.", 4),
        TextChunk(1, "References", 1, 1, "[1] Smith, J. Local retrieval.", 4),
    ]

    statistics = build_document_statistics(text, sections=sections, chunks=chunks)

    assert isinstance(statistics, DocumentStatistics)
    assert statistics.total_word_count == 10
    assert statistics.word_count_by_section == {
        "Introduction": 4,
        "References": 4,
    }
    assert statistics.chunk_count_by_section == {
        "Introduction": 1,
        "References": 1,
    }
    assert statistics.reference_count_estimate == 1
    assert statistics.readability.sentence_count >= 1
    assert statistics.to_dict()["readability"]["sentence_count"] >= 1


def test_summarize_section_selects_high_scoring_sentences_concisely() -> None:
    section = _section(
        "results",
        "Results",
        "The baseline was simple. "
        "Retrieval accuracy improved when retrieval chunks used clean evidence. "
        "Students reported faster thesis review with retrieval evidence. "
        "A minor formatting issue remained.",
    )

    summary = summarize_section(section, max_sentences=2, max_words=25)

    assert isinstance(summary, SectionSummary)
    assert summary.section_type == "results"
    assert summary.section_name == "Results"
    assert summary.selected_sentence_count == 2
    assert "Retrieval accuracy improved" in summary.summary
    assert "Students reported faster thesis review" in summary.summary
    assert "A minor formatting issue remained" not in summary.summary
    assert summary.source_sentence_indexes == [1, 2]
    assert count_analysis_words(summary.summary) <= 25


def test_summarize_section_never_exceeds_word_limit() -> None:
    section = _section(
        "discussion",
        "Discussion",
        "Retrieval retrieval retrieval retrieval retrieval retrieval retrieval "
        "retrieval retrieval retrieval retrieval evidence sentence is too long. "
        "Clean chunks helped students. "
        "Source evidence improved review.",
    )

    summary = summarize_section(section, max_sentences=2, max_words=8)

    assert summary is not None
    assert summary.selected_sentence_count == 2
    assert "too long" not in summary.summary
    assert summary.summary == "Clean chunks helped students. Source evidence improved review."
    assert summary.source_sentence_indexes == [1, 2]
    assert count_analysis_words(summary.summary) <= 8


def test_summarize_section_returns_empty_when_no_sentence_fits_word_limit() -> None:
    section = _section(
        "discussion",
        "Discussion",
        "Every available discussion sentence is deliberately longer than the limit. "
        "Another sentence also contains too many words for the configured summary limit.",
    )

    summary = summarize_section(section, max_sentences=2, max_words=3)

    assert summary == SectionSummary(
        section_type="discussion",
        section_name="Discussion",
        summary="",
        selected_sentence_count=0,
        source_sentence_indexes=[],
    )


def test_summarize_section_returns_none_for_unsupported_sections() -> None:
    section = _section(
        "references",
        "References",
        "Smith, J. Local retrieval. Khan, A. Thesis workflows.",
    )

    assert summarize_section(section) is None


def test_summarize_section_handles_empty_supported_section() -> None:
    section = _section("abstract", "Abstract", "   ")

    summary = summarize_section(section)

    assert summary == SectionSummary(
        section_type="abstract",
        section_name="Abstract",
        summary="",
        selected_sentence_count=0,
        source_sentence_indexes=[],
    )


def test_summarize_section_handles_punctuation_only_supported_section() -> None:
    section = _section("conclusion", "Conclusion", "!!! ... ???")

    summary = summarize_section(section)

    assert summary == SectionSummary(
        section_type="conclusion",
        section_name="Conclusion",
        summary="",
        selected_sentence_count=0,
        source_sentence_indexes=[],
    )


def test_summarize_sections_keeps_only_supported_academic_sections_in_order() -> None:
    sections = [
        _section("title", "Title", "Local Thesis Assistant"),
        _section("abstract", "Abstract", "This study evaluates local retrieval. It is useful."),
        _section("methodology", "Methodology", "We cleaned PDFs. We chunked sections."),
        _section("references", "References", "[1] Smith, J."),
    ]

    summaries = summarize_sections(sections, max_sentences_per_section=1)

    assert [summary.section_type for summary in summaries] == ["abstract", "methodology"]
    assert [summary.section_name for summary in summaries] == ["Abstract", "Methodology"]
    assert all(summary.selected_sentence_count == 1 for summary in summaries)


def test_summarize_sections_returns_section_specific_outputs() -> None:
    sections = [
        _section(
            "abstract",
            "Abstract",
            "This study evaluates local retrieval. "
            "The abstract highlights document intelligence.",
        ),
        _section(
            "methodology",
            "Methodology",
            "We cleaned extracted PDF text. " "The methodology uses chunk overlap.",
        ),
        _section(
            "conclusion",
            "Conclusion",
            "The assistant supports thesis review. "
            "The conclusion recommends local-first analysis.",
        ),
    ]

    summaries = summarize_sections(
        sections,
        max_sentences_per_section=1,
        max_words_per_section=9,
    )

    summaries_by_section = {summary.section_name: summary.summary for summary in summaries}
    assert summaries_by_section["Abstract"] in {
        "This study evaluates local retrieval.",
        "The abstract highlights document intelligence.",
    }
    assert summaries_by_section["Methodology"] in {
        "We cleaned extracted PDF text.",
        "The methodology uses chunk overlap.",
    }
    assert summaries_by_section["Conclusion"] in {
        "The assistant supports thesis review.",
        "The conclusion recommends local-first analysis.",
    }
    assert len(set(summaries_by_section.values())) == 3


def test_summarize_sections_returns_empty_list_for_empty_input() -> None:
    assert summarize_sections([]) == []
    assert summarize_sections(None) == []


def test_summarize_section_rejects_invalid_limits() -> None:
    section = _section("abstract", "Abstract", "Local retrieval works.")

    with pytest.raises(ValueError, match="sentence limit"):
        summarize_section(section, max_sentences=0)

    with pytest.raises(ValueError, match="word limit"):
        summarize_section(section, max_words=0)

import pytest

from backend.app.services.chunking import TextChunk
from backend.app.services.local_analysis import (
    DocumentStatistics,
    KeywordScore,
    ReadabilityMetrics,
    ResearchInfoItem,
    ResearchInformation,
    ResearchInformationField,
    SectionSummary,
    build_document_statistics,
    calculate_readability_metrics,
    count_analysis_words,
    count_chunks_by_section,
    count_words_by_section,
    estimate_reference_count,
    extract_keywords,
    extract_research_information,
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


def test_summarize_section_skips_numbered_heading_fragments() -> None:
    section = _section(
        "discussion",
        "Discussion",
        "2.1.3 Fatty Acid Nomenclature. "
        "2.2 Classification of Fatty Acids. "
        "The discussion explains that fatty acids differ by molecular structure. "
        "The review connects these differences to food product analysis.",
    )

    summary = summarize_section(section, max_sentences=2, max_words=30)

    assert summary is not None
    assert "2.1.3" not in summary.summary
    assert "Classification of Fatty Acids" not in summary.summary
    assert "fatty acids differ" in summary.summary


def test_summarize_section_trims_numbered_heading_prefix_from_sentence() -> None:
    section = _section(
        "discussion",
        "Discussion",
        "2.12.2 European Union Regulation on Trans Fatty Acids "
        "In the European Union, industrially produced trans fatty acids "
        "are regulated by quantitative restrictions. "
        "The review links this policy context to food product analysis.",
    )

    summary = summarize_section(section, max_sentences=1, max_words=30)

    assert summary is not None
    assert summary.summary.startswith("In the European Union")
    assert "2.12.2" not in summary.summary


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


def test_extract_research_information_finds_requested_fields_from_sections() -> None:
    sections = [
        _section(
            "introduction",
            "Introduction",
            "The problem is that thesis writers lack source-grounded review tools. "
            "The objective is to evaluate a local document assistant. "
            "RQ1: How does local retrieval affect thesis review?",
        ),
        _section(
            "methodology",
            "Methodology",
            "The methodology used a mixed-method survey and interview approach. "
            "The sample included 48 graduate students and 12 academic freelancers. "
            "Variables included review time, citation accuracy, and confidence.",
        ),
        _section(
            "results",
            "Results",
            "The findings revealed that retrieval improved citation accuracy. "
            "Results show that students completed reviews faster.",
        ),
        _section(
            "discussion",
            "Discussion",
            "The limitation is that the sample came from one university. "
            "Future work should explore larger datasets and more disciplines.",
        ),
    ]

    extraction = extract_research_information(sections=sections)

    assert isinstance(extraction, ResearchInformation)
    assert "lack source-grounded review tools" in extraction.research_problem[0].text
    assert "evaluate a local document assistant" in extraction.objectives[0].text
    assert extraction.research_questions[0].text == (
        "How does local retrieval affect thesis review?"
    )
    assert extraction.research_questions[0].source_section == "Introduction"
    assert "mixed-method survey" in extraction.methodology[0].text
    assert "48 graduate students" in extraction.dataset_sample[0].text
    assert "review time" in extraction.variables[0].text
    assert "retrieval improved citation accuracy" in extraction.findings[0].text
    assert "one university" in extraction.limitations[0].text
    assert "larger datasets" in extraction.future_work[0].text
    assert extraction.warnings == []
    assert extraction.findings[0].confidence >= 0.7
    assert "findings" in extraction.findings[0].matched_keywords

    payload = extraction.to_dict()
    assert set(payload["fields"]) == {
        "research_problem",
        "objectives",
        "research_questions",
        "methodology",
        "dataset_sample",
        "variables",
        "findings",
        "limitations",
        "future_work",
    }
    assert payload["fields"]["research_problem"]["field"] == "research_problem"
    assert (
        payload["fields"]["research_problem"]["extracted_text"]
        == extraction.research_problem[0].text
    )
    assert payload["fields"]["research_problem"]["source_section"] == "Introduction"
    assert payload["fields"]["research_problem"]["confidence"] >= 0.7
    assert payload["warnings"] == []


def test_extract_research_information_from_academic_sample_text() -> None:
    sections = [
        _section(
            "abstract",
            "Abstract",
            "The objective is to examine whether local document intelligence "
            "supports thesis writers during literature review. The study also "
            "measures changes in review speed and citation confidence.",
        ),
        _section(
            "methodology",
            "Methodology",
            "A quantitative survey method was used for the study. The sample "
            "included 120 postgraduate students from three public universities. "
            "The independent variable was assistant usage, and the dependent "
            "variable was literature review quality.",
        ),
        _section(
            "results",
            "Findings",
            "Results indicate that students using the assistant completed "
            "reviews faster and improved citation confidence. The findings also "
            "showed stronger source tracking.",
        ),
        _section(
            "discussion",
            "Limitations",
            "The main limitation is that the sample was limited to public "
            "universities. Future research should explore doctoral students and "
            "cross-discipline research workflows.",
        ),
    ]

    extraction = extract_research_information(sections=sections)
    fields = extraction.to_dict()["fields"]

    assert "supports thesis writers" in fields["objectives"]["extracted_text"]
    assert fields["objectives"]["source_section"] == "Abstract"
    assert "quantitative survey method" in fields["methodology"]["extracted_text"]
    assert fields["methodology"]["source_section"] == "Methodology"
    assert "120 postgraduate students" in fields["dataset_sample"]["extracted_text"]
    assert "independent variable" in fields["variables"]["extracted_text"]
    assert "completed reviews faster" in fields["findings"]["extracted_text"]
    assert "sample was limited" in fields["limitations"]["extracted_text"]
    assert "doctoral students" in fields["future_work"]["extracted_text"]
    assert all(
        fields[field_name]["confidence"] > 0
        for field_name in (
            "objectives",
            "methodology",
            "dataset_sample",
            "variables",
            "findings",
            "limitations",
        )
    )


def test_extract_research_information_works_with_plain_text() -> None:
    text = (
        "This study aims to test local analysis. "
        "Research question: Can local tools help thesis writers? "
        "The dataset contains 120 document chunks. "
        "The dependent variable is answer accuracy."
    )

    extraction = extract_research_information(text)

    assert extraction.objectives[0].source_section == "Full Document"
    assert "aims to test local analysis" in extraction.objectives[0].text
    assert "Can local tools help thesis writers?" in extraction.research_questions[0].text
    assert "120 document chunks" in extraction.dataset_sample[0].text
    assert "dependent variable" in extraction.variables[0].text


def test_extract_research_information_handles_empty_input_with_warning() -> None:
    extraction = extract_research_information("")

    assert extraction == ResearchInformation(
        research_problem=[],
        objectives=[],
        research_questions=[],
        methodology=[],
        dataset_sample=[],
        variables=[],
        findings=[],
        limitations=[],
        future_work=[],
        warnings=["No text was available for research information extraction."],
    )


def test_extract_research_information_warns_when_no_patterns_match() -> None:
    extraction = extract_research_information("Plain background text without target signals.")

    assert extraction.warnings == [
        "No research information patterns were detected with local rules."
    ]
    fields = extraction.to_dict()["fields"]
    assert fields["findings"] == {
        "field": "findings",
        "extracted_text": None,
        "source_section": None,
        "confidence": 0.0,
    }
    assert fields["future_work"]["extracted_text"] is None


def test_extract_research_information_deduplicates_and_respects_item_limit() -> None:
    sections = [
        _section(
            "results",
            "Results",
            "The findings revealed faster reviews. "
            "The findings revealed faster reviews. "
            "Results show better citation checks. "
            "Results indicate stronger source coverage.",
        )
    ]

    extraction = extract_research_information(sections=sections, max_items_per_field=2)

    assert len(extraction.findings) == 2
    assert len({item.text for item in extraction.findings}) == 2
    assert all(isinstance(item, ResearchInfoItem) for item in extraction.findings)


def test_extract_research_information_rejects_invalid_item_limit() -> None:
    with pytest.raises(ValueError, match="item limit"):
        extract_research_information("The objective is local analysis.", max_items_per_field=0)


def test_research_information_field_uses_unknown_values_when_missing() -> None:
    field = ResearchInformationField.from_items("limitations", [])

    assert field == ResearchInformationField(
        field="limitations",
        extracted_text=None,
        source_section=None,
        confidence=0.0,
    )
    assert field.to_dict() == {
        "field": "limitations",
        "extracted_text": None,
        "source_section": None,
        "confidence": 0.0,
    }


def test_research_info_item_serializes_with_extracted_text_key() -> None:
    item = ResearchInfoItem(
        text="The objective is to evaluate local extraction.",
        source_section="Introduction",
        confidence=0.8,
        matched_keywords=["objective"],
    )

    assert item.to_dict() == {
        "extracted_text": "The objective is to evaluate local extraction.",
        "source_section": "Introduction",
        "confidence": 0.8,
        "matched_keywords": ["objective"],
    }

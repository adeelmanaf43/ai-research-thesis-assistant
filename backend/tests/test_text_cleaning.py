import pytest

from backend.app.services.text_cleaning import (
    EMPTY_CLEANED_TEXT_WARNING,
    EMPTY_INPUT_WARNING,
    LARGE_TEXT_REDUCTION_WARNING,
    TextCleaningResult,
    build_cleaning_warnings,
    calculate_cleaning_statistics,
    clean_text,
    fix_broken_lines,
    normalize_whitespace,
    remove_control_characters,
    remove_repeated_page_artifacts,
    repair_hyphenated_line_breaks,
    run_text_cleaning_pipeline,
)


def test_remove_control_characters_keeps_readable_text() -> None:
    text = "Intro\x00duction\x08 text\nNext line\twith tab"

    cleaned = remove_control_characters(text)

    assert cleaned == "Introduction text\nNext line\twith tab"


def test_repair_hyphenated_line_breaks_rejoins_split_words() -> None:
    text = "The method improves docu-\nment retrieval and sum-\n marization."

    cleaned = repair_hyphenated_line_breaks(text)

    assert cleaned == "The method improves document retrieval and summarization."


def test_normalize_whitespace_collapses_spaces_and_blank_lines() -> None:
    text = "  First   line  \r\n\r\n\r\n  Second\t\tline  "

    cleaned = normalize_whitespace(text)

    assert cleaned == "First line\n\nSecond line"


def test_fix_broken_lines_joins_paragraph_lines_but_preserves_headings() -> None:
    text = (
        "Introduction\n"
        "This section describes the local processing\n"
        "pipeline for research documents\n\n"
        "1. First item\n"
        "2. Second item"
    )

    cleaned = fix_broken_lines(text)

    assert "Introduction\nThis section describes the local processing pipeline" in cleaned
    assert "1. First item\n2. Second item" in cleaned


def test_remove_repeated_page_artifacts_removes_safe_repeated_headers_and_numbers() -> None:
    text = (
        "Research Draft\n"
        "1\n"
        "Useful paragraph one.\n\n"
        "Research Draft\n"
        "2\n"
        "Useful paragraph two.\n\n"
        "Research Draft\n"
        "3\n"
        "Useful paragraph three."
    )

    cleaned = remove_repeated_page_artifacts(text)

    assert "Research Draft" not in cleaned
    assert "\n1\n" not in f"\n{cleaned}\n"
    assert "Useful paragraph one." in cleaned
    assert "Useful paragraph two." in cleaned
    assert "Useful paragraph three." in cleaned


def test_remove_repeated_page_artifacts_keeps_repeated_sentence_content() -> None:
    repeated_sentence = "This finding was statistically significant."
    text = "\n".join([repeated_sentence, repeated_sentence, repeated_sentence])

    cleaned = remove_repeated_page_artifacts(text)

    assert cleaned == text


def test_remove_repeated_page_artifacts_rejects_invalid_threshold() -> None:
    with pytest.raises(ValueError, match="min_repetitions must be at least 2"):
        remove_repeated_page_artifacts("text", min_repetitions=1)


def test_clean_text_runs_full_local_cleaning_pipeline() -> None:
    text = (
        "Journal Header\x00\n"
        "1\n"
        "This paper intro-\n"
        "duces a local-first\n"
        "document assistant.\n\n"
        "Journal Header\n"
        "2\n"
        "It removes noisy   spacing."
        "\n\n"
        "Journal Header\n"
        "3\n"
        "Final line."
    )

    cleaned = clean_text(text)

    assert "Journal Header" not in cleaned
    assert "introduces a local-first document assistant." in cleaned
    assert "noisy spacing." in cleaned
    assert "\x00" not in cleaned


def test_calculate_cleaning_statistics_reports_before_and_after_counts() -> None:
    original_text = "Header\n1\nUseful text with extra spacing."
    cleaned_text = "Useful text with extra spacing."

    statistics = calculate_cleaning_statistics(original_text, cleaned_text)

    assert statistics.original_character_count == len(original_text)
    assert statistics.cleaned_character_count == len(cleaned_text)
    assert statistics.removed_character_count == len(original_text) - len(cleaned_text)
    assert statistics.original_word_count == 7
    assert statistics.cleaned_word_count == 5
    assert statistics.original_line_count == 3
    assert statistics.cleaned_line_count == 1


def test_build_cleaning_warnings_reports_empty_input() -> None:
    statistics = calculate_cleaning_statistics("", "")

    warnings = build_cleaning_warnings("", "", statistics)

    assert warnings == [EMPTY_INPUT_WARNING]


def test_build_cleaning_warnings_reports_empty_cleaned_text() -> None:
    original_text = "Header\n1\nHeader\n2\nHeader\n3"
    cleaned_text = ""
    statistics = calculate_cleaning_statistics(original_text, cleaned_text)

    warnings = build_cleaning_warnings(original_text, cleaned_text, statistics)

    assert EMPTY_CLEANED_TEXT_WARNING in warnings
    assert LARGE_TEXT_REDUCTION_WARNING in warnings


def test_run_text_cleaning_pipeline_returns_original_cleaned_stats_and_warnings() -> None:
    text = (
        "Header\n"
        "1\n"
        "The docu-\n"
        "ment has noisy   text.\n"
        "Header\n"
        "2\n"
        "Final line.\n"
        "Header\n"
        "3"
    )

    result = run_text_cleaning_pipeline(text)

    assert isinstance(result, TextCleaningResult)
    assert result.original_text == text
    assert result.cleaned_text == "The document has noisy text.\nFinal line."
    assert result.statistics.original_character_count == len(text)
    assert result.statistics.cleaned_character_count == len(result.cleaned_text)
    assert result.statistics.cleaned_word_count == 7
    assert result.warnings == []


def test_run_text_cleaning_pipeline_handles_none_without_crashing() -> None:
    result = run_text_cleaning_pipeline(None)

    assert result.original_text == ""
    assert result.cleaned_text == ""
    assert result.statistics.original_character_count == 0
    assert result.statistics.cleaned_word_count == 0
    assert result.warnings == [EMPTY_INPUT_WARNING]


def test_clean_text_handles_common_academic_pdf_header_page_numbers_and_line_wraps() -> None:
    text = (
        "Journal of Local Research\n"
        "Page 1 of 3\n"
        "Abstract\n"
        "This study evaluates document intelligence\n"
        "systems for students and thesis writers.\n\n"
        "Journal of Local Research\n"
        "Page 2 of 3\n"
        "The method uses local extraction and deter-\n"
        "ministic cleaning before chunking.\n\n"
        "Journal of Local Research\n"
        "Page 3 of 3\n"
        "Results show fewer broken lines."
    )

    cleaned = clean_text(text)

    assert "Journal of Local Research" not in cleaned
    assert "Page 1 of 3" not in cleaned
    assert "Abstract\nThis study evaluates document intelligence systems" in cleaned
    assert "deterministic cleaning before chunking." in cleaned
    assert "Results show fewer broken lines." in cleaned


def test_clean_text_removes_control_symbols_but_preserves_academic_punctuation() -> None:
    text = (
        "Figure 1\x00 shows 95% confidence intervals.\n"
        "The p-value was < 0.05; however, results were not causal.\x0c"
    )

    cleaned = clean_text(text)

    assert "\x00" not in cleaned
    assert "\x0c" not in cleaned
    assert "95% confidence intervals." in cleaned
    assert "p-value was < 0.05; however" in cleaned


def test_clean_text_preserves_repeated_academic_sentence_content() -> None:
    repeated_finding = "The null hypothesis was rejected."
    text = (
        "Working Paper\n"
        "1\n"
        f"{repeated_finding}\n\n"
        "Working Paper\n"
        "2\n"
        f"{repeated_finding}\n\n"
        "Working Paper\n"
        "3\n"
        f"{repeated_finding}"
    )

    cleaned = clean_text(text)

    assert "Working Paper" not in cleaned
    assert cleaned.count(repeated_finding) == 3


def test_run_text_cleaning_pipeline_reports_statistics_for_academic_pdf_noise() -> None:
    text = (
        "Thesis Draft\n"
        "1\n"
        "The litera-\n"
        "ture review contains   extra spaces.\n"
        "Thesis Draft\n"
        "2\n"
        "The conclusion remains readable.\n"
        "Thesis Draft\n"
        "3"
    )

    result = run_text_cleaning_pipeline(text)

    assert result.cleaned_text == (
        "The literature review contains extra spaces.\n" "The conclusion remains readable."
    )
    assert result.statistics.cleaned_character_count < result.statistics.original_character_count
    assert result.statistics.cleaned_word_count == 10
    assert result.warnings == []

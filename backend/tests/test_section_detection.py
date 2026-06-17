from backend.app.services.section_detection import classify_heading, detect_sections


def test_classify_heading_detects_academic_section_aliases() -> None:
    assert classify_heading("Abstract") == "abstract"
    assert classify_heading("1. Introduction") == "introduction"
    assert classify_heading("2 Literature Review") == "literature_review"
    assert classify_heading("3. Materials and Methods") == "methodology"
    assert classify_heading("4) Findings") == "results"
    assert classify_heading("4.1 Results of Phase I") == "results"
    assert classify_heading("4.2.2 Dataset Overview and Availability") == "results"
    assert classify_heading("Discussion") == "discussion"
    assert classify_heading("5.7 Data Availability and Database Limitations") == "discussion"
    assert classify_heading("Concluding Remarks") == "conclusion"
    assert classify_heading("6.1 Policy Implications") == "conclusion"
    assert classify_heading("Works Cited") == "references"
    assert classify_heading("References (OF LITERATURE REVIEW)") == "references"
    assert classify_heading("A normal sentence with punctuation.") is None


def test_detect_sections_finds_title_and_common_academic_sections() -> None:
    text = """Local-First Thesis Assistant

Abstract
This paper studies local document processing.

1. Introduction
The introduction explains the research problem.

2. Literature Review
Prior studies are summarized here.

3. Methodology
The method is rule based and local.

4. Results
The system detects sections.

5. Discussion
The discussion explains implications.

6. Conclusion
The conclusion closes the paper.

References
Smith, J. Local Research.
"""

    sections = detect_sections(text)
    section_types = [section.section_type for section in sections]

    assert section_types == [
        "title",
        "abstract",
        "introduction",
        "literature_review",
        "methodology",
        "results",
        "discussion",
        "conclusion",
        "references",
    ]
    assert sections[0].heading == "Title"
    assert sections[0].section_name == "Title"
    assert sections[0].detected_heading == "Title"
    assert sections[0].confidence == 0.75
    assert sections[0].text == "Local-First Thesis Assistant"
    assert "local document processing" in sections[1].text
    assert sections[1].section_name == "Abstract"
    assert sections[1].detected_heading == "Abstract"
    assert sections[1].confidence == 0.95
    assert "Prior studies" in sections[3].text
    assert "Smith" in sections[-1].text


def test_detect_sections_returns_unknown_for_unstructured_text() -> None:
    text = "This paragraph has no reliable academic headings. It should remain unknown."

    sections = detect_sections(text)

    assert len(sections) == 1
    assert sections[0].section_type == "unknown"
    assert sections[0].section_name == "Unknown"
    assert sections[0].heading == "Unknown"
    assert sections[0].detected_heading == "Unknown"
    assert sections[0].text == text
    assert sections[0].start_index == 0
    assert sections[0].end_index == len(text)
    assert sections[0].confidence == 0.0


def test_detect_sections_handles_empty_text_without_crashing() -> None:
    sections = detect_sections("   ")

    assert len(sections) == 1
    assert sections[0].section_type == "unknown"
    assert sections[0].text == ""
    assert sections[0].start_index == 0
    assert sections[0].end_index == 0
    assert sections[0].confidence == 0.0


def test_detect_sections_keeps_unknown_heading_text_inside_current_section() -> None:
    text = """Research System Evaluation

Introduction
This is the introduction.

Threats to Validity
This heading is not part of the current supported taxonomy.

Conclusion
Final remarks.
"""

    sections = detect_sections(text)

    assert [section.section_type for section in sections] == [
        "title",
        "introduction",
        "conclusion",
    ]
    assert "Threats to Validity" in sections[1].text
    assert "Final remarks." in sections[2].text


def test_detect_sections_returns_character_indexes_for_detected_sections() -> None:
    text = """Research Title

Abstract
Short abstract.

Introduction
Opening context.
"""

    sections = detect_sections(text)
    abstract = sections[1]
    introduction = sections[2]

    assert text[abstract.start_index : abstract.end_index].startswith("Abstract")
    assert "Short abstract." in text[abstract.start_index : abstract.end_index]
    assert text[introduction.start_index : introduction.end_index].startswith("Introduction")
    assert "Opening context." in text[introduction.start_index : introduction.end_index]
    assert abstract.end_index < introduction.start_index


def test_detect_sections_handles_capitalization_and_numbering_formats() -> None:
    text = """A LOCAL STUDY OF THESIS WORKFLOWS

ABSTRACT
This abstract is written under an uppercase heading.

1 INTRODUCTION
The introduction heading uses a number without a dot.

2.1 RELATED WORK
This section uses nested decimal numbering and uppercase text.

3) RESEARCH METHODOLOGY
This methodology heading uses a closing parenthesis.

4. FINDINGS
The findings heading should map to results.

5 Discussion
This heading mixes a number with title case.

6.1 CONCLUSIONS
The conclusion heading uses plural uppercase wording.

BIBLIOGRAPHY
The references section uses an academic alias.
"""

    sections = detect_sections(text)

    assert [section.section_type for section in sections] == [
        "title",
        "abstract",
        "introduction",
        "literature_review",
        "methodology",
        "results",
        "discussion",
        "conclusion",
        "references",
    ]
    assert sections[1].detected_heading == "ABSTRACT"
    assert sections[2].detected_heading == "1 INTRODUCTION"
    assert sections[3].detected_heading == "2.1 RELATED WORK"
    assert sections[4].detected_heading == "3) RESEARCH METHODOLOGY"
    assert sections[5].detected_heading == "4. FINDINGS"
    assert sections[-1].detected_heading == "BIBLIOGRAPHY"
    assert "nested decimal numbering" in sections[3].text
    assert "academic alias" in sections[-1].text

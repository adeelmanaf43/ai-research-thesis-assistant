import re
from dataclasses import dataclass

CONTROL_CHARACTER_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
HYPHENATED_LINE_BREAK_PATTERN = re.compile(r"(?<=\w)-\s*\n\s*(?=\w)")
MULTIPLE_SPACES_PATTERN = re.compile(r"[ \t]+")
MULTIPLE_BLANK_LINES_PATTERN = re.compile(r"\n{3,}")
PAGE_NUMBER_PATTERN = re.compile(r"^(?:page\s*)?\d+(?:\s*(?:of|/)\s*\d+)?$", re.IGNORECASE)
WORD_PATTERN = re.compile(r"\b\w+\b")

EMPTY_INPUT_WARNING = "Input text is empty."
EMPTY_CLEANED_TEXT_WARNING = "Cleaned text is empty after removing extraction noise."
LARGE_TEXT_REDUCTION_WARNING = "Cleaning removed more than half of the original characters."
ACADEMIC_HEADINGS = {
    "abstract",
    "summary",
    "introduction",
    "background",
    "literature review",
    "review of literature",
    "related work",
    "previous studies",
    "methodology",
    "methods",
    "method",
    "materials and methods",
    "research methodology",
    "results",
    "findings",
    "discussion",
    "analysis",
    "conclusion",
    "conclusions",
    "concluding remarks",
    "references",
    "bibliography",
    "works cited",
}


@dataclass(frozen=True)
class CleaningStatistics:
    original_character_count: int
    cleaned_character_count: int
    removed_character_count: int
    original_word_count: int
    cleaned_word_count: int
    original_line_count: int
    cleaned_line_count: int


@dataclass(frozen=True)
class TextCleaningResult:
    original_text: str
    cleaned_text: str
    statistics: CleaningStatistics
    warnings: list[str]


def remove_control_characters(text: str | None) -> str:
    if not text:
        return ""
    return CONTROL_CHARACTER_PATTERN.sub("", text)


def repair_hyphenated_line_breaks(text: str | None) -> str:
    if not text:
        return ""
    return HYPHENATED_LINE_BREAK_PATTERN.sub("", text)


def normalize_whitespace(text: str | None) -> str:
    if not text:
        return ""

    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    normalized = "\n".join(
        MULTIPLE_SPACES_PATTERN.sub(" ", line).strip() for line in normalized.split("\n")
    )
    normalized = MULTIPLE_BLANK_LINES_PATTERN.sub("\n\n", normalized)
    return normalized.strip()


def _is_bullet_or_list_item(line: str) -> bool:
    return bool(re.match(r"^(\d+[\.)]|[A-Za-z][\.)]|[-*\u2022])\s+", line))


def _is_academic_heading_line(line: str) -> bool:
    normalized = re.sub(r"^\d+(?:\.\d+)*[\.)]?\s+", "", line.strip().lower())
    normalized = re.sub(r"[^a-z0-9 &/-]+", "", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized in ACADEMIC_HEADINGS


def _should_join_lines(current_line: str, next_line: str) -> bool:
    if not current_line or not next_line:
        return False
    if _is_academic_heading_line(current_line) or _is_academic_heading_line(next_line):
        return False
    if _is_bullet_or_list_item(current_line) or _is_bullet_or_list_item(next_line):
        return False
    if current_line.endswith((".", "!", "?", ":", ";")):
        return False
    if next_line[0].isupper() and len(current_line.split()) <= 6:
        return False
    return True


def fix_broken_lines(text: str | None) -> str:
    if not text:
        return ""

    paragraphs = text.split("\n\n")
    fixed_paragraphs: list[str] = []

    for paragraph in paragraphs:
        lines = [line.strip() for line in paragraph.split("\n") if line.strip()]
        if not lines:
            continue

        merged_lines = [lines[0]]
        for next_line in lines[1:]:
            current_line = merged_lines[-1]
            if _should_join_lines(current_line, next_line):
                merged_lines[-1] = f"{current_line} {next_line}"
            else:
                merged_lines.append(next_line)
        fixed_paragraphs.append("\n".join(merged_lines))

    return "\n\n".join(fixed_paragraphs).strip()


def _is_safe_repeated_artifact(line: str) -> bool:
    if not line or len(line) > 120:
        return False
    if PAGE_NUMBER_PATTERN.match(line):
        return True
    if line.endswith((".", "?", "!")):
        return False
    return len(line.split()) <= 10


def remove_repeated_page_artifacts(text: str | None, min_repetitions: int = 3) -> str:
    if not text:
        return ""
    if min_repetitions < 2:
        raise ValueError("min_repetitions must be at least 2.")

    lines = text.split("\n")
    normalized_counts: dict[str, int] = {}
    for line in lines:
        normalized_line = line.strip()
        if normalized_line:
            normalized_counts[normalized_line.lower()] = (
                normalized_counts.get(normalized_line.lower(), 0) + 1
            )

    cleaned_lines = []
    for line in lines:
        normalized_line = line.strip()
        is_page_number = bool(PAGE_NUMBER_PATTERN.match(normalized_line))
        is_repeated_artifact = normalized_counts.get(
            normalized_line.lower(), 0
        ) >= min_repetitions and _is_safe_repeated_artifact(normalized_line)
        should_remove = normalized_line and (is_page_number or is_repeated_artifact)
        if not should_remove:
            cleaned_lines.append(line)

    return "\n".join(cleaned_lines).strip()


def clean_text(text: str | None) -> str:
    cleaned = remove_control_characters(text)
    cleaned = repair_hyphenated_line_breaks(cleaned)
    cleaned = normalize_whitespace(cleaned)
    cleaned = remove_repeated_page_artifacts(cleaned)
    cleaned = fix_broken_lines(cleaned)
    return normalize_whitespace(cleaned)


def _count_lines(text: str) -> int:
    if not text:
        return 0
    return len(text.splitlines())


def _count_words(text: str) -> int:
    return len(WORD_PATTERN.findall(text))


def calculate_cleaning_statistics(
    original_text: str,
    cleaned_text: str,
) -> CleaningStatistics:
    original_character_count = len(original_text)
    cleaned_character_count = len(cleaned_text)
    return CleaningStatistics(
        original_character_count=original_character_count,
        cleaned_character_count=cleaned_character_count,
        removed_character_count=max(original_character_count - cleaned_character_count, 0),
        original_word_count=_count_words(original_text),
        cleaned_word_count=_count_words(cleaned_text),
        original_line_count=_count_lines(original_text),
        cleaned_line_count=_count_lines(cleaned_text),
    )


def build_cleaning_warnings(
    original_text: str,
    cleaned_text: str,
    statistics: CleaningStatistics,
) -> list[str]:
    warnings: list[str] = []
    if not original_text.strip():
        warnings.append(EMPTY_INPUT_WARNING)
    if original_text.strip() and not cleaned_text.strip():
        warnings.append(EMPTY_CLEANED_TEXT_WARNING)
    if (
        statistics.original_character_count > 0
        and statistics.removed_character_count > statistics.original_character_count * 0.5
    ):
        warnings.append(LARGE_TEXT_REDUCTION_WARNING)
    return warnings


def run_text_cleaning_pipeline(text: str | None) -> TextCleaningResult:
    original_text = text or ""
    cleaned_text = clean_text(original_text)
    statistics = calculate_cleaning_statistics(original_text, cleaned_text)
    warnings = build_cleaning_warnings(original_text, cleaned_text, statistics)
    return TextCleaningResult(
        original_text=original_text,
        cleaned_text=cleaned_text,
        statistics=statistics,
        warnings=warnings,
    )

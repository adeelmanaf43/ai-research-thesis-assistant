import re
from dataclasses import asdict, dataclass
from typing import Literal

SectionType = Literal[
    "title",
    "abstract",
    "introduction",
    "literature_review",
    "methodology",
    "results",
    "discussion",
    "conclusion",
    "references",
    "unknown",
]

HEADING_ALIASES: dict[SectionType, tuple[str, ...]] = {
    "abstract": ("abstract", "summary"),
    "introduction": ("introduction", "background"),
    "literature_review": (
        "literature review",
        "review of literature",
        "related work",
        "previous studies",
    ),
    "methodology": (
        "methodology",
        "methods",
        "method",
        "materials and methods",
        "research methodology",
    ),
    "results": ("results", "findings"),
    "discussion": ("discussion", "analysis"),
    "conclusion": ("conclusion", "conclusions", "concluding remarks"),
    "references": ("references", "bibliography", "works cited"),
}

NUMBERED_HEADING_PATTERN = re.compile(
    r"^\s*(?:\d+(?:\.\d+)*[\.)]?\s+)?(?P<heading>[A-Za-z][A-Za-z &/-]{2,80})\s*:?\s*$"
)
MAX_TITLE_LINE_LENGTH = 180


@dataclass(frozen=True)
class DetectedSection:
    section_type: SectionType
    section_name: str
    heading: str
    detected_heading: str
    text: str
    start_index: int
    end_index: int
    confidence: float
    start_line: int
    end_line: int

    def to_dict(self) -> dict[str, str | int | float]:
        return asdict(self)


def _normalize_heading(heading: str) -> str:
    normalized = heading.strip().lower()
    normalized = re.sub(r"[^a-z0-9 &/-]+", "", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized


def classify_heading(line: str) -> SectionType | None:
    match = NUMBERED_HEADING_PATTERN.match(line)
    if not match:
        return None

    normalized_heading = _normalize_heading(match.group("heading"))
    for section_type, aliases in HEADING_ALIASES.items():
        if normalized_heading in aliases:
            return section_type
    return None


def _is_probable_title_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped or len(stripped) > MAX_TITLE_LINE_LENGTH:
        return False
    if classify_heading(stripped) is not None:
        return False
    if stripped.endswith((".", ":", ";")):
        return False
    return any(character.isalpha() for character in stripped)


def _first_non_empty_line(lines: list[str]) -> tuple[int, str] | None:
    for index, line in enumerate(lines):
        if line.strip():
            return index, line.strip()
    return None


def _line_start_indexes(text: str, lines: list[str]) -> list[int]:
    indexes: list[int] = []
    search_start = 0
    for line in lines:
        index = text.find(line, search_start)
        if index == -1:
            index = search_start
        indexes.append(index)
        search_start = index + len(line) + 1
    return indexes


def _section_name(section_type: SectionType) -> str:
    return section_type.replace("_", " ").title()


def _confidence_for_section(section_type: SectionType, detected_heading: str) -> float:
    if section_type == "unknown":
        return 0.0
    if section_type == "title":
        return 0.75
    if detected_heading.strip():
        return 0.95
    return 0.5


def _build_section(
    section_type: SectionType,
    heading: str,
    content_lines: list[str],
    start_line: int,
    end_line: int,
    line_start_indexes: list[int],
    full_text: str,
    full_lines: list[str],
) -> DetectedSection:
    text = "\n".join(line.rstrip() for line in content_lines).strip()
    start_index = line_start_indexes[start_line] if line_start_indexes else 0
    if end_line >= len(line_start_indexes):
        end_index = len(full_text)
    else:
        end_index = line_start_indexes[end_line] + len(full_lines[end_line])
    detected_heading = heading.strip()
    return DetectedSection(
        section_type=section_type,
        section_name=_section_name(section_type),
        heading=detected_heading,
        detected_heading=detected_heading,
        text=text,
        start_index=start_index,
        end_index=end_index,
        confidence=_confidence_for_section(section_type, detected_heading),
        start_line=start_line,
        end_line=end_line,
    )


def detect_sections(text: str | None) -> list[DetectedSection]:
    if not text or not text.strip():
        return [
            DetectedSection(
                section_type="unknown",
                section_name="Unknown",
                heading="Unknown",
                detected_heading="Unknown",
                text="",
                start_index=0,
                end_index=0,
                confidence=0.0,
                start_line=0,
                end_line=0,
            )
        ]

    lines = text.splitlines()
    line_start_indexes = _line_start_indexes(text, lines)
    detected_sections: list[DetectedSection] = []
    current_type: SectionType | None = None
    current_heading = ""
    current_start_line = 0
    current_content: list[str] = []

    first_content_line = _first_non_empty_line(lines)
    if first_content_line is not None:
        first_line_index, first_line = first_content_line
        if _is_probable_title_line(first_line):
            detected_sections.append(
                _build_section(
                    "title",
                    "Title",
                    [first_line],
                    first_line_index,
                    first_line_index,
                    line_start_indexes,
                    text,
                    lines,
                )
            )

    for line_number, line in enumerate(lines):
        stripped_line = line.strip()
        section_type = classify_heading(stripped_line)
        if section_type is None:
            if current_type is not None:
                current_content.append(line)
            continue

        if current_type is not None:
            detected_sections.append(
                _build_section(
                    current_type,
                    current_heading,
                    current_content,
                    current_start_line,
                    line_number - 1,
                    line_start_indexes,
                    text,
                    lines,
                )
            )

        current_type = section_type
        current_heading = stripped_line
        current_start_line = line_number
        current_content = []

    if current_type is not None:
        detected_sections.append(
            _build_section(
                current_type,
                current_heading,
                current_content,
                current_start_line,
                len(lines) - 1,
                line_start_indexes,
                text,
                lines,
            )
        )

    if detected_sections:
        return detected_sections

    first_line_index, first_line = first_content_line or (0, "")
    if _is_probable_title_line(first_line):
        return [
            _build_section(
                "title",
                "Title",
                [first_line],
                first_line_index,
                first_line_index,
                line_start_indexes,
                text,
                lines,
            )
        ]

    return [
        DetectedSection(
            section_type="unknown",
            section_name="Unknown",
            heading="Unknown",
            detected_heading="Unknown",
            text=text.strip(),
            start_index=0,
            end_index=len(text),
            confidence=0.0,
            start_line=0,
            end_line=max(len(lines) - 1, 0),
        )
    ]

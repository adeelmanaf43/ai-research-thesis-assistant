import json
from dataclasses import asdict, dataclass
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.models.analysis import Analysis
from backend.app.models.chunk import Chunk
from backend.app.models.document import Document


@dataclass(frozen=True)
class SectionOverview:
    section_name: str
    detected_heading: str
    confidence: float

    def to_dict(self) -> dict[str, str | float]:
        return asdict(self)


@dataclass(frozen=True)
class ProcessingSummary:
    status: str
    message: str
    is_complete: bool
    requires_attention: bool
    next_step: str | None = None

    def to_dict(self) -> dict[str, str | bool | None]:
        return asdict(self)


@dataclass(frozen=True)
class DocumentOverview:
    document_id: int
    filename: str
    status: str
    page_count: int | None
    word_count: int | None
    chunk_count: int
    detected_sections: list[SectionOverview]
    extraction_warnings: list[str]
    processing_summary: ProcessingSummary

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["detected_sections"] = [section.to_dict() for section in self.detected_sections]
        payload["processing_summary"] = self.processing_summary.to_dict()
        return payload


def _split_warning_lines(value: str | None) -> list[str]:
    if not value:
        return []
    return [line.strip() for line in value.splitlines() if line.strip()]


def _latest_section_analysis(db: Session, document_id: int) -> Analysis | None:
    statement = (
        select(Analysis)
        .where(
            Analysis.document_id == document_id,
            Analysis.analysis_type == "section_detection",
        )
        .order_by(Analysis.created_at.desc(), Analysis.id.desc())
    )
    return db.scalars(statement).first()


def _load_detected_sections(analysis: Analysis | None) -> list[SectionOverview]:
    if analysis is None:
        return []

    try:
        raw_sections = json.loads(analysis.content)
    except json.JSONDecodeError:
        return []

    if not isinstance(raw_sections, list):
        return []

    sections: list[SectionOverview] = []
    for raw_section in raw_sections:
        if not isinstance(raw_section, dict):
            continue
        section_name = str(raw_section.get("section_name") or "Unknown").strip() or "Unknown"
        detected_heading = str(raw_section.get("detected_heading") or "").strip()
        raw_confidence = raw_section.get("confidence", 0.0)
        try:
            confidence = float(raw_confidence)
        except (TypeError, ValueError):
            confidence = 0.0
        confidence = max(0.0, min(confidence, 1.0))

        sections.append(
            SectionOverview(
                section_name=section_name,
                detected_heading=detected_heading,
                confidence=confidence,
            )
        )

    return sections


def _chunk_count(db: Session, document_id: int) -> int:
    statement = select(func.count(Chunk.id)).where(Chunk.document_id == document_id)
    return int(db.scalar(statement) or 0)


def _processing_summary(
    document: Document,
    *,
    chunk_count: int,
    section_count: int,
) -> ProcessingSummary:
    status = document.status
    if status == "processed":
        return ProcessingSummary(
            status=status,
            message=(
                f"Document processed locally with {section_count} detected sections "
                f"and {chunk_count} stored chunks."
            ),
            is_complete=True,
            requires_attention=False,
            next_step="Review the overview or continue with the next local analysis step.",
        )
    if status == "ocr_needed":
        return ProcessingSummary(
            status=status,
            message="Document was saved, but very little text was extracted. OCR may be needed.",
            is_complete=False,
            requires_attention=True,
            next_step="Use a text-based PDF or add OCR support in a later workflow.",
        )
    if status == "extraction_failed":
        return ProcessingSummary(
            status=status,
            message="Document was saved, but local PDF text extraction failed.",
            is_complete=False,
            requires_attention=True,
            next_step="Verify the PDF is readable and try uploading it again.",
        )
    if status == "text_processing_failed":
        return ProcessingSummary(
            status=status,
            message="Document text was extracted, but text artifact storage failed.",
            is_complete=False,
            requires_attention=True,
            next_step="Check local storage permissions and retry processing.",
        )
    if status == "section_detection_failed":
        return ProcessingSummary(
            status=status,
            message="Document text was cleaned, but section detection output could not be stored.",
            is_complete=False,
            requires_attention=True,
            next_step="Check local database access and retry processing.",
        )
    if status == "chunking_failed":
        return ProcessingSummary(
            status=status,
            message="Document sections were detected, but chunk storage failed.",
            is_complete=False,
            requires_attention=True,
            next_step="Check local database access and retry processing.",
        )
    return ProcessingSummary(
        status=status,
        message=f"Document is currently in '{status}' status.",
        is_complete=False,
        requires_attention=False,
        next_step="Wait for processing to finish or inspect the document status.",
    )


def get_document_overview(db: Session, document_id: int) -> DocumentOverview | None:
    if document_id <= 0:
        raise ValueError("Document ID must be a positive integer.")

    document = db.get(Document, document_id)
    if document is None:
        return None

    chunk_count = _chunk_count(db, document.id)
    sections = _load_detected_sections(_latest_section_analysis(db, document.id))
    warnings = [
        *_split_warning_lines(document.extraction_error),
        *_split_warning_lines(document.cleaning_warnings),
    ]

    return DocumentOverview(
        document_id=document.id,
        filename=document.original_filename,
        status=document.status,
        page_count=document.page_count,
        word_count=document.word_count,
        chunk_count=chunk_count,
        detected_sections=sections,
        extraction_warnings=warnings,
        processing_summary=_processing_summary(
            document,
            chunk_count=chunk_count,
            section_count=len(sections),
        ),
    )

import json
import re
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.models.analysis import Analysis
from backend.app.models.chunk import Chunk
from backend.app.models.document import Document
from backend.app.schemas.document import DocumentCreate
from backend.app.services.document_storage import (
    build_stored_document_filename,
    ensure_project_documents_dir,
    get_document_storage_path,
)
from backend.app.services.local_analysis import (
    SectionSummary,
    build_document_statistics,
    extract_keywords,
    summarize_section,
)
from backend.app.services.section_detection import DetectedSection
from backend.app.services.text_cleaning import TextCleaningResult


class DocumentStorageError(RuntimeError):
    """Raised when a document file cannot be saved locally."""


class DocumentProcessingError(RuntimeError):
    """Raised when local document processing metadata cannot be saved."""


WORD_PATTERN = re.compile(r"\b\w+\b")
MIN_EXTRACTED_WORDS_FOR_TEXT = 10
OCR_NEEDED_MESSAGE = "Very little extractable text was found. This PDF may be scanned or need OCR."
DOCUMENT_OVERVIEW_LOCAL_ANALYSIS_TYPE = "document_overview_local"
DOCUMENT_SECTION_SUMMARIES_LOCAL_ANALYSIS_TYPE = "section_summaries_local"


@dataclass(frozen=True)
class SavedDocumentFile:
    original_filename: str
    stored_filename: str
    file_path: Path
    file_size_bytes: int


@dataclass(frozen=True)
class TextProcessingArtifacts:
    extracted_text_path: Path
    cleaned_text_path: Path


@dataclass(frozen=True)
class StoredDetectedSection:
    section_type: str
    section_name: str
    text: str
    confidence: float


@dataclass(frozen=True)
class SectionSummaryResult:
    section_name: str
    section_type: str
    summary: str
    selected_sentence_count: int
    source_sentence_indexes: list[int]
    confidence: float
    limitations: list[str]

    def to_dict(self) -> dict[str, str | int | float | list[int] | list[str]]:
        return {
            "section_name": self.section_name,
            "section_type": self.section_type,
            "summary": self.summary,
            "selected_sentence_count": self.selected_sentence_count,
            "source_sentence_indexes": self.source_sentence_indexes,
            "confidence": self.confidence,
            "limitations": self.limitations,
        }


@dataclass(frozen=True)
class DocumentSectionSummaries:
    document_id: int
    summaries: list[SectionSummaryResult]
    source_section_names: list[str]
    limitations: list[str]

    def to_dict(self) -> dict[str, int | list[dict] | list[str]]:
        return {
            "document_id": self.document_id,
            "summaries": [summary.to_dict() for summary in self.summaries],
            "source_section_names": self.source_section_names,
            "limitations": self.limitations,
        }


def save_uploaded_file(
    upload_dir: Path,
    project_id: int,
    original_filename: str,
    file_content: bytes,
) -> SavedDocumentFile:
    stored_filename = build_stored_document_filename(original_filename)
    ensure_project_documents_dir(upload_dir, project_id)
    file_path = get_document_storage_path(upload_dir, project_id, stored_filename)

    try:
        file_path.write_bytes(file_content)
    except OSError as exc:
        raise DocumentStorageError(f"Could not save uploaded file: {exc}") from exc

    return SavedDocumentFile(
        original_filename=original_filename,
        stored_filename=stored_filename,
        file_path=file_path,
        file_size_bytes=len(file_content),
    )


def create_document_record(
    db: Session,
    document_in: DocumentCreate,
    stored_filename: str,
    file_path: Path | str,
    status: str = "stored",
) -> Document:
    document = Document(
        project_id=document_in.project_id,
        original_filename=document_in.original_filename,
        stored_filename=stored_filename,
        file_path=str(file_path),
        mime_type=document_in.mime_type,
        file_size_bytes=document_in.file_size_bytes,
        status=status,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


def save_text_processing_artifacts(
    pdf_file_path: Path | str,
    cleaning_result: TextCleaningResult,
) -> TextProcessingArtifacts:
    source_path = Path(pdf_file_path)
    extracted_text_path = source_path.with_name(f"{source_path.stem}.extracted.txt")
    cleaned_text_path = source_path.with_name(f"{source_path.stem}.cleaned.txt")

    try:
        extracted_text_path.write_text(cleaning_result.original_text, encoding="utf-8")
        cleaned_text_path.write_text(cleaning_result.cleaned_text, encoding="utf-8")
    except OSError as exc:
        raise DocumentStorageError(f"Could not save text processing artifacts: {exc}") from exc

    return TextProcessingArtifacts(
        extracted_text_path=extracted_text_path,
        cleaned_text_path=cleaned_text_path,
    )


def create_section_detection_analysis(
    db: Session,
    document: Document,
    sections: list[DetectedSection],
) -> Analysis:
    content = json.dumps(
        [section.to_dict() for section in sections],
        ensure_ascii=True,
        indent=2,
    )
    analysis = Analysis(
        project_id=document.project_id,
        document_id=document.id,
        analysis_type="section_detection",
        title="Detected document sections",
        content=content,
        provider_mode="local",
    )

    try:
        db.add(analysis)
        db.commit()
        db.refresh(analysis)
    except SQLAlchemyError as exc:
        db.rollback()
        raise DocumentProcessingError("Could not save section detection analysis.") from exc

    return analysis


def create_document_overview_local_analysis(
    db: Session,
    document: Document,
    output_json: dict,
) -> Analysis:
    try:
        content = json.dumps(output_json, ensure_ascii=True, indent=2, sort_keys=True)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "Document overview local analysis output must be JSON serializable."
        ) from exc

    analysis = Analysis(
        project_id=document.project_id,
        document_id=document.id,
        analysis_type=DOCUMENT_OVERVIEW_LOCAL_ANALYSIS_TYPE,
        title="Local document overview analysis",
        content=content,
        provider_mode="local",
    )

    try:
        db.add(analysis)
        db.commit()
        db.refresh(analysis)
    except SQLAlchemyError as exc:
        db.rollback()
        raise DocumentProcessingError("Could not save local document overview analysis.") from exc

    return analysis


def create_document_section_summaries_local_analysis(
    db: Session,
    document_id: int,
) -> Analysis | None:
    section_summaries = get_document_section_summaries(db, document_id)
    if section_summaries is None:
        return None

    document = db.get(Document, document_id)
    if document is None:
        return None

    output_json = section_summaries.to_dict()
    try:
        content = json.dumps(output_json, ensure_ascii=True, indent=2, sort_keys=True)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "Section summaries local analysis output must be JSON serializable."
        ) from exc

    analysis = Analysis(
        project_id=document.project_id,
        document_id=document.id,
        analysis_type=DOCUMENT_SECTION_SUMMARIES_LOCAL_ANALYSIS_TYPE,
        title="Local section summaries",
        content=content,
        provider_mode="local",
    )

    try:
        db.add(analysis)
        db.commit()
        db.refresh(analysis)
    except SQLAlchemyError as exc:
        db.rollback()
        raise DocumentProcessingError("Could not save local section summaries.") from exc

    return analysis


def get_latest_document_overview_local_analysis(
    db: Session,
    document_id: int,
) -> Analysis | None:
    if document_id <= 0:
        raise ValueError("Document ID must be a positive integer.")

    statement = (
        select(Analysis)
        .where(
            Analysis.document_id == document_id,
            Analysis.analysis_type == DOCUMENT_OVERVIEW_LOCAL_ANALYSIS_TYPE,
        )
        .order_by(Analysis.created_at.desc(), Analysis.id.desc())
    )
    return db.scalars(statement).first()


def _latest_section_detection_analysis(db: Session, document_id: int) -> Analysis | None:
    statement = (
        select(Analysis)
        .where(
            Analysis.document_id == document_id,
            Analysis.analysis_type == "section_detection",
        )
        .order_by(Analysis.created_at.desc(), Analysis.id.desc())
    )
    return db.scalars(statement).first()


def _load_stored_sections(analysis: Analysis | None) -> list[StoredDetectedSection]:
    if analysis is None:
        return []

    try:
        raw_sections = json.loads(analysis.content)
    except json.JSONDecodeError:
        return []

    if not isinstance(raw_sections, list):
        return []

    sections: list[StoredDetectedSection] = []
    for raw_section in raw_sections:
        if not isinstance(raw_section, dict):
            continue
        raw_confidence = raw_section.get("confidence", 0.0)
        try:
            confidence = float(raw_confidence)
        except (TypeError, ValueError):
            confidence = 0.0
        confidence = max(0.0, min(confidence, 1.0))
        sections.append(
            StoredDetectedSection(
                section_type=str(raw_section.get("section_type") or "unknown"),
                section_name=str(raw_section.get("section_name") or "Unknown"),
                text=str(raw_section.get("text") or ""),
                confidence=confidence,
            )
        )
    return sections


def _summary_confidence(section: StoredDetectedSection, summary: SectionSummary) -> float:
    if not summary.summary:
        return 0.0
    sentence_factor = min(summary.selected_sentence_count / 2, 1.0)
    return round((section.confidence * 0.75) + (sentence_factor * 0.25), 2)


def _summary_limitations(
    section: StoredDetectedSection,
    summary: SectionSummary,
) -> list[str]:
    limitations = [
        (
            "Extractive summary uses original sentences only and does not rewrite "
            "or infer missing context."
        )
    ]
    if section.confidence < 0.8:
        limitations.append(
            "Section confidence is heuristic because section detection is rule-based."
        )
    if not summary.summary:
        limitations.append("No extractable summary sentences were found for this section.")
    elif summary.selected_sentence_count < 2:
        limitations.append("Short section produced fewer than two summary sentences.")
    return limitations


def get_document_section_summaries(
    db: Session,
    document_id: int,
) -> DocumentSectionSummaries | None:
    if document_id <= 0:
        raise ValueError("Document ID must be a positive integer.")

    document = db.get(Document, document_id)
    if document is None:
        return None

    section_analysis = _latest_section_detection_analysis(db, document.id)
    sections = _load_stored_sections(section_analysis)
    if not sections:
        return DocumentSectionSummaries(
            document_id=document.id,
            summaries=[],
            source_section_names=[],
            limitations=[
                (
                    "No stored section detection output was found. "
                    "Upload and process the document first."
                )
            ],
        )

    summaries: list[SectionSummaryResult] = []
    source_section_names: list[str] = []
    for section in sections:
        summary = summarize_section(section)
        if summary is None:
            continue

        source_section_names.append(section.section_name)
        summaries.append(
            SectionSummaryResult(
                section_name=summary.section_name,
                section_type=summary.section_type,
                summary=summary.summary,
                selected_sentence_count=summary.selected_sentence_count,
                source_sentence_indexes=summary.source_sentence_indexes,
                confidence=_summary_confidence(section, summary),
                limitations=_summary_limitations(section, summary),
            )
        )

    limitations = [
        (
            "Summaries are extractive and local; they select source sentences "
            "instead of generating new prose."
        )
    ]
    if not summaries:
        limitations.append("No supported academic sections were available for summarization.")

    return DocumentSectionSummaries(
        document_id=document.id,
        summaries=summaries,
        source_section_names=source_section_names,
        limitations=limitations,
    )


def _document_chunks(db: Session, document_id: int) -> list[Chunk]:
    statement = (
        select(Chunk)
        .where(Chunk.document_id == document_id)
        .order_by(Chunk.chunk_index.asc(), Chunk.id.asc())
    )
    return list(db.scalars(statement).all())


def create_document_overview_local_analysis_for_document(
    db: Session,
    document_id: int,
    *,
    top_keyword_count: int = 10,
) -> Analysis | None:
    if document_id <= 0:
        raise ValueError("Document ID must be a positive integer.")

    document = db.get(Document, document_id)
    if document is None:
        return None
    if not document.cleaned_text_path:
        raise DocumentProcessingError(
            "Cleaned text is not available. Upload and process the document first."
        )

    cleaned_text_path = Path(document.cleaned_text_path)
    try:
        cleaned_text = cleaned_text_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise DocumentProcessingError("Could not read cleaned document text.") from exc

    sections = _load_stored_sections(_latest_section_detection_analysis(db, document.id))
    chunks = _document_chunks(db, document.id)
    output_json = {
        "document_id": document.id,
        "filename": document.original_filename,
        "keywords": [
            keyword.to_dict() for keyword in extract_keywords(cleaned_text, top_n=top_keyword_count)
        ],
        "statistics": build_document_statistics(
            cleaned_text,
            sections=sections,
            chunks=chunks,
        ).to_dict(),
    }
    return create_document_overview_local_analysis(db, document, output_json)


def count_words(text: str) -> int:
    return len(WORD_PATTERN.findall(text))


def is_ocr_likely_needed(word_count: int) -> bool:
    return word_count < MIN_EXTRACTED_WORDS_FOR_TEXT


def update_document_extraction_metadata(
    db: Session,
    document: Document,
    *,
    page_count: int | None,
    word_count: int | None,
    status: str,
    extraction_error: str | None = None,
    extracted_text_path: Path | str | None = None,
    cleaned_text_path: Path | str | None = None,
    cleaning_warnings: list[str] | None = None,
) -> Document:
    cleaned_status = status.strip()
    if not cleaned_status:
        raise ValueError("Document status cannot be empty.")

    document.page_count = page_count
    document.word_count = word_count
    document.status = cleaned_status
    cleaned_error = extraction_error.strip() if extraction_error else ""
    document.extraction_error = cleaned_error or None
    document.extracted_text_path = str(extracted_text_path) if extracted_text_path else None
    document.cleaned_text_path = str(cleaned_text_path) if cleaned_text_path else None
    document.cleaning_warnings = "\n".join(cleaning_warnings or []) or None
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


def update_document_status(db: Session, document: Document, status: str) -> Document:
    cleaned_status = status.strip()
    if not cleaned_status:
        raise ValueError("Document status cannot be empty.")

    document.status = cleaned_status
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


def list_documents_by_project(db: Session, project_id: int) -> list[Document]:
    statement = (
        select(Document)
        .where(Document.project_id == project_id)
        .order_by(Document.uploaded_at.desc(), Document.id.desc())
    )
    return list(db.scalars(statement).all())

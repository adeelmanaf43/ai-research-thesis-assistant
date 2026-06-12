import re
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.document import Document
from backend.app.schemas.document import DocumentCreate
from backend.app.services.document_storage import (
    build_stored_document_filename,
    ensure_project_documents_dir,
    get_document_storage_path,
)
from backend.app.services.text_cleaning import TextCleaningResult


class DocumentStorageError(RuntimeError):
    """Raised when a document file cannot be saved locally."""


WORD_PATTERN = re.compile(r"\b\w+\b")
MIN_EXTRACTED_WORDS_FOR_TEXT = 10
OCR_NEEDED_MESSAGE = "Very little extractable text was found. This PDF may be scanned or need OCR."


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

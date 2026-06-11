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


class DocumentStorageError(RuntimeError):
    """Raised when a document file cannot be saved locally."""


@dataclass(frozen=True)
class SavedDocumentFile:
    original_filename: str
    stored_filename: str
    file_path: Path
    file_size_bytes: int


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

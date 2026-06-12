from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from backend.app.core.config import Settings, get_settings
from backend.app.core.database import get_db
from backend.app.schemas.document import DocumentCreate, DocumentResponse
from backend.app.services.document_extraction import PDFExtractionError, extract_pdf_text
from backend.app.services.document_service import (
    OCR_NEEDED_MESSAGE,
    DocumentStorageError,
    count_words,
    create_document_record,
    is_ocr_likely_needed,
    save_uploaded_file,
    update_document_extraction_metadata,
)
from backend.app.services.project_service import get_project_by_id

PDF_CONTENT_TYPES = {"application/pdf", "application/x-pdf"}

router = APIRouter(prefix="/api/projects/{project_id}/documents", tags=["documents"])


def _validate_pdf_upload(file: UploadFile) -> None:
    filename = file.filename or ""
    if Path(filename).suffix.lower() != ".pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are supported.",
        )

    if file.content_type and file.content_type.lower() not in PDF_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file content type must be application/pdf.",
        )


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document_route(
    project_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> DocumentResponse:
    project = get_project_by_id(db, project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found.",
        )

    _validate_pdf_upload(file)
    file_content = await file.read()
    if len(file_content) > settings.max_upload_file_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="Uploaded file exceeds the configured size limit.",
        )

    try:
        saved_file = save_uploaded_file(
            settings.upload_dir,
            project_id,
            file.filename or "document.pdf",
            file_content,
        )
    except DocumentStorageError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not save uploaded document.",
        ) from exc

    document = create_document_record(
        db,
        DocumentCreate(
            project_id=project_id,
            original_filename=saved_file.original_filename,
            mime_type=file.content_type,
            file_size_bytes=saved_file.file_size_bytes,
        ),
        stored_filename=saved_file.stored_filename,
        file_path=saved_file.file_path,
    )

    try:
        extracted_pdf = extract_pdf_text(saved_file.file_path)
    except PDFExtractionError as exc:
        return update_document_extraction_metadata(
            db,
            document,
            page_count=None,
            word_count=None,
            status="extraction_failed",
            extraction_error=str(exc),
        )

    word_count = count_words(extracted_pdf.full_text)
    if is_ocr_likely_needed(word_count):
        return update_document_extraction_metadata(
            db,
            document,
            page_count=extracted_pdf.page_count,
            word_count=word_count,
            status="ocr_needed",
            extraction_error=OCR_NEEDED_MESSAGE,
        )

    return update_document_extraction_metadata(
        db,
        document,
        page_count=extracted_pdf.page_count,
        word_count=word_count,
        status="extracted",
    )

from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from backend.app.core.config import Settings, get_settings
from backend.app.core.database import get_db
from backend.app.schemas.document import (
    DocumentCreate,
    DocumentOverviewResponse,
    DocumentResponse,
)
from backend.app.services.chunking import (
    ChunkPersistenceError,
    replace_document_chunks,
    split_sections_into_chunks,
)
from backend.app.services.document_extraction import PDFExtractionError, extract_pdf_text
from backend.app.services.document_overview import get_document_overview
from backend.app.services.document_service import (
    OCR_NEEDED_MESSAGE,
    DocumentProcessingError,
    DocumentStorageError,
    count_words,
    create_document_record,
    create_section_detection_analysis,
    is_ocr_likely_needed,
    list_documents_by_project,
    save_text_processing_artifacts,
    save_uploaded_file,
    update_document_extraction_metadata,
)
from backend.app.services.project_service import get_project_by_id
from backend.app.services.section_detection import detect_sections
from backend.app.services.text_cleaning import run_text_cleaning_pipeline

PDF_CONTENT_TYPES = {"application/pdf", "application/x-pdf"}

router = APIRouter(prefix="/api/projects/{project_id}/documents", tags=["documents"])
overview_router = APIRouter(prefix="/api/documents", tags=["documents"])


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


@router.get("", response_model=list[DocumentResponse])
def list_project_documents_route(
    project_id: int,
    db: Session = Depends(get_db),
) -> list[DocumentResponse]:
    project = get_project_by_id(db, project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found. Create the project before listing documents.",
        )

    return list_documents_by_project(db, project_id)


@overview_router.get("/{document_id}/overview", response_model=DocumentOverviewResponse)
def get_document_overview_route(
    document_id: int,
    db: Session = Depends(get_db),
) -> dict:
    try:
        overview = get_document_overview(db, document_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    if overview is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found. Upload a document or use an existing document ID.",
        )

    return overview.to_dict()


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

    cleaning_result = run_text_cleaning_pipeline(extracted_pdf.full_text)
    word_count = count_words(cleaning_result.cleaned_text)

    try:
        text_artifacts = save_text_processing_artifacts(saved_file.file_path, cleaning_result)
    except DocumentStorageError as exc:
        return update_document_extraction_metadata(
            db,
            document,
            page_count=extracted_pdf.page_count,
            word_count=word_count,
            status="text_processing_failed",
            extraction_error=str(exc),
            cleaning_warnings=cleaning_result.warnings,
        )

    sections = detect_sections(cleaning_result.cleaned_text)
    try:
        create_section_detection_analysis(db, document, sections)
    except DocumentProcessingError as exc:
        return update_document_extraction_metadata(
            db,
            document,
            page_count=extracted_pdf.page_count,
            word_count=word_count,
            status="section_detection_failed",
            extraction_error=str(exc),
            extracted_text_path=text_artifacts.extracted_text_path,
            cleaned_text_path=text_artifacts.cleaned_text_path,
            cleaning_warnings=cleaning_result.warnings,
        )

    chunks = split_sections_into_chunks(sections, page_count=extracted_pdf.page_count)
    try:
        replace_document_chunks(db, document.id, chunks)
    except ChunkPersistenceError as exc:
        return update_document_extraction_metadata(
            db,
            document,
            page_count=extracted_pdf.page_count,
            word_count=word_count,
            status="chunking_failed",
            extraction_error=str(exc),
            extracted_text_path=text_artifacts.extracted_text_path,
            cleaned_text_path=text_artifacts.cleaned_text_path,
            cleaning_warnings=cleaning_result.warnings,
        )

    if is_ocr_likely_needed(word_count):
        return update_document_extraction_metadata(
            db,
            document,
            page_count=extracted_pdf.page_count,
            word_count=word_count,
            status="ocr_needed",
            extraction_error=OCR_NEEDED_MESSAGE,
            extracted_text_path=text_artifacts.extracted_text_path,
            cleaned_text_path=text_artifacts.cleaned_text_path,
            cleaning_warnings=cleaning_result.warnings,
        )

    return update_document_extraction_metadata(
        db,
        document,
        page_count=extracted_pdf.page_count,
        word_count=word_count,
        status="processed",
        extracted_text_path=text_artifacts.extracted_text_path,
        cleaned_text_path=text_artifacts.cleaned_text_path,
        cleaning_warnings=cleaning_result.warnings,
    )

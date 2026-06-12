"""Domain service boundary for application workflows."""

from backend.app.services.document_extraction import (
    ExtractedPDF,
    PDFExtractionDependencyError,
    PDFExtractionError,
    extract_pdf_text,
)
from backend.app.services.document_service import (
    OCR_NEEDED_MESSAGE,
    DocumentStorageError,
    SavedDocumentFile,
    count_words,
    create_document_record,
    is_ocr_likely_needed,
    list_documents_by_project,
    save_uploaded_file,
    update_document_extraction_metadata,
    update_document_status,
)
from backend.app.services.document_storage import (
    UnsafeStoragePathError,
    build_stored_document_filename,
    ensure_path_within_directory,
    ensure_project_documents_dir,
    get_document_storage_path,
    get_project_documents_dir,
    sanitize_upload_filename,
)
from backend.app.services.project_service import (
    create_project,
    delete_project,
    get_project_by_id,
    list_projects,
    update_project,
)

__all__ = [
    "DocumentStorageError",
    "ExtractedPDF",
    "OCR_NEEDED_MESSAGE",
    "PDFExtractionDependencyError",
    "PDFExtractionError",
    "SavedDocumentFile",
    "UnsafeStoragePathError",
    "build_stored_document_filename",
    "count_words",
    "create_document_record",
    "create_project",
    "delete_project",
    "ensure_path_within_directory",
    "ensure_project_documents_dir",
    "extract_pdf_text",
    "get_document_storage_path",
    "get_project_by_id",
    "get_project_documents_dir",
    "is_ocr_likely_needed",
    "list_documents_by_project",
    "list_projects",
    "save_uploaded_file",
    "sanitize_upload_filename",
    "update_document_extraction_metadata",
    "update_document_status",
    "update_project",
]

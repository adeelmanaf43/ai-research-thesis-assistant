# Architecture Notes

The product is local-first. The system must remain useful when Ollama is unavailable, no paid API key exists, documents are long, or local hardware is limited.

## Current Layers

- `backend/app/main.py`: FastAPI application factory and route registration
- `backend/app/core/config.py`: environment-driven local configuration
- `backend/app/core/database.py`: SQLAlchemy SQLite engine, session dependency, declarative `Base`, and metadata initialization utility
- `backend/app/api/`: HTTP routes
- `backend/app/schemas/`: API response/request schemas
- `backend/app/models/`: base ORM models for users, projects, documents, chunks, analyses, and chat history
- `backend/app/services/`: business logic services kept outside API route modules
- `frontend/streamlit_app.py`: Streamlit entry point

## Planned Local-First Flow

Project creation, file upload, text extraction, cleaning, section detection, chunking, local overview, source-grounded Q&A, comparison, and export will be added in later milestones.

Ollama and cloud providers are optional layers behind provider abstractions. They must never be required for the core app to work.

## Current Processing Pipeline

Week 2 now validates the local upload-to-overview pipeline. The pipeline is intentionally deterministic and keeps every required step inside local services before any optional AI layer is introduced.

```text
POST /api/projects/{project_id}/documents
  -> validate project, PDF extension, content type, and file size
  -> save original PDF under data/uploads/projects/{project_id}/documents/
  -> create documents row in SQLite
  -> extract page text, page count, and metadata with PyMuPDF
  -> clean extracted text with deterministic text_cleaning helpers
  -> save .extracted.txt and .cleaned.txt artifacts beside the PDF
  -> detect academic sections with rule-based section_detection
  -> store section_detection output in analyses table
  -> split section text into overlapping chunks with chunking service
  -> replace document chunks transactionally in chunks table
  -> mark document as processed, ocr_needed, or a clear failure status
  -> GET /api/documents/{document_id}/overview returns safe processing metadata
```

Pipeline ownership:

- `routes_documents.py` orchestrates HTTP validation and calls service functions.
- `document_storage.py` owns safe local paths.
- `document_extraction.py` owns PyMuPDF extraction.
- `text_cleaning.py` owns deterministic cleanup and warnings.
- `section_detection.py` owns rule-based academic section metadata.
- `chunking.py` owns chunk generation and transactional chunk replacement.
- `document_overview.py` owns user-facing overview aggregation.

Failure behavior:

- Invalid uploads fail before storage.
- Unreadable PDFs keep the upload record and use `extraction_failed`.
- Very low-text PDFs use `ocr_needed` without requiring OCR.
- Text artifact, section analysis, and chunk storage failures use explicit failure statuses instead of crashing silently.
- The overview endpoint exposes safe metadata, warnings, and aggregate counts, not internal file paths or raw chunk text.

## Configuration Defaults

The backend loads local settings from environment variables and `.env` when available. Relative local paths are resolved from the project root so commands work consistently from the repository. The default provider mode is `local`, and the app creates upload/export directories on startup.

## Database Foundation

The backend uses SQLAlchemy with SQLite for the local-first MVP. `backend/app/core/database.py` exposes the shared engine, `SessionLocal`, `get_db()` FastAPI dependency, declarative `Base`, and `init_database()` utility.

The Week 1 foundation includes base ORM tables for `User`, `Project`, `Document`, `Chunk`, `Analysis`, and `ChatHistory`. User ownership is optional on projects so the MVP can work without a login flow.

## Schema Boundary

Project and document Pydantic schemas provide serialization-friendly request and response contracts. Document responses intentionally omit internal storage fields such as `file_path` and `stored_filename`.

Project schemas separate creation/update input from list/detail responses and reject blank project names.

## Service Layer

Project CRUD behavior starts in `backend/app/services/project_service.py`. Routes should call service functions instead of placing database business logic directly in API modules.

Document storage path behavior starts in `backend/app/services/document_storage.py`. File storage helpers keep uploaded document paths inside the configured upload directory and use the structure `uploads/projects/{project_id}/documents/`.

Document persistence behavior starts in `backend/app/services/document_service.py`. It provides service-layer functions for saving supplied file bytes, creating document database records, updating document status, and fetching documents by project.

PDF text extraction starts in `backend/app/services/document_extraction.py`. It uses PyMuPDF locally to return page count, basic PDF metadata, a per-page text list, combined text, and a safe `has_text` flag. This service is intentionally separate from upload routes so extraction can be tested and evolved without making file upload brittle.

Text cleaning starts in `backend/app/services/text_cleaning.py`. It provides deterministic helpers for whitespace normalization, broken line repair, hyphenated line break repair, conservative repeated page artifact removal, control character removal, and a full `run_text_cleaning_pipeline()` function. The pipeline returns original text, cleaned text, cleaning statistics, and warnings. It is intentionally local and rule-based so it can run without AI providers.

Section detection starts in `backend/app/services/section_detection.py`. It uses rule-based academic headings to identify title, abstract, introduction, literature review, methodology, results, discussion, conclusion, references, and unknown sections. Each detected section includes a section name, detected heading, character start and end indexes, text, confidence score, and line indexes. The service is deterministic and local-first so it can run before chunking or AI providers.

The section detector is intentionally explainable rather than intelligent. It depends on headings extracted from the PDF text, so unusual section names, damaged PDF layout, OCR-only documents, or headings split across lines can reduce accuracy. Unsupported headings are preserved inside the nearest known section instead of being discarded, and heuristic confidence values are used only as local processing hints.

Chunking starts in `backend/app/services/chunking.py`. It splits cleaned text or detected section text into local `TextChunk` objects with `chunk_index`, `section_name`, approximate `page_start` and `page_end`, text, and word count. Chunk settings are validated so standard processing uses 500-800 word chunks with 100-150 word overlap. The service can replace stored chunks for a document transactionally by deleting stale chunks and inserting the new chunk set in one database commit. It does not call AI providers.

Document overview starts in `backend/app/services/document_overview.py`. It reads existing document metadata, internal chunk records, section detection analysis, extraction errors, and cleaning warnings to return a local overview with filename, status, page count, word count, chunk count, detected sections, extraction warnings, and a structured processing summary. The summary includes a user-facing message, completion flag, attention flag, and suggested next step. The public overview route exposes this service at `/api/documents/{document_id}/overview` without exposing internal file paths or calling AI providers.

Local research information extraction starts in `backend/app/services/local_analysis.py` and is stored through `backend/app/services/document_service.py`. The route `POST /api/analysis/{document_id}/research-info` reads cleaned text, uses stored section detection output when available, extracts common academic fields with deterministic rules, and stores the payload in the `analyses` table with `analysis_type="research_info_local"` and `provider_mode="local"`.

This extraction layer is intentionally reliable rather than magical. It handles recognizable academic signals such as objectives, research questions, methods, samples, variables, findings, limitations, and future work. It also returns `null` values and `0.0` confidence for fields it cannot find. It does not infer hidden meaning, rewrite the paper, or call an LLM. That makes the behavior safe, explainable, and useful as a fallback before future retrieval or optional AI layers are added.

## Project API

Project routes live in `backend/app/api/routes_projects.py` and are mounted under `/api/projects`. They remain thin FastAPI handlers over the project service layer.

## Document API

Document routes live in `backend/app/api/routes_documents.py`. Project-scoped document routes are mounted under `/api/projects/{project_id}/documents`; the upload route validates project existence, PDF extension, provided content type, and configured file size before calling document services. The document overview route is mounted at `/api/documents/{document_id}/overview`.

## Document Storage Boundary

The storage foundation defines safe local path helpers used by the upload endpoint. Filenames are sanitized before storage, project IDs must be positive integers, and resolved paths are checked so path traversal cannot escape the configured upload directory.

The document upload API saves PDF bytes, creates document metadata records, then attempts local extraction. Successful extraction runs deterministic text cleaning and saves separate `.extracted.txt` and `.cleaned.txt` artifacts beside the uploaded PDF. The original PDF is left untouched. Failed extraction keeps the upload successful and stores an extraction error. Very low cleaned text is marked `ocr_needed` so scanned or empty PDFs can be flagged without requiring OCR yet. Section detection runs on cleaned text and stores structured sections in a local `section_detection` analysis record. Chunking runs after section detection and replaces stored chunks transactionally. Normal successful documents become `processed` only after chunks are stored.

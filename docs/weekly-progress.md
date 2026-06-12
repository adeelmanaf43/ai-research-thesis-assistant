# Weekly Progress

## Week 1 Summary

Week 1 established the professional project foundation for the AI Research / Thesis Assistant. The project is now a local-first, testable FastAPI and Streamlit application skeleton with SQLite persistence, project management, safe PDF upload storage, documentation, and quality tooling.

The foundation intentionally avoids paid API keys, cloud providers, mandatory Ollama, Docker, authentication, and payment complexity.

## Completed Features

- Root repository structure with backend, frontend, docs, sample data, and local data folders.
- Python virtual environment workflow documented for local development.
- FastAPI application factory with root and health endpoints.
- Streamlit frontend skeleton with product status and local-first messaging.
- Environment-driven settings for app metadata, SQLite database URL, upload directory, export directory, provider mode, and upload size limit.
- SQLAlchemy SQLite connection, session dependency, declarative base, and database initialization utility.
- Base ORM models for users, projects, documents, chunks, analyses, and chat history.
- Pydantic schemas for project and document request/response contracts.
- Project CRUD service layer and `/api/projects` routes.
- Safe local document storage helpers under `data/uploads/projects/{project_id}/documents/`.
- Document service functions for saving uploaded bytes, creating metadata records, updating status, and listing project documents.
- PDF-only document upload route at `/api/projects/{project_id}/documents`.
- Tests for configuration, database setup, models, schemas, project services, project API routes, document storage, document services, document upload routes, frontend structure, documentation structure, and tooling configuration.
- Ruff and Black quality baseline.
- README, setup guide, architecture notes, API docs, API reference, known limitations, learning notes, and daily validation notes.

## Demo Steps

1. Create and activate the virtual environment:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements-dev.txt
   copy .env.example .env
   ```

2. Run the backend:

   ```powershell
   .\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload
   ```

3. Check health:

   ```powershell
   Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8000/health"
   ```

4. Create a project:

   ```powershell
   Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8000/api/projects" -Method Post -ContentType "application/json" -Body '{"name":"Thesis project","description":"Local workspace"}'
   ```

5. List projects:

   ```powershell
   Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8000/api/projects"
   ```

6. Upload a sample PDF to an existing project:

   ```powershell
   curl.exe -X POST "http://127.0.0.1:8000/api/projects/1/documents" -F "file=@sample_data\invoice_GAF-175351693.pdf;type=application/pdf"
   ```

7. Run the Streamlit frontend:

   ```powershell
   .\.venv\Scripts\python.exe -m streamlit run frontend/streamlit_app.py
   ```

8. Run the validation suite:

   ```powershell
   .\.venv\Scripts\python.exe -m pytest
   .\.venv\Scripts\python.exe -m ruff check .
   $env:BLACK_CACHE_DIR='data/test_tmp/black_cache_week1'; .\.venv\Scripts\python.exe -m black --check --workers 1 backend frontend
   ```

## Next Week Plan

Week 2 should begin document intake and local text processing without adding AI provider dependency.

Recommended sequence:

1. Wire local PDF text extraction into the document processing workflow.
2. Detect empty, unreadable, or likely scanned PDFs and return clear status messages.
3. Store page count, word count, and extraction status in document metadata.
4. Add text cleaning helpers with deterministic tests.
5. Keep extraction and cleaning logic in services, not API route modules.
6. Update API responses and docs only after each behavior is functional and tested.

## Known Week 1 Limitations

- The upload API stores PDF bytes and metadata only.
- No PDF extraction, OCR, section detection, chunking, search, Q&A, summaries, comparison, or export exists yet.
- The frontend is still a foundation screen and does not call the backend yet.
- No authentication or user permissions are implemented.
- Ollama and cloud providers are intentionally not integrated.

## Interview Summary

Week 1 proves the project is being built like a real product instead of a one-file demo. The foundation separates API routes, services, schemas, models, configuration, database setup, and tests. It also protects local user files with safe storage paths and avoids paid or cloud dependencies. This makes the future AI features easier to add because the core app already has reliable boundaries, documentation, and validation.

## Week 2 Day 1 Update

Week 2 Day 1 added the local PDF text extraction foundation.

Completed:

- Added PyMuPDF as the local PDF extraction dependency.
- Added `backend/app/services/document_extraction.py` for page text, page count, metadata, and safe extraction errors.
- Connected upload processing to extraction after local save.
- Updated document metadata with `page_count`, `word_count`, `status`, and `extraction_error`.
- Added `ocr_needed` status for empty or very low-text PDFs.
- Added tests for generated PDFs, mocked extraction, invalid paths, invalid PDF bytes, upload success, extraction failure, and OCR-needed detection.

Still not included after Day 1:

- OCR processing
- Section detection
- Chunking
- Search, Q&A, summaries, comparison, or export

## Week 2 Day 2 Update

Week 2 Day 2 started the deterministic text cleaning layer.

Completed:

- Added `backend/app/services/text_cleaning.py`.
- Added helpers for whitespace normalization, broken line repair, hyphenated line break repair, repeated page artifact removal, and control character removal.
- Added a `clean_text()` pipeline that combines the helpers locally without any AI provider.
- Added focused tests for each cleaning behavior and conservative repeated-content handling.
- Added `run_text_cleaning_pipeline()` to return original text, cleaned text, cleaning statistics, and warnings.
- Connected upload processing to save internal extracted-text and cleaned-text artifacts after successful PDF extraction.
- Preserved the original uploaded PDF while storing text artifacts separately for later pipeline stages.

Still not included:

- Exposing cleaned text through API responses
- Section detection
- Chunking
- Search, Q&A, summaries, comparison, or export

# Week 1 Day 4 Validation

Day 4 added the document file storage foundation.

## Completed Scope

- Safe upload path helpers using `uploads/projects/{project_id}/documents/`
- Filename sanitization and path traversal protection
- Document service functions for saving local file bytes, creating records, updating status, and listing documents by project
- PDF-only upload route at `POST /api/projects/{project_id}/documents`
- Upload validation for project existence, file extension, content type, and configured file size
- Tests for upload validation using small fake files
- Documentation for upload usage, storage boundaries, and security notes

## Validation Commands

Run from the project root after activating the virtual environment:

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests\test_document_storage.py
.\.venv\Scripts\python.exe -m pytest backend\tests\test_document_service.py
.\.venv\Scripts\python.exe -m pytest backend\tests\test_document_routes.py
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
```

Expected result:

```text
All tests pass.
All lint checks pass.
```

## Manual API Check

Start the backend on a clean port:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8020 --reload
```

Create a project:

```powershell
Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8020/api/projects" -Method Post -ContentType "application/json" -Body '{"name":"Thesis project"}'
```

Upload a PDF to the created project:

```powershell
curl.exe -X POST "http://127.0.0.1:8020/api/projects/1/documents" -F "file=@sample_data\invoice_GAF-175351693.pdf;type=application/pdf"
```

Expected upload result:

```text
StatusCode: 201
```

## Security Notes

- Uploaded filenames are sanitized before storage.
- Stored files stay under the configured local upload directory.
- Path traversal attempts cannot escape the configured upload directory because filenames are sanitized and resolved storage paths are checked.
- Internal storage paths are not exposed by the API response.
- Generated files under `data/uploads/` are ignored by Git.

## Known Day 4 Boundaries

- No PDF text extraction yet
- No page counting yet
- No OCR or scanned PDF handling yet
- No search, retrieval, LLM, Ollama, cloud provider, or export workflow yet
- Upload validation is intentionally lightweight and local-first for Week 1

# API Reference

This reference documents the current Week 2 API surface for the local-first AI Research / Thesis Assistant. The API works without paid API keys, cloud providers, Docker, authentication, or mandatory Ollama.

Base URL for local development:

```text
http://127.0.0.1:8000
```

## Current Endpoints

| Method   | Path                                   | Purpose                                 |
| -------- | -------------------------------------- | --------------------------------------- |
| `GET`    | `/`                                    | Basic app readiness metadata            |
| `GET`    | `/health`                              | Local health check                      |
| `GET`    | `/api/v1/health`                       | Versioned health check                  |
| `POST`   | `/api/projects`                        | Create a local research project         |
| `GET`    | `/api/projects`                        | List local research projects            |
| `GET`    | `/api/projects/{project_id}`           | Fetch one project by ID                 |
| `PATCH`  | `/api/projects/{project_id}`           | Update project name or description      |
| `DELETE` | `/api/projects/{project_id}`           | Delete a project                        |
| `GET`    | `/api/projects/{project_id}/documents` | List documents in one project           |
| `POST`   | `/api/projects/{project_id}/documents` | Upload one PDF into an existing project |
| `GET`    | `/api/documents/{document_id}/overview` | Fetch local document processing overview |

## Health

### `GET /`

Returns basic application readiness metadata.

Example request:

```powershell
Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8000/"
```

Example response:

```json
{
  "app": "AI Research / Thesis Assistant",
  "version": "0.1.0",
  "status": "ready",
  "mode": "local-first"
}
```

### `GET /health`

Returns the local health status.

Example request:

```powershell
Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8000/health"
```

Example response:

```json
{
  "status": "ok",
  "app": "AI Research / Thesis Assistant",
  "version": "0.1.0",
  "environment": "local",
  "mode": "local-first"
}
```

### `GET /api/v1/health`

Returns the same health payload through a versioned path for future integrations.

Example request:

```powershell
Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8000/api/v1/health"
```

Expected status: `200 OK`

## Projects

Project endpoints manage local research workspaces. Authentication is intentionally not required in the current local-first foundation.

### `POST /api/projects`

Creates a project.

Example request:

```powershell
Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8000/api/projects" -Method Post -ContentType "application/json" -Body '{"name":"Thesis project","description":"Local workspace"}'
```

Request body:

```json
{
  "name": "Thesis project",
  "description": "Local workspace"
}
```

Example response:

```json
{
  "id": 1,
  "user_id": null,
  "name": "Thesis project",
  "description": "Local workspace",
  "created_at": "2026-06-11T10:00:00",
  "updated_at": "2026-06-11T10:00:00"
}
```

Expected status: `201 Created`

Validation:

- `name` is required.
- Leading and trailing whitespace in `name` is stripped.
- Empty or whitespace-only names return `422 Unprocessable Entity`.

### `GET /api/projects`

Lists projects, newest first.

Example request:

```powershell
Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8000/api/projects"
```

Example response:

```json
[
  {
    "id": 1,
    "user_id": null,
    "name": "Thesis project",
    "description": "Local workspace",
    "created_at": "2026-06-11T10:00:00",
    "updated_at": "2026-06-11T10:00:00"
  }
]
```

Expected status: `200 OK`

### `GET /api/projects/{project_id}`

Returns one project by ID.

Example request:

```powershell
Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8000/api/projects/1"
```

Expected status:

- `200 OK` when the project exists.
- `404 Not Found` when the project does not exist.

Example not found response:

```json
{
  "detail": "Project not found."
}
```

### `PATCH /api/projects/{project_id}`

Updates a project name or description.

Example request:

```powershell
Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8000/api/projects/1" -Method Patch -ContentType "application/json" -Body '{"name":"Updated thesis project"}'
```

Request body:

```json
{
  "name": "Updated thesis project"
}
```

Expected status:

- `200 OK` when the project exists.
- `404 Not Found` when the project does not exist.
- `422 Unprocessable Entity` when `name` is empty or whitespace only.

### `DELETE /api/projects/{project_id}`

Deletes one project.

Example request:

```powershell
Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8000/api/projects/1" -Method Delete
```

Expected status:

- `204 No Content` when the project is deleted.
- `404 Not Found` when the project does not exist.

## Documents

Document endpoints currently support PDF upload, metadata storage, local PyMuPDF extraction, deterministic text cleaning, internal rule-based section detection, and internal chunk persistence. They do not summarize, search, or run AI analysis yet.

### `GET /api/projects/{project_id}/documents`

Lists documents for one existing project, newest first.

Example request:

```powershell
Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8000/api/projects/1/documents"
```

Example response:

```json
[
  {
    "id": 1,
    "project_id": 1,
    "original_filename": "invoice_GAF-175351693.pdf",
    "mime_type": "application/pdf",
    "file_size_bytes": 1024,
    "page_count": 1,
    "word_count": 120,
    "status": "processed",
    "extraction_error": null,
    "uploaded_at": "2026-06-11T10:00:00"
  }
]
```

Expected status:

- `200 OK` when the project exists.
- `404 Not Found` when the project does not exist.

Response boundary:

- Internal storage fields are not exposed.
- Cleaned text paths, extracted text paths, and raw chunk records are not exposed.

### `POST /api/projects/{project_id}/documents`

Uploads one PDF file into an existing project.

Example request:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/projects/1/documents" -F "file=@sample_data\invoice_GAF-175351693.pdf;type=application/pdf"
```

Request type: `multipart/form-data`

Required field:

- `file`: a PDF file

Example response:

```json
{
  "id": 1,
  "project_id": 1,
  "original_filename": "invoice_GAF-175351693.pdf",
  "mime_type": "application/pdf",
  "file_size_bytes": 1024,
  "page_count": 1,
  "word_count": 120,
  "status": "processed",
  "extraction_error": null,
  "uploaded_at": "2026-06-11T10:00:00"
}
```

Expected status:

- `201 Created` when the PDF is saved and the metadata record is created.
- `404 Not Found` when the project does not exist.
- `400 Bad Request` when the filename extension is not `.pdf`.
- `400 Bad Request` when a provided content type is not `application/pdf` or `application/x-pdf`.
- `413 Content Too Large` when the file exceeds `MAX_UPLOAD_FILE_SIZE_BYTES`.
- `422 Unprocessable Entity` when the multipart `file` field is missing.
- `500 Internal Server Error` when local storage fails.

Extraction behavior:

- Valid PDFs are parsed locally with PyMuPDF after saving.
- Successful extraction runs deterministic text cleaning, saves internal `.extracted.txt` and `.cleaned.txt` artifacts, populates `page_count`, and populates `word_count`.
- Section detection runs on cleaned text and stores structured sections in an internal `section_detection` analysis record.
- Chunking runs after section detection and stores internal chunks. Normal successful documents use `status` value `processed` only after chunks are stored.
- PDFs that save successfully but cannot be parsed still return `201 Created`.
- Extraction failures set `status` to `extraction_failed` and return `extraction_error`.
- PDFs with very little extractable text use `status` value `ocr_needed` and return an OCR warning in `extraction_error`.

Processed document lifecycle:

```text
upload PDF
  -> save original file locally
  -> create document metadata row
  -> extract text with PyMuPDF
  -> clean extracted text
  -> save internal extracted/cleaned text artifacts
  -> detect academic sections
  -> store internal section_detection analysis
  -> create overlapping chunks with section metadata
  -> replace stored chunks transactionally
  -> mark document status as processed
```

Failure status meanings:

| Status                     | Meaning                                                              |
| -------------------------- | -------------------------------------------------------------------- |
| `processed`                | Text was extracted, cleaned, sectioned, chunked, and chunks stored   |
| `ocr_needed`               | Upload saved, but very little text was extractable                   |
| `extraction_failed`        | Upload saved, but local PDF parsing failed                           |
| `text_processing_failed`   | Upload and extraction worked, but text artifact storage failed       |
| `section_detection_failed` | Cleaning worked, but section analysis storage failed                 |
| `chunking_failed`          | Section detection worked, but chunk storage failed                   |

### `GET /api/documents/{document_id}/overview`

Returns a local processing overview for one document.

Example request:

```powershell
Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8000/api/documents/1/overview"
```

Example response:

```json
{
  "document_id": 1,
  "filename": "invoice_GAF-175351693.pdf",
  "status": "processed",
  "page_count": 1,
  "word_count": 120,
  "chunk_count": 3,
  "detected_sections": [
    {
      "section_name": "Title",
      "detected_heading": "Title",
      "confidence": 0.75
    }
  ],
  "extraction_warnings": [],
  "processing_summary": {
    "status": "processed",
    "message": "Document processed locally with 1 detected sections and 3 stored chunks.",
    "is_complete": true,
    "requires_attention": false,
    "next_step": "Review the overview or continue with the next local analysis step."
  }
}
```

Expected status:

- `200 OK` when the document exists.
- `404 Not Found` when the document does not exist.
- `422 Unprocessable Entity` when the document ID is not a positive integer.

Overview behavior:

- `chunk_count` is counted from stored local chunk rows.
- `detected_sections` is read from the latest stored `section_detection` analysis.
- `extraction_warnings` combines extraction errors and cleaning warnings.
- `processing_summary` is structured for frontend use and includes status, message, completion state, attention state, and next-step guidance.
- No AI provider, Ollama model, or cloud API is called.

User-friendly errors:

- Missing documents return `Document not found. Upload a document or use an existing document ID.`
- Invalid document IDs return `Document ID must be a positive integer.`

Response boundary:

- `file_path` is intentionally not exposed.
- `stored_filename` is intentionally not exposed.
- `extracted_text_path` and `cleaned_text_path` are intentionally not exposed.
- Chunk records are intentionally not exposed through this upload response.
- The original filename is returned for user clarity.
- Saved files remain under the configured local upload directory.

## Known Limitations

- No OCR processing for scanned PDFs yet.
- Text cleaning artifacts are stored internally but are not exposed through API responses yet.
- Section detection output is exposed only as safe overview metadata, not as raw full section text.
- Section detection is rule-based and depends on extracted heading text. It can miss non-standard academic structures, merge unsupported sections into the nearest known section, or infer a weak title from the first non-empty line.
- Section confidence values are explainable heuristic scores, not statistical model confidence.
- Chunks are stored internally; only aggregate `chunk_count` is exposed through the overview response.
- No search, retrieval, RAG, Q&A, summaries, comparison, or export yet.
- No auth or permissions layer yet.
- No Ollama or cloud provider calls yet.
- Upload validation checks extension, provided content type, and configured file size before local extraction.

These limitations are intentional for Week 2. The current API establishes a stable local-first extraction foundation before document intelligence features are added.

## Manual Smoke Test

If port `8000` is already used by an old backend process, run the backend on port `8020` and verify the project and upload flow:

```powershell
Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8020/api/projects" -Method Post -ContentType "application/json" -Body '{"name":"Thesis project","description":"Local workspace"}'
```

```powershell
curl.exe -X POST "http://127.0.0.1:8020/api/projects/1/documents" -F "file=@sample_data\invoice_GAF-175351693.pdf;type=application/pdf"
```

The upload response should include `page_count`, `word_count`, `status`, and `extraction_error`.

List uploaded project documents:

```powershell
Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8020/api/projects/1/documents"
```

Fetch the document overview:

```powershell
Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8020/api/documents/1/overview"
```

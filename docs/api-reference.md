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
| `POST`   | `/api/projects/{project_id}/documents` | Upload one PDF into an existing project |

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

Document endpoints currently support PDF upload, metadata storage, local PyMuPDF extraction, deterministic text cleaning, and internal rule-based section detection. They do not chunk, summarize, search, or run AI analysis yet.

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
  "status": "extracted",
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
- Successful extraction runs deterministic text cleaning, saves internal `.extracted.txt` and `.cleaned.txt` artifacts, sets `status` to `extracted`, populates `page_count`, and populates `word_count`.
- Section detection runs on cleaned text and stores structured sections in an internal `section_detection` analysis record.
- PDFs that save successfully but cannot be parsed still return `201 Created`.
- Extraction failures set `status` to `extraction_failed` and return `extraction_error`.
- PDFs with very little extractable text use `status` value `ocr_needed` and return an OCR warning in `extraction_error`.

Response boundary:

- `file_path` is intentionally not exposed.
- `stored_filename` is intentionally not exposed.
- `extracted_text_path` and `cleaned_text_path` are intentionally not exposed.
- The original filename is returned for user clarity.
- Saved files remain under the configured local upload directory.

## Known Limitations

- No OCR processing for scanned PDFs yet.
- Text cleaning artifacts are stored internally but are not exposed through API responses yet.
- Section detection output is stored internally but is not exposed through API responses yet.
- Section detection is rule-based and depends on extracted heading text. It can miss non-standard academic structures, merge unsupported sections into the nearest known section, or infer a weak title from the first non-empty line.
- Section confidence values are explainable heuristic scores, not statistical model confidence.
- No chunking yet.
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

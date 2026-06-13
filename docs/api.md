# API Endpoints

## `GET /`

Returns a basic application readiness payload.

Example response:

```json
{
  "app": "AI Research / Thesis Assistant",
  "version": "0.1.0",
  "status": "ready",
  "mode": "local-first"
}
```

## `GET /health`

Returns the current health status for local development checks.

## `GET /api/v1/health`

Versioned health endpoint for future frontend and integration use.

## `POST /api/projects`

Creates a local project. `name` is the project title and cannot be empty or whitespace only.

PowerShell example:

```powershell
Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8000/api/projects" -Method Post -ContentType "application/json" -Body '{"name":"Thesis project","description":"Optional project notes"}'
```

Request:

```json
{
  "name": "Thesis project",
  "description": "Optional project notes"
}
```

Response status: `201 Created`

Response:

```json
{
  "id": 1,
  "user_id": null,
  "name": "Thesis project",
  "description": "Optional project notes",
  "created_at": "2026-06-10T10:00:00",
  "updated_at": "2026-06-10T10:00:00"
}
```

Validation behavior:

- Whitespace around `name` is stripped.
- Empty or whitespace-only `name` values return `422 Unprocessable Entity`.

## `GET /api/projects`

Lists local projects.

PowerShell example:

```powershell
Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8000/api/projects"
```

Response status: `200 OK`

Response:

```json
[
  {
    "id": 1,
    "user_id": null,
    "name": "Thesis project",
    "description": "Optional project notes",
    "created_at": "2026-06-10T10:00:00",
    "updated_at": "2026-06-10T10:00:00"
  }
]

```

## `GET /api/projects/{project_id}`

Returns a project by ID. Returns `404` when the project does not exist.

PowerShell example:

```powershell
Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8000/api/projects/1"
```

Response status: `200 OK`

## `PATCH /api/projects/{project_id}`

Updates project name or description. `name` cannot be empty or whitespace only. Returns `404` when the project does not exist.

PowerShell example:

```powershell
Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8000/api/projects/1" -Method Patch -ContentType "application/json" -Body '{"name":"Updated thesis project"}'
```

Response status: `200 OK`

## `DELETE /api/projects/{project_id}`

Deletes a project. Returns `204` on success and `404` when the project does not exist.

PowerShell example:

```powershell
Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8000/api/projects/1" -Method Delete
```

Response status: `204 No Content`

## `POST /api/projects/{project_id}/documents`

Uploads one PDF document into an existing project.

PowerShell example:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/projects/1/documents" -F "file=@sample_data\invoice_GAF-175351693.pdf;type=application/pdf"
```

Request type: `multipart/form-data`

Required field:

- `file`: PDF file

Response status: `201 Created`

Response:

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

Validation behavior:

- Missing projects return `404 Not Found`.
- Non-`.pdf` filenames return `400 Bad Request`.
- Non-PDF content types return `400 Bad Request` when the content type is provided.
- Oversized files return `413 Content Too Large`.
- Valid PDFs are saved, parsed locally with PyMuPDF, cleaned deterministically, and stored as internal extracted/cleaned text artifacts.
- Detected sections are stored internally as a local `section_detection` analysis record.
- Section detection is rule-based and depends on clear extracted headings; unusual heading names, badly extracted layout, or unsupported sections may be classified as unknown or kept inside the nearest known section.
- Chunks are stored internally after section detection; normal successful uploads return `status="processed"` only after chunk persistence succeeds.
- Chunk persistence failures do not crash the upload; the response uses `status="chunking_failed"` and includes `extraction_error`.
- Extraction failures do not fail the upload; the response uses `status="extraction_failed"` and includes `extraction_error`.
- PDFs with very little extractable text use `status="ocr_needed"` and include an OCR warning in `extraction_error`.
- Internal storage fields such as `file_path`, `stored_filename`, `extracted_text_path`, `cleaned_text_path`, and chunk records are not exposed in the response.

Processed document lifecycle:

```text
upload -> save PDF -> create metadata -> extract -> clean -> save text artifacts -> detect sections -> store section analysis -> chunk -> replace chunks -> processed
```

Current document status values:

- `processed`: local extraction, cleaning, section detection, and chunk storage completed.
- `ocr_needed`: the PDF was saved, but too little text was extracted for reliable downstream use.
- `extraction_failed`: the PDF was saved, but local parsing failed.
- `text_processing_failed`: extraction worked, but text artifacts could not be saved.
- `section_detection_failed`: cleaning worked, but section analysis could not be saved.
- `chunking_failed`: section detection worked, but chunk persistence failed.

## `GET /api/projects/{project_id}/documents`

Lists documents for one existing project, newest first.

PowerShell example:

```powershell
Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8000/api/projects/1/documents"
```

Response status:

- `200 OK` when the project exists.
- `404 Not Found` when the project does not exist.

The response uses the public document metadata shape and does not expose internal storage paths.

## `GET /api/documents/{document_id}/overview`

Returns the local processing overview for one document.

PowerShell example:

```powershell
Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8000/api/documents/1/overview"
```

Response status:

- `200 OK` when the document exists.
- `404 Not Found` when the document does not exist.
- `422 Unprocessable Entity` when the document ID is not positive.

Response:

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

## Current API Boundaries

The Project and Document APIs are local-first and do not require authentication in the current MVP. Project ownership is represented by nullable `user_id` fields in the database, but login and permissions are intentionally out of scope for the current foundation.

The document upload endpoint stores the PDF, creates metadata, attempts local text extraction, writes internal raw/cleaned text artifacts, stores rule-based section detection output as local analysis data, and persists internal chunks. The overview endpoint exposes safe processing metadata, section names, warnings, aggregate chunk count, and structured user-facing processing summary. It does not run search, call Ollama, call cloud APIs, summarize, or generate reports. Those workflows belong to later milestones.

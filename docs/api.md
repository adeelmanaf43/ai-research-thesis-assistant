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
curl.exe -X POST "http://127.0.0.1:8000/api/projects/1/documents" -F "file=@sample_data\example.pdf;type=application/pdf"
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
  "original_filename": "example.pdf",
  "mime_type": "application/pdf",
  "file_size_bytes": 1024,
  "page_count": null,
  "word_count": null,
  "status": "stored",
  "uploaded_at": "2026-06-11T10:00:00"
}
```

Validation behavior:

- Missing projects return `404 Not Found`.
- Non-`.pdf` filenames return `400 Bad Request`.
- Non-PDF content types return `400 Bad Request` when the content type is provided.
- Oversized files return `413 Content Too Large`.
- Internal storage fields such as `file_path` and `stored_filename` are not exposed in the response.

## Current API Boundaries

The Project and Document APIs are local-first and do not require authentication in the Week 1 MVP. Project ownership is represented by nullable `user_id` fields in the database, but login and permissions are intentionally out of scope for Day 4.

The document upload endpoint stores the PDF and creates metadata only. It does not extract text, count pages, run search, call Ollama, call cloud APIs, or generate reports. Those workflows belong to later milestones.

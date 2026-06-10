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

## Current API Boundaries

The Project API is local-first and does not require authentication in the Week 1 MVP. Project ownership is represented by nullable `user_id` fields in the database, but login and permissions are intentionally out of scope for Day 3.

These endpoints do not upload documents, run extraction, call Ollama, call cloud APIs, or generate reports. Those workflows belong to later milestones.

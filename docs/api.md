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


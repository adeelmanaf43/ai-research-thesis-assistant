# Usage Guide

This milestone contains the project skeleton, backend configuration, database foundation, Project CRUD API, and PDF-only document upload foundation.

Current useful actions:

- Start the backend and confirm `/health` returns `ok`
- Create, list, view, update, and delete local projects through `/api/projects`
- Upload a PDF document to an existing project through `/api/projects/{project_id}/documents`
- Start the Streamlit frontend and confirm the foundation page shows the app title, product description, MVP status, and backend connection placeholder
- Run the test suite before committing changes

Example project creation request:

```powershell
Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8000/api/projects" -Method Post -ContentType "application/json" -Body '{"name":"Thesis project","description":"Local workspace"}'
```

Example PDF upload request:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/projects/1/documents" -F "file=@sample_data\invoice_GAF-175351693.pdf;type=application/pdf"
```

PDF extraction, analysis, search, Q&A, comparison, and export are intentionally not implemented yet.

# Usage Guide

This milestone contains the project skeleton, backend configuration, database foundation, Project CRUD API, safe PDF upload, and local PDF text extraction foundation.

Current useful actions:

- Start the backend and confirm `/health` returns `ok`
- Create, list, view, update, and delete local projects through `/api/projects`
- Upload a PDF document to an existing project through `/api/projects/{project_id}/documents`
- Receive extraction metadata such as page count, word count, status, and extraction warnings
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

Text cleaning runs after successful extraction and saves internal raw/cleaned text artifacts for later processing, but those internal paths are not exposed through API responses. Section detection runs after cleaning and stores internal local analysis output, but sections are not exposed through API responses yet. The detector is rule-based, so it works best with clear academic headings and can miss unusual or poorly extracted section labels. Chunking runs after section detection and replaces stored chunks transactionally, but chunks are not exposed through API responses yet. Search, Q&A, comparison, OCR processing, and export are intentionally not implemented yet.

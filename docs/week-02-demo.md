# Week 2 Demo

This demo shows the local-first document ingestion pipeline working end to end. It does not require paid API keys, cloud providers, Docker, authentication, or Ollama.

## What This Demo Proves

- A user can create a local research project.
- A PDF can be uploaded into project-scoped local storage.
- The backend extracts text locally with PyMuPDF.
- The backend cleans text deterministically.
- The backend detects academic sections with rule-based logic.
- The backend creates and stores chunks.
- The backend exposes a safe document overview.
- Streamlit can display the overview when the backend is running.

## Prerequisites

Run these commands from the repository root:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
```

Confirm the sample file exists:

```powershell
Test-Path sample_data\invoice_GAF-175351693.pdf
```

Expected result:

```text
True
```

## 1. Start Backend

Use port `8020` for the demo to avoid conflicts with older backend processes:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8020 --reload
```

Expected result:

```text
Uvicorn running on http://127.0.0.1:8020
```

Open a second PowerShell window for the remaining commands.

## 2. Check Health

```powershell
Invoke-RestMethod "http://127.0.0.1:8020/health"
```

Expected result:

```text
status : ok
mode   : local-first
```

## 3. Create Project

```powershell
$project = Invoke-RestMethod "http://127.0.0.1:8020/api/projects" -Method Post -ContentType "application/json" -Body '{"name":"Week 2 Demo Project","description":"Local document processing demo"}'
$project
```

Expected result:

```text
id          : 1
name        : Week 2 Demo Project
description : Local document processing demo
```

Save the project ID:

```powershell
$projectId = $project.id
```

## 4. Upload PDF

```powershell
$uploadJson = curl.exe -s -X POST "http://127.0.0.1:8020/api/projects/$projectId/documents" -F "file=@sample_data\invoice_GAF-175351693.pdf;type=application/pdf"
$upload = $uploadJson | ConvertFrom-Json
$upload
```

Expected result for a text-based PDF:

```text
status      : processed
page_count  : 1
word_count  : 101
```

Possible valid alternative:

```text
status : ocr_needed
```

That means the PDF was saved but very little text was extractable.

Save the document ID:

```powershell
$documentId = $upload.id
```

## 5. List Project Documents

```powershell
Invoke-RestMethod "http://127.0.0.1:8020/api/projects/$projectId/documents"
```

Expected result:

```text
original_filename : invoice_GAF-175351693.pdf
status            : processed
```

The response intentionally does not expose `file_path`, `stored_filename`, `.extracted.txt`, or `.cleaned.txt` paths.

## 6. Fetch Document Overview

```powershell
$overview = Invoke-RestMethod "http://127.0.0.1:8020/api/documents/$documentId/overview"
$overview
```

Expected result:

```text
filename       : invoice_GAF-175351693.pdf
status         : processed
page_count     : 1
word_count     : 101
chunk_count    : 1
```

Inspect the structured summary:

```powershell
$overview.processing_summary
```

Expected result:

```text
status             : processed
is_complete        : True
requires_attention : False
```

Inspect detected sections:

```powershell
$overview.detected_sections
```

Expected result:

```text
section_name
------------
Title
```

Detected sections depend on the document text and extracted headings. A document with academic headings should expose more section metadata.

## 7. Open Streamlit Overview

Start Streamlit:

```powershell
.\.venv\Scripts\streamlit.exe run frontend/streamlit_app.py
```

Expected result:

```text
Local URL: http://localhost:8501
```

In the Streamlit page:

1. Enter backend URL `http://127.0.0.1:8020`.
2. Enter the document ID from `$documentId`.
3. Select `Load Overview`.

Expected UI result:

- Filename appears.
- Status, pages, words, and chunks appear as metrics.
- Processing summary appears.
- Warnings appear only when needed.
- Detected sections appear when available.

## 8. Run Automated Validation

Run the dedicated integration test:

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests/test_week2_processing_integration.py -vv
```

Expected result:

```text
3 passed
```

Run the full suite:

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
$env:BLACK_CACHE_DIR='data/test_tmp/black_cache_week2_demo'; .\.venv\Scripts\python.exe -m black --check --workers 1 backend frontend
```

Expected result:

```text
190 passed
All checks passed!
54 files would be left unchanged.
```

## Demo Talking Points

- The app remains useful without paid APIs or AI providers because extraction, cleaning, section detection, chunking, and overview are local.
- Upload responses are resilient: corrupt PDFs become `extraction_failed`, low-text PDFs become `ocr_needed`, and successful documents become `processed`.
- Internal paths and raw chunks are not exposed through public responses.
- The automated integration test proves the pipeline through public API calls and verifies local database side effects.

## Cleanup

Manual demo uploads are stored under `data/uploads/`, which is ignored by Git. You can keep them for local testing or remove generated demo data later.

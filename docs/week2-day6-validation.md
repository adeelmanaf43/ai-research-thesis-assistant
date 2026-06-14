# Week 2 Day 6 Validation

Day 6 validates that the Week 2 local document processing pieces work together as one pipeline.

## Scope Validated

- Create a project through the public API.
- Upload a text-based PDF through the public API.
- Save the original PDF under local project-scoped storage.
- Extract text locally with PyMuPDF.
- The pipeline can extract text locally with PyMuPDF without paid APIs.
- Clean extracted text deterministically.
- Detect academic sections from cleaned text.
- Store section detection output as local analysis.
- Create and store document chunks.
- Return processed document metadata.
- List documents for the project.
- Fetch the document overview.

## Edge Cases Covered

The Week 2 integration and route tests cover these hardening cases:

| Edge case | Expected behavior |
| --- | --- |
| Non-PDF upload | Request returns `400 Bad Request` before storage |
| Missing project | Request returns `404 Not Found` before storage |
| Corrupt PDF | File is saved, document row remains, status becomes `extraction_failed` |
| Empty or scanned-like PDF | File is saved, status becomes `ocr_needed` |
| Database rollback during chunk replacement | Existing chunks are preserved |
| Duplicate same-name uploads | Each upload creates a separate document record |
| Long document processing | Long extracted text creates multiple stored chunks |

Hour 3 also fixed a cleaning edge case where academic headings such as `Abstract` and `Methodology` could be merged into following lowercase text. The cleaner now preserves known academic heading lines before section detection runs.

## Automated Test

The automated upload-to-overview integration test covers the full local pipeline.

Run the dedicated integration test:

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests/test_week2_processing_integration.py -vv
```

Expected result:

```text
3 passed
```

The test generates a local text-based PDF in memory, uses the FastAPI ASGI app directly, writes only to a temporary SQLite database under `data/test_tmp`, and does not require a running server.

## Manual Verification

Start the backend:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8020 --reload
```

Create a project:

```powershell
Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8020/api/projects" -Method Post -ContentType "application/json" -Body '{"name":"Integration thesis project","description":"Week 2 manual validation"}'
```

Upload the sample PDF:

```powershell
curl.exe -X POST "http://127.0.0.1:8020/api/projects/1/documents" -F "file=@sample_data\invoice_GAF-175351693.pdf;type=application/pdf"
```

List project documents:

```powershell
Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8020/api/projects/1/documents"
```

Fetch the document overview:

```powershell
Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8020/api/documents/1/overview"
```

Expected response behavior:

- Upload returns `201 Created`.
- A successful text-based PDF uses `status` value `processed`.
- Low-text or scanned-like PDFs use `status` value `ocr_needed`.
- Overview includes filename, status, page count, word count, chunk count, detected sections, warnings, and structured processing summary.

## Notes

- OCR, search, Q&A, summaries, comparison, and export are still outside this milestone.
- Uploaded manual files stay under `data/uploads/` and are ignored by Git.
- The automated test uses a generated PDF so private local PDFs are not required.

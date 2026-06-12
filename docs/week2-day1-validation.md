# Week 2 Day 1 Validation

Week 2 Day 1 adds the local PDF text extraction service and connects upload processing to extraction metadata updates.

## Scope Completed

- Added PyMuPDF as a local runtime dependency.
- Added `backend/app/services/document_extraction.py`.
- Extracted page count, basic metadata, per-page text, combined text, and `has_text`.
- Connected `POST /api/projects/{project_id}/documents` to extraction after saving the PDF.
- Updated document records with `page_count`, `word_count`, `status`, and `extraction_error`.
- Added graceful fallback for invalid or unreadable PDFs with `status="extraction_failed"`.
- Added low-text detection with `status="ocr_needed"` for likely scanned or empty PDFs.
- Kept OCR, text cleaning, chunking, search, and AI providers out of scope.

## Validation Commands

```powershell
.\.venv\Scripts\pip.exe install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
$env:BLACK_CACHE_DIR='data/test_tmp/black_cache_week2_day1_final'; .\.venv\Scripts\python.exe -m black --check --workers 1 backend frontend
```

## Expected Results

- Pytest reports all tests passing.
- Ruff reports `All checks passed!`.
- Black reports all checked files would be left unchanged.

## Manual Verification

1. Start the backend:

   ```powershell
   .\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8020 --reload
   ```

2. Create a project:

   ```powershell
   Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8020/api/projects" -Method Post -ContentType "application/json" -Body '{"name":"Extraction test"}'
   ```

3. Upload the sample PDF:

   ```powershell
   curl.exe -X POST "http://127.0.0.1:8020/api/projects/1/documents" -F "file=@sample_data\invoice_GAF-175351693.pdf;type=application/pdf"
   ```

4. Confirm the response includes `page_count`, `word_count`, `status`, and `extraction_error`.

## Notes

- Use a clean port such as `8020` if port `8000` is already occupied by an old server process.
- Invalid PDFs should still save successfully and return `status="extraction_failed"`.
- Very low-text PDFs should return `status="ocr_needed"` without requiring OCR.

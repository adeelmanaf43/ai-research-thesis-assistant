# Known Limitations

- PDF upload attempts local PyMuPDF extraction after saving, but it does not clean, chunk, summarize, or analyze text yet
- OCR processing for scanned PDFs is not implemented yet; low-text PDFs are only marked `ocr_needed`
- No search or retrieval yet
- No LLM provider integration yet
- No report export yet
- No frontend/backend API calls yet

These limitations are intentional for the current Week 2 foundation. They keep the MVP local-first and focused before document intelligence features are added.

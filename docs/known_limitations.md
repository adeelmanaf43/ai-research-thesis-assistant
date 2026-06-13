# Known Limitations

- PDF upload attempts local PyMuPDF extraction and deterministic cleaning after saving, but cleaned text is not exposed through API responses yet
- Text cleaning helpers are deterministic and conservative; warnings are informational and do not perform semantic rewriting
- OCR processing for scanned PDFs is not implemented yet; low-text PDFs are only marked `ocr_needed`
- Section detection output is stored internally but is not exposed through API responses yet
- Section detection is rule-based and heading-driven; it can miss unusual headings, infer weak titles, or misclassify content when PDFs extract headings poorly
- Section confidence scores are simple deterministic signals, not machine-learned probabilities
- Chunks are persisted internally during upload processing but are not exposed through API responses yet
- No search or retrieval yet
- No LLM provider integration yet
- No report export yet
- No frontend/backend API calls yet

These limitations are intentional for the current Week 2 foundation. They keep the MVP local-first and focused before document intelligence features are added.

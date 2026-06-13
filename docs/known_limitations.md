# Known Limitations

- PDF upload attempts local PyMuPDF extraction and deterministic cleaning after saving, but cleaned text is not exposed through API responses yet
- Text cleaning helpers are deterministic and conservative; warnings are informational and do not perform semantic rewriting
- OCR processing for scanned PDFs is not implemented yet; low-text PDFs are only marked `ocr_needed`
- Section detection full text is stored internally; only safe section metadata is exposed through the document overview response
- Section detection is rule-based and heading-driven; it can miss unusual headings, infer weak titles, or misclassify content when PDFs extract headings poorly
- Section confidence scores are simple deterministic signals, not machine-learned probabilities
- Chunks are persisted internally during upload processing; only aggregate `chunk_count` is exposed through the document overview response
- No search or retrieval yet
- No LLM provider integration yet
- No report export yet
- The frontend can load document overview data, but full frontend project creation, upload, and document management workflows are not implemented yet

These limitations are intentional for the current Week 2 foundation. They keep the MVP local-first and focused before document intelligence features are added.

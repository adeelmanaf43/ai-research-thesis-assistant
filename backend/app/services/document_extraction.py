from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import fitz
except ImportError:  # pragma: no cover - only reached before dependencies are installed.
    fitz = None


class PDFExtractionError(RuntimeError):
    """Raised when local PDF text extraction cannot complete safely."""


class PDFExtractionDependencyError(PDFExtractionError):
    """Raised when PyMuPDF is not installed in the active environment."""


@dataclass(frozen=True)
class ExtractedPDF:
    page_count: int
    metadata: dict[str, str]
    page_texts: list[str]

    @property
    def full_text(self) -> str:
        return "\n\n".join(page_text for page_text in self.page_texts if page_text)

    @property
    def has_text(self) -> bool:
        return bool(self.full_text.strip())


def _require_pymupdf() -> Any:
    if fitz is None:
        raise PDFExtractionDependencyError(
            "PyMuPDF is required for local PDF extraction. Install project requirements first."
        )
    return fitz


def _clean_metadata(raw_metadata: dict[str, Any] | None) -> dict[str, str]:
    if not raw_metadata:
        return {}

    cleaned_metadata: dict[str, str] = {}
    for key, value in raw_metadata.items():
        if value is None:
            continue
        text_value = str(value).strip()
        if text_value:
            cleaned_metadata[key] = text_value
    return cleaned_metadata


def extract_pdf_text(pdf_path: Path | str) -> ExtractedPDF:
    pdf_library = _require_pymupdf()
    resolved_path = Path(pdf_path)
    if not resolved_path.exists():
        raise PDFExtractionError(f"PDF file does not exist: {resolved_path}")
    if not resolved_path.is_file():
        raise PDFExtractionError(f"PDF path is not a file: {resolved_path}")

    try:
        with pdf_library.open(resolved_path) as document:
            page_texts = [(page.get_text("text") or "").strip() for page in document]
            return ExtractedPDF(
                page_count=document.page_count,
                metadata=_clean_metadata(document.metadata),
                page_texts=page_texts,
            )
    except PDFExtractionError:
        raise
    except Exception as exc:
        raise PDFExtractionError(f"Could not extract text from PDF: {resolved_path}") from exc

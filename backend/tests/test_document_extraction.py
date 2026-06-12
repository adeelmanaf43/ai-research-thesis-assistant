from pathlib import Path

import fitz
import pytest

from backend.app.services.document_extraction import PDFExtractionError, extract_pdf_text


def _create_pdf(path: Path, page_texts: list[str], metadata: dict[str, str] | None = None) -> None:
    document = fitz.open()
    if metadata:
        document.set_metadata(metadata)

    for page_text in page_texts:
        page = document.new_page()
        if page_text:
            page.insert_text((72, 72), page_text)

    document.save(path)
    document.close()


def test_extract_pdf_text_returns_page_count_metadata_and_page_texts(
    workspace_tmp_path: Path,
) -> None:
    pdf_path = workspace_tmp_path / "research-paper.pdf"
    _create_pdf(
        pdf_path,
        ["Introduction to local extraction", "Methods and results"],
        metadata={"title": "Local PDF Test", "author": "Researcher"},
    )

    extracted = extract_pdf_text(pdf_path)

    assert extracted.page_count == 2
    assert extracted.metadata["title"] == "Local PDF Test"
    assert extracted.metadata["author"] == "Researcher"
    assert extracted.page_texts == ["Introduction to local extraction", "Methods and results"]
    assert "Introduction to local extraction" in extracted.full_text
    assert "Methods and results" in extracted.full_text
    assert extracted.has_text is True


def test_extract_pdf_text_handles_pages_without_text(workspace_tmp_path: Path) -> None:
    pdf_path = workspace_tmp_path / "empty-page.pdf"
    _create_pdf(pdf_path, [""])

    extracted = extract_pdf_text(pdf_path)

    assert extracted.page_count == 1
    assert extracted.page_texts == [""]
    assert extracted.full_text == ""
    assert extracted.has_text is False


def test_extract_pdf_text_rejects_missing_file(workspace_tmp_path: Path) -> None:
    missing_pdf = workspace_tmp_path / "missing.pdf"

    with pytest.raises(PDFExtractionError, match="PDF file does not exist"):
        extract_pdf_text(missing_pdf)


def test_extract_pdf_text_rejects_directory_path(workspace_tmp_path: Path) -> None:
    directory_path = workspace_tmp_path / "not-a-file.pdf"
    directory_path.mkdir()

    with pytest.raises(PDFExtractionError, match="PDF path is not a file"):
        extract_pdf_text(directory_path)


def test_extract_pdf_text_wraps_invalid_pdf_errors(workspace_tmp_path: Path) -> None:
    invalid_pdf = workspace_tmp_path / "not-a-real.pdf"
    invalid_pdf.write_text("not a pdf", encoding="utf-8")

    with pytest.raises(PDFExtractionError, match="Could not extract text from PDF"):
        extract_pdf_text(invalid_pdf)

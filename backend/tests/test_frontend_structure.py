from pathlib import Path
from urllib.error import URLError

from frontend import streamlit_app

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_APP = PROJECT_ROOT / "frontend" / "streamlit_app.py"
PAGES_DIR = PROJECT_ROOT / "frontend" / "pages"


def test_hour_three_streamlit_skeleton_exists() -> None:
    assert FRONTEND_APP.exists()
    assert PAGES_DIR.exists()


def test_streamlit_app_shows_required_foundation_content() -> None:
    source = FRONTEND_APP.read_text(encoding="utf-8")

    assert "AI Research / Thesis Assistant" in source
    assert "local-first research workspace" in source
    assert "MVP status" in source
    assert "Week 3 local analysis foundation" in source
    assert "document overview" in source
    assert "section summaries" in source
    assert "Backend Document Overview" in source
    assert "Load Overview" in source
    assert "does not require paid API keys" in source


def test_document_overview_url_uses_backend_base_url() -> None:
    assert streamlit_app.build_document_overview_url("http://127.0.0.1:8020/", 7) == (
        "http://127.0.0.1:8020/api/documents/7/overview"
    )


def test_document_section_summaries_url_uses_backend_base_url() -> None:
    assert streamlit_app.build_document_section_summaries_url("http://127.0.0.1:8020/", 7) == (
        "http://127.0.0.1:8020/api/documents/7/summaries/sections"
    )


def test_fetch_document_overview_rejects_invalid_document_id() -> None:
    overview, error = streamlit_app.fetch_document_overview("http://127.0.0.1:8020", 0)

    assert overview is None
    assert error == "Enter a positive document ID."


def test_fetch_document_section_summaries_rejects_invalid_document_id() -> None:
    summaries, error = streamlit_app.fetch_document_section_summaries(
        "http://127.0.0.1:8020",
        0,
    )

    assert summaries is None
    assert error == "Enter a positive document ID."


def test_fetch_document_overview_parses_backend_payload(monkeypatch) -> None:
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self) -> bytes:
            return b'{"document_id": 1, "filename": "paper.pdf"}'

    def fake_urlopen(request, timeout):
        assert request.full_url == "http://127.0.0.1:8020/api/documents/1/overview"
        assert timeout == streamlit_app.REQUEST_TIMEOUT_SECONDS
        return FakeResponse()

    monkeypatch.setattr(streamlit_app, "urlopen", fake_urlopen)

    overview, error = streamlit_app.fetch_document_overview("http://127.0.0.1:8020", 1)

    assert error is None
    assert overview == {"document_id": 1, "filename": "paper.pdf"}


def test_fetch_document_section_summaries_parses_backend_payload(monkeypatch) -> None:
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self) -> bytes:
            return (
                b'{"document_id": 1, "summaries": [{"section_name": "Results", '
                b'"summary": "Local summary."}], "source_section_names": ["Results"], '
                b'"limitations": []}'
            )

    def fake_urlopen(request, timeout):
        assert request.full_url == "http://127.0.0.1:8020/api/documents/1/summaries/sections"
        assert timeout == streamlit_app.REQUEST_TIMEOUT_SECONDS
        return FakeResponse()

    monkeypatch.setattr(streamlit_app, "urlopen", fake_urlopen)

    summaries, error = streamlit_app.fetch_document_section_summaries(
        "http://127.0.0.1:8020",
        1,
    )

    assert error is None
    assert summaries is not None
    assert summaries["summaries"][0]["section_name"] == "Results"
    assert summaries["summaries"][0]["summary"] == "Local summary."


def test_fetch_document_overview_handles_backend_connection_error(monkeypatch) -> None:
    def fake_urlopen(*args, **kwargs):
        raise URLError("connection refused")

    monkeypatch.setattr(streamlit_app, "urlopen", fake_urlopen)

    overview, error = streamlit_app.fetch_document_overview("http://127.0.0.1:8020", 1)

    assert overview is None
    assert error == "Could not connect to the backend. Confirm FastAPI is running."


def test_fetch_document_section_summaries_handles_backend_connection_error(monkeypatch) -> None:
    def fake_urlopen(*args, **kwargs):
        raise URLError("connection refused")

    monkeypatch.setattr(streamlit_app, "urlopen", fake_urlopen)

    summaries, error = streamlit_app.fetch_document_section_summaries(
        "http://127.0.0.1:8020",
        1,
    )

    assert summaries is None
    assert error == "Could not connect to the backend. Confirm FastAPI is running."


def test_pages_folder_is_empty_except_gitkeep() -> None:
    visible_page_files = [path.name for path in PAGES_DIR.iterdir() if path.name != ".gitkeep"]

    assert visible_page_files == []

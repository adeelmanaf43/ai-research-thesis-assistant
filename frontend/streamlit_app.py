from __future__ import annotations

import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import streamlit as st

APP_TITLE = "AI Research / Thesis Assistant"
PRODUCT_DESCRIPTION = (
    "A local-first research workspace for students, thesis writers, academic "
    "freelancers, and analysts."
)
MVP_STATUS = (
    "MVP status: Week 2 document ingestion foundation is in progress. Project CRUD, "
    "local SQLite setup, PDF upload, extraction, cleaning, section detection, "
    "chunking, and document overview are available; search, Q&A, and export are "
    "intentionally not built yet."
)
BACKEND_CONNECTION_PLACEHOLDER = (
    "Start the FastAPI backend separately, then enter a document ID to load its "
    "local processing overview."
)
LOCAL_FIRST_NOTE = (
    "This project does not require paid API keys, cloud providers, or mandatory Ollama "
    "for the MVP foundation."
)
DEFAULT_BACKEND_URL = os.getenv("THESIS_ASSISTANT_BACKEND_URL", "http://127.0.0.1:8000")
REQUEST_TIMEOUT_SECONDS = 3


def normalize_backend_url(base_url: str) -> str:
    cleaned_url = base_url.strip().rstrip("/")
    return cleaned_url or DEFAULT_BACKEND_URL


def build_document_overview_url(base_url: str, document_id: int) -> str:
    return f"{normalize_backend_url(base_url)}/api/documents/{document_id}/overview"


def _friendly_http_error(exc: HTTPError) -> str:
    try:
        payload = json.loads(exc.read().decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return f"Backend returned HTTP {exc.code}."

    detail = payload.get("detail") if isinstance(payload, dict) else None
    if isinstance(detail, str) and detail.strip():
        return detail.strip()
    return f"Backend returned HTTP {exc.code}."


def fetch_document_overview(
    base_url: str,
    document_id: int,
) -> tuple[dict[str, Any] | None, str | None]:
    if document_id <= 0:
        return None, "Enter a positive document ID."

    request = Request(
        build_document_overview_url(base_url, document_id),
        headers={"Accept": "application/json"},
    )
    try:
        with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        return None, _friendly_http_error(exc)
    except (TimeoutError, URLError):
        return None, "Could not connect to the backend. Confirm FastAPI is running."
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None, "Backend response was not valid JSON."

    if not isinstance(payload, dict):
        return None, "Backend response did not match the overview format."
    return payload, None


def render_document_overview(overview: dict[str, Any]) -> None:
    st.success("Document overview loaded from the local backend.")
    st.write(f"**Filename:** {overview.get('filename', 'Unknown')}")

    status = str(overview.get("status", "unknown"))
    page_count = overview.get("page_count")
    word_count = overview.get("word_count")
    chunk_count = overview.get("chunk_count")
    metric_columns = st.columns(4)
    metric_columns[0].metric("Status", status)
    metric_columns[1].metric("Pages", page_count if page_count is not None else "Unknown")
    metric_columns[2].metric("Words", word_count if word_count is not None else "Unknown")
    metric_columns[3].metric("Chunks", chunk_count if chunk_count is not None else 0)

    summary = overview.get("processing_summary")
    if isinstance(summary, dict):
        st.write(summary.get("message", "No processing summary available."))
        if summary.get("requires_attention"):
            st.warning(summary.get("next_step") or "Review this document before continuing.")
        elif summary.get("next_step"):
            st.caption(summary["next_step"])

    warnings = overview.get("extraction_warnings") or []
    if warnings:
        st.warning("\n".join(str(warning) for warning in warnings))

    sections = overview.get("detected_sections") or []
    if sections:
        st.dataframe(sections, hide_index=True, use_container_width=True)
    else:
        st.info("No detected sections are available for this document yet.")


def render_backend_overview_panel() -> None:
    st.subheader("Backend Document Overview")
    st.write(BACKEND_CONNECTION_PLACEHOLDER)

    backend_url = st.text_input("Backend URL", value=DEFAULT_BACKEND_URL)
    document_id = st.number_input("Document ID", min_value=1, value=1, step=1)

    if st.button("Load Overview"):
        overview, error = fetch_document_overview(backend_url, int(document_id))
        if error:
            st.error(error)
            return
        if overview is not None:
            render_document_overview(overview)


def render_app() -> None:
    st.set_page_config(
        page_title=APP_TITLE,
        layout="wide",
    )

    st.title(APP_TITLE)
    st.caption("Local-first document intelligence workspace")
    st.write(PRODUCT_DESCRIPTION)

    st.subheader("MVP Status")
    st.info(MVP_STATUS)

    render_backend_overview_panel()

    st.subheader("Local-First Promise")
    st.write(LOCAL_FIRST_NOTE)


if __name__ == "__main__":
    render_app()

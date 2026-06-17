from __future__ import annotations

import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import streamlit as st

APP_TITLE = "AI Research / Thesis Assistant"
PRODUCT_DESCRIPTION = (
    "A local-first research workspace for students, thesis writers, academic "
    "freelancers, and analysts."
)
MVP_STATUS = (
    "MVP status: Week 3 local analysis foundation is in progress. Project CRUD, "
    "local SQLite setup, PDF upload, extraction, cleaning, section detection, "
    "chunking, document overview, keyword/statistics analysis, and extractive "
    "section summaries, local search, and source-grounded Q&A fallback are "
    "available; export is intentionally not built yet."
)
BACKEND_CONNECTION_PLACEHOLDER = (
    "Start the FastAPI backend separately, then enter a document ID to load its "
    "local processing overview, section summaries, search results, and Q&A."
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


def build_document_section_summaries_url(base_url: str, document_id: int) -> str:
    return f"{normalize_backend_url(base_url)}/api/documents/{document_id}/summaries/sections"


def build_document_search_url(base_url: str, document_id: int, query: str, top_k: int) -> str:
    params = urlencode({"q": query, "top_k": top_k})
    return f"{normalize_backend_url(base_url)}/api/documents/{document_id}/search?{params}"


def build_document_chat_url(base_url: str, document_id: int) -> str:
    return f"{normalize_backend_url(base_url)}/api/documents/{document_id}/chat"


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


def fetch_document_section_summaries(
    base_url: str,
    document_id: int,
) -> tuple[dict[str, Any] | None, str | None]:
    if document_id <= 0:
        return None, "Enter a positive document ID."

    request = Request(
        build_document_section_summaries_url(base_url, document_id),
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
        return None, "Backend response did not match the section summaries format."
    return payload, None


def fetch_document_search(
    base_url: str,
    document_id: int,
    query: str,
    top_k: int,
) -> tuple[list[dict[str, Any]] | None, str | None]:
    if document_id <= 0:
        return None, "Enter a positive document ID."
    if not query.strip():
        return None, "Enter a search query."

    request = Request(
        build_document_search_url(base_url, document_id, query.strip(), top_k),
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

    if not isinstance(payload, list):
        return None, "Backend response did not match the search results format."
    return payload, None


def ask_document_question(
    base_url: str,
    document_id: int,
    question: str,
    top_k: int,
) -> tuple[dict[str, Any] | None, str | None]:
    if document_id <= 0:
        return None, "Enter a positive document ID."
    if not question.strip():
        return None, "Enter a question."

    body = json.dumps({"question": question.strip(), "top_k": top_k}).encode("utf-8")
    request = Request(
        build_document_chat_url(base_url, document_id),
        data=body,
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        method="POST",
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
        return None, "Backend response did not match the chat answer format."
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


def render_section_summaries(section_summaries: dict[str, Any] | None) -> None:
    st.subheader("Section Summaries")
    if not section_summaries:
        st.info("No section summary response is available yet.")
        return

    limitations = section_summaries.get("limitations") or []
    summaries = section_summaries.get("summaries") or []

    if not summaries:
        st.info("No section summaries are available for this document yet.")
    else:
        for summary in summaries:
            if not isinstance(summary, dict):
                continue
            section_name = summary.get("section_name", "Unknown section")
            confidence = summary.get("confidence")
            caption_parts = []
            if confidence is not None:
                caption_parts.append(f"Confidence: {confidence}")
            source_indexes = summary.get("source_sentence_indexes") or []
            if source_indexes:
                caption_parts.append(f"Source sentences: {source_indexes}")

            with st.expander(str(section_name), expanded=True):
                st.write(summary.get("summary") or "No summary text available.")
                if caption_parts:
                    st.caption(" | ".join(caption_parts))
                summary_limitations = summary.get("limitations") or []
                if summary_limitations:
                    st.caption("Limitations: " + "; ".join(map(str, summary_limitations)))

    if limitations:
        st.caption("Overall limitations: " + "; ".join(map(str, limitations)))


def render_search_results(results: list[dict[str, Any]] | None) -> None:
    st.subheader("Local Search")
    if results is None:
        st.info("Run a local search to see matching source chunks.")
        return
    if not results:
        st.info("No matching chunks found.")
        return

    for result in results:
        section_name = result.get("section_name") or "Unknown section"
        score = result.get("score")
        page_start = result.get("page_start")
        page_end = result.get("page_end")
        label = f"{section_name}"
        if score is not None:
            label = f"{label} | Score: {score}"
        with st.expander(label, expanded=False):
            st.write(result.get("text_preview") or "No preview available.")
            if page_start is not None or page_end is not None:
                st.caption(f"Pages: {page_start or '?'}-{page_end or '?'}")


def render_chat_answer(answer: dict[str, Any] | None) -> None:
    st.subheader("Local Source-Grounded Q&A")
    if answer is None:
        st.info("Ask a question to generate a local answer from retrieved chunks.")
        return

    if answer.get("answer_found"):
        st.success(answer.get("answer") or "Answer returned.")
    else:
        st.warning(answer.get("answer") or "No answer found in retrieved chunks.")

    source_chunks = answer.get("source_chunks") or []
    if source_chunks:
        st.write("Source snippets")
        for source in source_chunks:
            if not isinstance(source, dict):
                continue
            section_name = source.get("section_name") or "Unknown section"
            st.caption(f"{section_name} | Score: {source.get('score')}")
            st.write(source.get("snippet") or "No snippet available.")

    limitations = answer.get("limitations") or []
    if limitations:
        st.caption("Limitations: " + "; ".join(map(str, limitations)))


def render_backend_overview_panel() -> None:
    st.subheader("Backend Document Overview")
    st.write(BACKEND_CONNECTION_PLACEHOLDER)

    backend_url = st.text_input("Backend URL", value=DEFAULT_BACKEND_URL)
    document_id = st.number_input("Document ID", min_value=1, value=1, step=1)
    intelligence_columns = st.columns(3)
    search_query = intelligence_columns[0].text_input("Search query", value="methodology")
    search_top_k = intelligence_columns[1].number_input(
        "Search top K",
        min_value=1,
        max_value=10,
        value=3,
        step=1,
    )
    chat_top_k = intelligence_columns[2].number_input(
        "Q&A top K",
        min_value=1,
        max_value=10,
        value=3,
        step=1,
    )
    question = st.text_input("Question", value="What does the document say about methodology?")

    if st.button("Load Overview"):
        overview, overview_error = fetch_document_overview(backend_url, int(document_id))
        if overview_error:
            st.error(overview_error)
            return
        if overview is not None:
            render_document_overview(overview)

        section_summaries, summaries_error = fetch_document_section_summaries(
            backend_url,
            int(document_id),
        )
        if summaries_error:
            st.warning(summaries_error)
        else:
            render_section_summaries(section_summaries)

    action_columns = st.columns(2)
    if action_columns[0].button("Search Document"):
        search_results, search_error = fetch_document_search(
            backend_url,
            int(document_id),
            search_query,
            int(search_top_k),
        )
        if search_error:
            st.error(search_error)
        else:
            render_search_results(search_results)

    if action_columns[1].button("Ask Question"):
        chat_answer, chat_error = ask_document_question(
            backend_url,
            int(document_id),
            question,
            int(chat_top_k),
        )
        if chat_error:
            st.error(chat_error)
        else:
            render_chat_answer(chat_answer)


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

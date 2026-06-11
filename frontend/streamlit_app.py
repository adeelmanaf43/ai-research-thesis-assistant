import streamlit as st

APP_TITLE = "AI Research / Thesis Assistant"
PRODUCT_DESCRIPTION = (
    "A local-first research workspace for students, thesis writers, academic "
    "freelancers, and analysts."
)
MVP_STATUS = (
    "MVP status: Week 1 foundation is in progress. Document upload, PDF extraction, "
    "search, Q&A, and export are intentionally not built yet."
)
BACKEND_CONNECTION_PLACEHOLDER = (
    "Backend connection: placeholder only. Start the FastAPI backend separately and "
    "wire a health check in a later milestone."
)
LOCAL_FIRST_NOTE = (
    "This project does not require paid API keys, cloud providers, or mandatory Ollama "
    "for the MVP foundation."
)


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

    st.subheader("Backend Connection")
    st.warning(BACKEND_CONNECTION_PLACEHOLDER)

    st.subheader("Local-First Promise")
    st.write(LOCAL_FIRST_NOTE)


if __name__ == "__main__":
    render_app()

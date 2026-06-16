from dataclasses import asdict, dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.chunk import Chunk

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
except ImportError:  # pragma: no cover - covered by deployment/runtime environment
    TfidfVectorizer = None  # type: ignore[assignment]


class RetrievalDependencyError(RuntimeError):
    """Raised when local retrieval dependencies are not installed."""


@dataclass(frozen=True)
class RetrievalResult:
    chunk_id: int
    document_id: int
    chunk_index: int
    section_name: str | None
    page_start: int | None
    page_end: int | None
    score: float
    text: str

    def to_dict(self) -> dict[str, int | str | float | None]:
        return asdict(self)

    def to_response_dict(
        self,
        *,
        include_full_text: bool = False,
        preview_char_limit: int = 300,
    ) -> dict[str, int | str | float | None]:
        if preview_char_limit < 1:
            raise ValueError("Preview character limit must be a positive integer.")

        cleaned_text = " ".join(self.text.split())
        text_preview = cleaned_text
        if len(text_preview) > preview_char_limit:
            text_preview = f"{text_preview[: preview_char_limit - 3].rstrip()}..."

        payload: dict[str, int | str | float | None] = {
            "chunk_id": self.chunk_id,
            "chunk_index": self.chunk_index,
            "section_name": self.section_name,
            "page_start": self.page_start,
            "page_end": self.page_end,
            "score": self.score,
            "text_preview": text_preview,
            "full_text": self.text if include_full_text else None,
        }
        return payload


def _validate_retrieval_inputs(
    query: str | None,
    top_k: int,
    document_id: int | None,
) -> str:
    cleaned_query = (query or "").strip()
    if not cleaned_query:
        raise ValueError("Search query must not be empty.")
    if top_k < 1:
        raise ValueError("top_k must be a positive integer.")
    if document_id is not None and document_id <= 0:
        raise ValueError("Document ID must be a positive integer.")
    return cleaned_query


def _load_searchable_chunks(db: Session, document_id: int | None) -> list[Chunk]:
    statement = select(Chunk)
    if document_id is not None:
        statement = statement.where(Chunk.document_id == document_id)
    statement = statement.order_by(Chunk.document_id.asc(), Chunk.chunk_index.asc(), Chunk.id.asc())

    return [chunk for chunk in db.scalars(statement).all() if chunk.text and chunk.text.strip()]


def search_chunks(
    db: Session,
    query: str | None,
    *,
    top_k: int = 5,
    document_id: int | None = None,
) -> list[RetrievalResult]:
    cleaned_query = _validate_retrieval_inputs(query, top_k, document_id)
    chunks = _load_searchable_chunks(db, document_id)
    if not chunks:
        return []
    if TfidfVectorizer is None:
        raise RetrievalDependencyError(
            "scikit-learn is required for local TF-IDF retrieval. "
            "Install project requirements first."
        )

    chunk_texts = [chunk.text for chunk in chunks]
    vectorizer = TfidfVectorizer(stop_words="english")
    try:
        chunk_matrix = vectorizer.fit_transform(chunk_texts)
        query_vector = vectorizer.transform([cleaned_query])
    except ValueError:
        return []

    scores = (chunk_matrix @ query_vector.T).toarray().ravel()
    ranked_results = sorted(
        (
            (float(score), chunk)
            for score, chunk in zip(scores, chunks, strict=True)
            if float(score) > 0
        ),
        key=lambda item: (-item[0], item[1].document_id, item[1].chunk_index, item[1].id),
    )

    return [
        RetrievalResult(
            chunk_id=chunk.id,
            document_id=chunk.document_id,
            chunk_index=chunk.chunk_index,
            section_name=chunk.section_name,
            page_start=chunk.page_start,
            page_end=chunk.page_end,
            score=round(score, 6),
            text=chunk.text,
        )
        for score, chunk in ranked_results[:top_k]
    ]

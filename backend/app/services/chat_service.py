from dataclasses import dataclass

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.models.chat_history import ChatHistory
from backend.app.models.document import Document
from backend.app.services.llm.local_provider import LocalAnswer, SourceSnippet, answer_question
from backend.app.services.retrieval import search_chunks


class ChatPersistenceError(RuntimeError):
    """Raised when a local chat answer cannot be stored."""


@dataclass(frozen=True)
class DocumentChatAnswer:
    chat_id: int
    document_id: int
    question: str
    answer: str
    answer_found: bool
    provider_mode: str
    source_chunks: list[SourceSnippet]
    limitations: list[str]

    def to_dict(self) -> dict:
        return {
            "chat_id": self.chat_id,
            "document_id": self.document_id,
            "question": self.question,
            "answer": self.answer,
            "answer_found": self.answer_found,
            "provider_mode": self.provider_mode,
            "source_chunks": [source.to_dict() for source in self.source_chunks],
            "limitations": self.limitations,
        }


def answer_document_question(
    db: Session,
    document_id: int,
    question: str | None,
    *,
    top_k: int = 5,
) -> DocumentChatAnswer | None:
    if document_id <= 0:
        raise ValueError("Document ID must be a positive integer.")

    cleaned_question = (question or "").strip()
    if not cleaned_question:
        raise ValueError("Question must not be empty.")
    if top_k < 1:
        raise ValueError("top_k must be a positive integer.")

    document = db.get(Document, document_id)
    if document is None:
        return None

    retrieved_chunks = search_chunks(
        db,
        cleaned_question,
        top_k=top_k,
        document_id=document_id,
    )
    local_answer: LocalAnswer = answer_question(
        cleaned_question,
        retrieved_chunks,
        max_source_snippets=top_k,
    )

    chat = ChatHistory(
        project_id=document.project_id,
        document_id=document.id,
        question=cleaned_question,
        answer=local_answer.answer,
        provider_mode="local",
    )

    try:
        db.add(chat)
        db.commit()
        db.refresh(chat)
    except SQLAlchemyError as exc:
        db.rollback()
        raise ChatPersistenceError("Could not save local chat history.") from exc

    return DocumentChatAnswer(
        chat_id=chat.id,
        document_id=document.id,
        question=cleaned_question,
        answer=local_answer.answer,
        answer_found=local_answer.answer_found,
        provider_mode=chat.provider_mode,
        source_chunks=local_answer.source_snippets,
        limitations=local_answer.limitations,
    )

"""LLM provider boundary for optional future local and cloud integrations."""

from backend.app.services.llm.local_provider import (
    LocalAnswer,
    SourceSnippet,
    answer_question,
)

__all__ = [
    "LocalAnswer",
    "SourceSnippet",
    "answer_question",
]

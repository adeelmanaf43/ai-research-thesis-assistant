import math
from dataclasses import asdict, dataclass

from sqlalchemy import delete, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.models.chunk import Chunk
from backend.app.services.section_detection import DetectedSection

MIN_CHUNK_SIZE_WORDS = 500
MAX_CHUNK_SIZE_WORDS = 800
DEFAULT_CHUNK_SIZE_WORDS = 700

MIN_OVERLAP_WORDS = 100
MAX_OVERLAP_WORDS = 150
DEFAULT_OVERLAP_WORDS = 125
DEFAULT_SECTION_NAME = "Unknown"
MAX_SINGLE_CHUNK_WORDS = (MIN_CHUNK_SIZE_WORDS * 2) - MAX_OVERLAP_WORDS - 1
MAX_TWO_CHUNK_WORDS = (MAX_CHUNK_SIZE_WORDS * 2) - MIN_OVERLAP_WORDS


class ChunkPersistenceError(RuntimeError):
    """Raised when document chunks cannot be replaced safely."""


@dataclass(frozen=True)
class TextChunk:
    chunk_index: int
    section_name: str
    page_start: int | None
    page_end: int | None
    text: str
    word_count: int

    def to_dict(self) -> dict[str, str | int | None]:
        return asdict(self)


def _validate_chunking_settings(chunk_size_words: int, overlap_words: int) -> None:
    if not MIN_CHUNK_SIZE_WORDS <= chunk_size_words <= MAX_CHUNK_SIZE_WORDS:
        raise ValueError("Chunk size must be between 500 and 800 words.")
    if not MIN_OVERLAP_WORDS <= overlap_words <= MAX_OVERLAP_WORDS:
        raise ValueError("Chunk overlap must be between 100 and 150 words.")
    if overlap_words >= chunk_size_words:
        raise ValueError("Chunk overlap must be smaller than chunk size.")


def _split_words(text: str | None) -> list[str]:
    if not text:
        return []
    return text.split()


def _estimate_page_range(
    start_word_index: int,
    end_word_index: int,
    total_words: int,
    page_count: int | None,
) -> tuple[int | None, int | None]:
    if page_count is None or page_count <= 0 or total_words <= 0:
        return None, None

    page_start = math.floor((start_word_index / total_words) * page_count) + 1
    page_end = math.ceil((end_word_index / total_words) * page_count)
    page_start = min(max(page_start, 1), page_count)
    page_end = min(max(page_end, page_start), page_count)
    return page_start, page_end


def _final_pair_ranges(
    start_word_index: int,
    total_words: int,
    chunk_size_words: int,
    overlap_words: int,
) -> tuple[tuple[int, int], tuple[int, int]]:
    remaining_words = total_words - start_word_index
    candidates: list[tuple[int, int, int, int]] = []
    for first_size in range(MIN_CHUNK_SIZE_WORDS, MAX_CHUNK_SIZE_WORDS + 1):
        for overlap in range(MIN_OVERLAP_WORDS, MAX_OVERLAP_WORDS + 1):
            second_size = remaining_words - first_size + overlap
            if MIN_CHUNK_SIZE_WORDS <= second_size <= MAX_CHUNK_SIZE_WORDS:
                score = (
                    abs(first_size - chunk_size_words)
                    + abs(second_size - chunk_size_words)
                    + abs(overlap - overlap_words)
                )
                candidates.append((score, first_size, second_size, overlap))

    if not candidates:
        end_word_index = min(start_word_index + chunk_size_words, total_words)
        return (start_word_index, end_word_index), (end_word_index, total_words)

    _, first_size, _, overlap = min(candidates)
    first_end = start_word_index + first_size
    second_start = first_end - overlap
    return (start_word_index, first_end), (second_start, total_words)


def split_text_into_chunks(
    text: str | None,
    *,
    section_name: str = DEFAULT_SECTION_NAME,
    page_count: int | None = None,
    chunk_size_words: int = DEFAULT_CHUNK_SIZE_WORDS,
    overlap_words: int = DEFAULT_OVERLAP_WORDS,
    starting_chunk_index: int = 0,
) -> list[TextChunk]:
    _validate_chunking_settings(chunk_size_words, overlap_words)

    words = _split_words(text)
    if not words:
        return []

    cleaned_section_name = section_name.strip() or DEFAULT_SECTION_NAME
    if len(words) <= MAX_SINGLE_CHUNK_WORDS:
        page_start, page_end = _estimate_page_range(0, len(words), len(words), page_count)
        return [
            TextChunk(
                chunk_index=starting_chunk_index,
                section_name=cleaned_section_name,
                page_start=page_start,
                page_end=page_end,
                text=" ".join(words),
                word_count=len(words),
            )
        ]

    chunks: list[TextChunk] = []
    start_word_index = 0
    chunk_index = starting_chunk_index

    while start_word_index < len(words):
        end_word_index = min(start_word_index + chunk_size_words, len(words))
        next_start_word_index = end_word_index - overlap_words
        if (
            len(words) - start_word_index <= MAX_TWO_CHUNK_WORDS
            and len(words) - next_start_word_index <= MAX_SINGLE_CHUNK_WORDS
        ):
            ranges = _final_pair_ranges(
                start_word_index,
                len(words),
                chunk_size_words,
                overlap_words,
            )
            for range_start, range_end in ranges:
                page_start, page_end = _estimate_page_range(
                    range_start,
                    range_end,
                    len(words),
                    page_count,
                )
                chunk_words = words[range_start:range_end]
                chunks.append(
                    TextChunk(
                        chunk_index=chunk_index,
                        section_name=cleaned_section_name,
                        page_start=page_start,
                        page_end=page_end,
                        text=" ".join(chunk_words),
                        word_count=len(chunk_words),
                    )
                )
                chunk_index += 1
            break

        page_start, page_end = _estimate_page_range(
            start_word_index,
            end_word_index,
            len(words),
            page_count,
        )
        chunk_words = words[start_word_index:end_word_index]
        chunks.append(
            TextChunk(
                chunk_index=chunk_index,
                section_name=cleaned_section_name,
                page_start=page_start,
                page_end=page_end,
                text=" ".join(chunk_words),
                word_count=len(chunk_words),
            )
        )

        if end_word_index == len(words):
            break

        start_word_index = next_start_word_index
        chunk_index += 1

    return chunks


def split_sections_into_chunks(
    sections: list[DetectedSection],
    *,
    page_count: int | None = None,
    chunk_size_words: int = DEFAULT_CHUNK_SIZE_WORDS,
    overlap_words: int = DEFAULT_OVERLAP_WORDS,
) -> list[TextChunk]:
    chunks: list[TextChunk] = []
    for section in sections:
        section_chunks = split_text_into_chunks(
            section.text,
            section_name=section.section_name,
            page_count=page_count,
            chunk_size_words=chunk_size_words,
            overlap_words=overlap_words,
            starting_chunk_index=len(chunks),
        )
        chunks.extend(section_chunks)
    return chunks


def replace_document_chunks(
    db: Session,
    document_id: int,
    chunks: list[TextChunk],
) -> list[Chunk]:
    if document_id <= 0:
        raise ValueError("Document ID must be a positive integer.")

    chunk_records = [
        Chunk(
            document_id=document_id,
            chunk_index=chunk.chunk_index,
            section_name=chunk.section_name,
            text=chunk.text,
            word_count=chunk.word_count,
            page_start=chunk.page_start,
            page_end=chunk.page_end,
        )
        for chunk in chunks
    ]

    try:
        db.execute(delete(Chunk).where(Chunk.document_id == document_id))
        db.add_all(chunk_records)
        db.commit()
        statement = (
            select(Chunk)
            .where(Chunk.document_id == document_id)
            .order_by(Chunk.chunk_index.asc(), Chunk.id.asc())
        )
        return list(db.scalars(statement).all())
    except SQLAlchemyError as exc:
        db.rollback()
        raise ChunkPersistenceError("Could not replace document chunks.") from exc

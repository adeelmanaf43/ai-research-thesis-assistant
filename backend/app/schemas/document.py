from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DocumentCreate(BaseModel):
    project_id: int
    original_filename: str = Field(min_length=1, max_length=255)
    mime_type: str | None = Field(default=None, max_length=120)
    file_size_bytes: int | None = Field(default=None, ge=0)


class DocumentMetadataUpdate(BaseModel):
    page_count: int | None = Field(default=None, ge=0)
    word_count: int | None = Field(default=None, ge=0)
    status: str | None = Field(default=None, min_length=1, max_length=50)
    extraction_error: str | None = None


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    original_filename: str
    mime_type: str | None = None
    file_size_bytes: int | None = None
    page_count: int | None = None
    word_count: int | None = None
    status: str
    extraction_error: str | None = None
    uploaded_at: datetime


class SectionOverviewResponse(BaseModel):
    section_name: str
    detected_heading: str
    confidence: float = Field(ge=0.0, le=1.0)


class ProcessingSummaryResponse(BaseModel):
    status: str
    message: str
    is_complete: bool
    requires_attention: bool
    next_step: str | None = None


class DocumentOverviewResponse(BaseModel):
    document_id: int
    filename: str
    status: str
    page_count: int | None = None
    word_count: int | None = None
    chunk_count: int
    detected_sections: list[SectionOverviewResponse]
    extraction_warnings: list[str]
    processing_summary: ProcessingSummaryResponse


class DocumentLocalAnalysisResponse(BaseModel):
    id: int
    document_id: int
    analysis_type: str
    title: str | None = None
    provider_mode: str
    output_json: dict[str, Any]
    created_at: datetime


class SectionSummaryResponse(BaseModel):
    section_name: str
    section_type: str
    summary: str
    selected_sentence_count: int
    source_sentence_indexes: list[int]
    confidence: float = Field(ge=0.0, le=1.0)
    limitations: list[str]


class DocumentSectionSummariesResponse(BaseModel):
    document_id: int
    summaries: list[SectionSummaryResponse]
    source_section_names: list[str]
    limitations: list[str]

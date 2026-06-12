from datetime import datetime

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

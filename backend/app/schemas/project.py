from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _clean_project_name(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("Project name cannot be empty.")
    return cleaned


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return _clean_project_name(value)


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return _clean_project_name(value)


class ProjectListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int | None = None
    name: str
    description: str | None = None
    created_at: datetime
    updated_at: datetime


class ProjectDetailResponse(ProjectListItem):
    pass


ProjectResponse = ProjectDetailResponse

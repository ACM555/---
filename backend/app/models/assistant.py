from __future__ import annotations

from uuid import uuid4

from pydantic import BaseModel, Field


class AssistantPassage(BaseModel):
    locator: str
    original_text: str
    chinese_text: str | None = None
    effective_at: str | None = None


class AssistantSource(BaseModel):
    id: str
    title: str
    excerpt: str
    source_url: str | None = None
    country_code: str | None = None
    legal_module: str | None = None
    evidence_level: str | None = None
    source_type: str | None = None
    source_language: str | None = None
    verified_at: str | None = None
    effective_at: str | None = None
    prerequisites: list[str] = Field(default_factory=list)
    non_inferences: list[str] = Field(default_factory=list)
    review_triggers: list[str] = Field(default_factory=list)
    passages: list[AssistantPassage] = Field(default_factory=list)


class AssistantChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    page: str = Field(default="", max_length=120)
    session_id: str = Field(default_factory=lambda: uuid4().hex, min_length=8, max_length=80)
    image_data_url: str | None = Field(default=None, max_length=14_000_000)


class AssistantChatResponse(BaseModel):
    answer: str
    answer_status: str
    sources: list[AssistantSource]
    scope_and_preconditions: list[str]
    facts_to_confirm: list[str]
    suggested_actions: list[str]
    human_review_reasons: list[str]
    disclaimer: str


class AssistantUploadResponse(BaseModel):
    document_id: str
    filename: str
    indexed: bool
    message: str

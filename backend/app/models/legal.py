from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


EvidenceLevel = Literal["A", "B"]
ApprovalStatus = Literal["draft", "approved", "retired"]
ProvenanceRole = Literal["primary", "cross_check"]


class LegalSourceProvenance(BaseModel):
    provenance_id: str
    role: ProvenanceRole
    publisher: str = Field(min_length=2, max_length=200)
    source_type: str = Field(min_length=2, max_length=80)
    source_url: HttpUrl
    source_language: str = Field(min_length=2, max_length=80)
    checked_at: date
    version_note: str = Field(default="", max_length=1000)
    conflict_note: str = Field(default="", max_length=1000)


class LegalSourceProvenanceCreate(BaseModel):
    role: ProvenanceRole
    publisher: str = Field(min_length=2, max_length=200)
    source_type: str = Field(min_length=2, max_length=80)
    source_url: HttpUrl
    source_language: str = Field(min_length=2, max_length=80)
    checked_at: date
    version_note: str = Field(default="", max_length=1000)
    conflict_note: str = Field(default="", max_length=1000)


class LegalSourceCreate(BaseModel):
    country_code: str = Field(min_length=2, max_length=8, pattern=r"^[A-Z-]+$")
    legal_module: str = Field(min_length=2, max_length=12, pattern=r"^M[1-6]$")
    evidence_level: EvidenceLevel
    title: str = Field(min_length=2, max_length=300)
    source_type: str = Field(min_length=2, max_length=80)
    source_url: HttpUrl
    source_language: str = Field(min_length=2, max_length=80)
    effective_at: date | None = None
    verified_at: date
    supported_fact: str = Field(min_length=8, max_length=2000)
    prerequisites: list[str] = Field(min_length=1, max_length=20)
    non_inferences: list[str] = Field(min_length=1, max_length=20)
    review_triggers: list[str] = Field(min_length=1, max_length=20)
    approval_status: ApprovalStatus = "draft"


class LegalSourceRecord(LegalSourceCreate):
    source_id: str
    provenance: list[LegalSourceProvenance] = Field(default_factory=list)
    reviewable_passage_count: int = Field(default=0, ge=0)
    created_at: str
    updated_at: str


class LegalSourceSearch(BaseModel):
    country_code: str | None = Field(default=None, min_length=2, max_length=8)
    legal_module: str | None = Field(default=None, pattern=r"^M[1-6]$")
    evidence_level: EvidenceLevel | None = None
    as_of: date | None = None
    limit: int = Field(default=20, ge=1, le=100)


class LegalSourceReviewRequest(BaseModel):
    approval_status: Literal["approved", "retired"]


class LegalPassageCreate(BaseModel):
    source_id: str = Field(min_length=8, max_length=80)
    locator: str = Field(min_length=1, max_length=120)
    original_text: str = Field(min_length=1, max_length=12000)
    chinese_text: str | None = Field(default=None, max_length=12000)
    effective_at: date | None = None
    prerequisites: list[str] = Field(min_length=1, max_length=20)
    non_inferences: list[str] = Field(min_length=1, max_length=20)
    approval_status: ApprovalStatus = "draft"


class LegalPassageRecord(LegalPassageCreate):
    passage_id: str
    created_at: str
    updated_at: str

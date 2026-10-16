from __future__ import annotations
from app.services.official_monitoring import official_legal_pointers

from datetime import date
import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.auth import admin_user, current_user
from app.models.legal import (
    ApprovalStatus,
    EvidenceLevel,
    LegalPassageCreate,
    LegalPassageRecord,
    LegalSourceRecord,
    LegalSourceProvenanceCreate,
    LegalSourceReviewRequest,
    LegalSourceSearch,
)
from app.services.legal_repository import LegalRepository


router = APIRouter(prefix="/legal", tags=["法律资料"])
repository = LegalRepository()


@router.get("/scenario-checklists")
def scenario_checklists(country_code: str | None = None, legal_module: str | None = None, _: dict = Depends(current_user)) -> list[dict]:
    package_path = Path(__file__).resolve().parents[2] / "data" / "sg_m5_filing_checklist.json"
    package = json.loads(package_path.read_text(encoding="utf-8"))
    return [package] if (not country_code or package["countryCode"] == country_code) and (not legal_module or package["legalModule"] == legal_module) else []


@router.get("/official-pointers")
def list_official_pointers(country_code: str | None = None, legal_module: str | None = None, _: dict = Depends(current_user)) -> list[dict]:
    return [item for item in official_legal_pointers() if (not country_code or item["countryCode"] == country_code) and (not legal_module or item["legalModule"] == legal_module)]


@router.get("/sources", response_model=list[LegalSourceRecord])
async def list_approved_sources(
    country_code: str | None = Query(default=None, min_length=2, max_length=8),
    legal_module: str | None = Query(default=None, pattern=r"^M[1-6]$"),
    evidence_level: EvidenceLevel | None = Query(default=None),
    as_of: date | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    _: dict[str, str] = Depends(current_user),
) -> list[LegalSourceRecord]:
    """Return only project-lead-approved legal sources for citation and retrieval."""
    return repository.search_sources(
        LegalSourceSearch(
            country_code=country_code.upper() if country_code else None,
            legal_module=legal_module,
            evidence_level=evidence_level,
            as_of=as_of,
            limit=limit,
        )
    )


@router.get("/admin/sources", response_model=list[LegalSourceRecord])
async def list_sources_for_review(
    approval_status: ApprovalStatus = Query(default="draft"),
    limit: int = Query(default=100, ge=1, le=200),
    _: dict[str, str] = Depends(admin_user),
) -> list[LegalSourceRecord]:
    return repository.list_sources_for_review(approval_status, limit)


@router.post("/admin/sources/{source_id}/approval", response_model=LegalSourceRecord)
async def review_source(
    source_id: str,
    payload: LegalSourceReviewRequest,
    _: dict[str, str] = Depends(admin_user),
) -> LegalSourceRecord:
    try:
        source = repository.set_approval_status(source_id, payload.approval_status)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    if source is None:
        raise HTTPException(status_code=404, detail="未找到法律资料")
    return source


@router.post("/admin/sources/{source_id}/provenance", response_model=LegalSourceRecord)
async def add_source_provenance(
    source_id: str,
    payload: LegalSourceProvenanceCreate,
    _: dict[str, str] = Depends(admin_user),
) -> LegalSourceRecord:
    try:
        source = repository.add_provenance(source_id, payload)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    if source is None:
        raise HTTPException(status_code=404, detail="未找到法律资料")
    return source


@router.get("/admin/sources/{source_id}/passages", response_model=list[LegalPassageRecord])
async def list_source_passages(
    source_id: str,
    approval_status: ApprovalStatus | None = Query(default=None),
    _: dict[str, str] = Depends(admin_user),
) -> list[LegalPassageRecord]:
    return repository.list_passages(source_id, approval_status)


@router.post("/admin/sources/{source_id}/passages", response_model=LegalPassageRecord)
async def add_source_passage(
    source_id: str,
    payload: LegalPassageCreate,
    _: dict[str, str] = Depends(admin_user),
) -> LegalPassageRecord:
    if payload.source_id != source_id:
        raise HTTPException(status_code=422, detail="条款摘录的 source_id 必须与路径一致")
    passage = repository.create_passage(payload)
    if passage is None:
        raise HTTPException(status_code=404, detail="未找到法律资料")
    return passage


@router.post("/admin/passages/{passage_id}/approval", response_model=LegalPassageRecord)
async def review_passage(
    passage_id: str,
    payload: LegalSourceReviewRequest,
    _: dict[str, str] = Depends(admin_user),
) -> LegalPassageRecord:
    passage = repository.set_passage_approval_status(passage_id, payload.approval_status)
    if passage is None:
        raise HTTPException(status_code=404, detail="未找到法律条款摘录")
    return passage

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.auth import admin_user, current_user
from app.database import get_admin_statistics, get_system_status, get_task, list_audit_tasks, list_users
from app.services.official_monitoring import official_alerts, official_source_status, sync_official_sources
from app.services.public_data import PublicDataError, search_public_trademarks, watched_trademarks, watch_trademark, unwatch_trademark
from app.services.public_data_ai import explain_public_record
from app.services.platform_service import (
    build_report_center,
    get_brand_assets,
    get_country_rules,
    get_platform_overview,
)


router = APIRouter(tags=["平台"])


def _success(data: object | None = None, message: str = "success") -> dict:
    return {"code": 0, "message": message, "data": data}


@router.get("/platform/overview")
def platform_overview(_: dict = Depends(current_user)) -> dict:
    return _success(get_platform_overview())


@router.get("/rules/countries")
def country_rules(_: dict = Depends(current_user)) -> dict:
    return _success(get_country_rules())


@router.get("/brands")
def brand_assets(user: dict = Depends(current_user)) -> dict:
    return _success(
        get_brand_assets(
            list_audit_tasks(limit=200, user_id=user["userId"]),
            user.get("company") or user["username"],
        )
    )


@router.get("/monitoring/alerts")
def monitoring_alerts(user: dict = Depends(current_user)) -> dict:
    return _success(official_alerts(user["userId"]))


@router.post("/monitoring/sync")
async def monitoring_sync(_: dict = Depends(admin_user)) -> dict:
    return _success(await sync_official_sources())


@router.get("/data-sources/status")
def data_source_status(_: dict = Depends(current_user)) -> dict:
    return _success(official_source_status())


@router.get("/trademarks/search")
async def public_trademark_search(q: str = Query(min_length=2, max_length=100), offset: int = Query(default=0, ge=0, le=100), _: dict = Depends(current_user)) -> dict:
    try:
        return _success(await search_public_trademarks(q, offset))
    except PublicDataError as failure:
        raise HTTPException(status_code=503, detail=str(failure)) from failure


@router.post("/trademarks/{application_number}/explain")
async def public_trademark_explain(application_number: str, _: dict = Depends(current_user)) -> dict:
    result = await explain_public_record(application_number)
    if result is None:
        raise HTTPException(status_code=404, detail="请先检索并取得官方记录，再进行 AI 翻译。")
    return _success(result)


@router.get("/trademarks/watches")
def public_trademark_watches(user: dict = Depends(current_user)) -> dict:
    return _success(watched_trademarks(user["userId"]))


@router.post("/trademarks/{application_number}/watch")
def public_trademark_watch(application_number: str, user: dict = Depends(current_user)) -> dict:
    try:
        return _success(watch_trademark(user["userId"], application_number))
    except PublicDataError as failure:
        raise HTTPException(status_code=409, detail=str(failure)) from failure


@router.delete("/trademarks/{application_number}/watch")
def public_trademark_unwatch(application_number: str, user: dict = Depends(current_user)) -> dict:
    return _success(unwatch_trademark(user["userId"], application_number))


@router.get("/reports")
def report_center(_: dict = Depends(current_user)) -> dict:
    return _success(build_report_center(list_audit_tasks(user_id=_.get("userId"))))


@router.get("/admin/statistics")
def admin_statistics(_: dict = Depends(admin_user)) -> dict:
    return _success(get_admin_statistics())


@router.get("/admin/tasks")
def admin_tasks(_: dict = Depends(admin_user)) -> dict:
    return _success(list_audit_tasks())


@router.get("/admin/users")
def admin_users(_: dict = Depends(admin_user)) -> dict:
    return _success(list_users())


@router.get("/admin/system-status")
def admin_system_status(_: dict = Depends(admin_user)) -> dict:
    return _success(get_system_status())


@router.get("/admin/tasks/{task_id}")
def admin_task_detail(task_id: str, _: dict = Depends(admin_user)) -> dict:
    task = get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="审查任务不存在")
    return _success(task)

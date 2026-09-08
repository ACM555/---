from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.auth import admin_user, current_user
from app.database import get_admin_statistics, get_system_status, get_task, list_audit_tasks, list_users
from app.services.platform_service import (
    build_report_center,
    get_brand_assets,
    get_country_rules,
    get_data_source_status,
    get_monitoring_alerts,
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
def brand_assets(_: dict = Depends(current_user)) -> dict:
    return _success(get_brand_assets())


@router.get("/monitoring/alerts")
def monitoring_alerts(_: dict = Depends(current_user)) -> dict:
    return _success(get_monitoring_alerts())


@router.get("/data-sources/status")
def data_source_status(_: dict = Depends(current_user)) -> dict:
    return _success(get_data_source_status())


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

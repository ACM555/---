from datetime import datetime, timezone
from uuid import uuid4

import base64
import binascii

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response

from app.api.auth import current_user
from app.core.config import settings
from app.database import create_task, get_task, list_audit_tasks, record_report_view, update_task
from app.models.audit import AuditRequest, AuditResponse, AuditResult, UnifiedResponse
from app.services.audit_engine import run_audit
from app.services.audit_result import build_complete_audit_result
from app.services.pdf_service import build_audit_pdf

router = APIRouter(prefix="/audit", tags=["商标审查"])


@router.get("/tasks")
def audit_tasks(user: dict = Depends(current_user)) -> dict:
    return {"code": 0, "message": "success", "data": list_audit_tasks(limit=200, user_id=user["userId"])}

@router.post(
    "",
    response_model=UnifiedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="提交商标审查",
    description="""
接收品牌信息与 Logo 图片，创建审查任务。
返回 taskId，前端通过 GET /api/audit/result/{taskId} 轮询获取结果。

**处理流程：**
1. 法条规则匹配（越南《工业产权法》第72-76条）
2. 多模态视觉比对（OpenCV + 视觉大模型）
3. 风险综合评估

**预计耗时：** 3-5 秒（模拟阶段）
""",
    responses={
        200: {
            "description": "提交成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "审查已提交",
                        "data": {
                            "taskId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                            "status": "pending",
                            "message": "审查已提交，正在处理中",
                        },
                    },
                },
            },
        },
        422: {"description": "请求体校验失败"},
    },
)
async def submit_audit(req: AuditRequest, user: dict = Depends(current_user)) -> UnifiedResponse:
    """提交商标审查任务，并返回用于轮询的 taskId。"""

    logo_payload = req.logo.split(",", 1)[1] if "," in req.logo and "base64" in req.logo[:50] else req.logo
    try:
        logo_bytes = base64.b64decode(logo_payload, validate=True)
    except (binascii.Error, ValueError) as error:
        raise HTTPException(status_code=422, detail="Logo 不是有效的 Base64 图片") from error
    if len(logo_bytes) > settings.MAX_IMAGE_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"Logo 图片不能超过 {settings.MAX_IMAGE_SIZE_MB} MB")
    if not (logo_bytes.startswith(b"\x89PNG\r\n\x1a\n") or logo_bytes.startswith(b"\xff\xd8\xff")):
        raise HTTPException(status_code=422, detail="Logo 仅支持 PNG 或 JPEG 图片")

    task_id = str(uuid4())
    create_task(task_id, user["userId"], req.model_dump())

    response = AuditResponse(taskId=task_id, status="pending", message="审查已提交，正在处理中")
    return UnifiedResponse(code=0, message="审查已提交", data=response.model_dump())


@router.get(
    "/result/{taskId}",
    response_model=UnifiedResponse,
    summary="获取审查结果",
    description="""
轮询审查结果。前端每 2 秒调用一次。

**状态流转：**
- pending → processing（step 0-2）→ done / error
- done 时返回完整审查结果（hitRules / references / suggestions / radarData 等）
- error 时返回 errorMessage

**轮询策略：**
- 间隔：2 秒
- 超时：60 秒未完成视为超时
- done 后停止轮询
""",
    responses={
        200: {
            "description": "审查结果",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "success",
                        "data": {
                            "taskId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                            "status": "done",
                            "currentStep": 2,
                            "progress": 100,
                            "brandName": "墨兰奶白",
                            "niceClass": "第43类-餐饮服务",
                            "goodsServices": "新茶饮品牌，主营奶茶饮品，目标市场越南",
                            "riskLevel": "high",
                            "riskScore": 82,
                            "overallResult": "存在跨类目驰名商誉攀附风险，建议暂缓提交。",
                            "hitRules": [
                                {
                                    "ruleType": "relative",
                                    "article": "越南《工业产权法》第74.2(c)条",
                                    "content": "与在越南已注册的驰名商标构成混淆性近似",
                                    "applicable": True,
                                    "similarityType": "图形相似-四叶花卉几何结构",
                                    "similarityScore": 87,
                                    "note": "四叶花卉图形与Louis Vuitton几何特征高度近似",
                                },
                            ],
                            "references": [
                                {
                                    "refType": "trademark",
                                    "title": "Louis Vuitton",
                                    "source": "WIPO Madrid Monitor",
                                    "date": "2019-03-15",
                                    "registrationNo": "4VN-2019-00XXX",
                                    "summary": "全类注册（含第43类餐饮服务）",
                                    "relevance": "图形几何构图高度近似",
                                },
                            ],
                            "suggestions": [
                                {
                                    "priority": "P0",
                                    "title": "立即停止使用四叶花卉图形",
                                    "description": "暂停当前图形在越南市场使用和申请。",
                                },
                            ],
                            "manualReviewRequired": True,
                        },
                    },
                },
            },
        },
        404: {
            "description": "任务不存在",
            "content": {
                "application/json": {
                    "example": {"code": 404, "message": "任务不存在", "data": None},
                },
            },
        },
    },
)
async def get_audit_result(taskId: str, user: dict = Depends(current_user)) -> UnifiedResponse:
    """根据 taskId 轮询审查状态；完成后返回持久化的本地规则引擎报告。"""

    task = get_task(taskId)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if task["userId"] != user["userId"] and user.get("role") != "superadmin":
        raise HTTPException(status_code=404, detail="任务不存在")

    if task["status"] == "done" and task["result"] and task["result"].get("reportSchemaVersion") != 2:
        raw_result = run_audit(task["request"]) if task["request"].get("logo") else task["result"]
        migrated_result = build_complete_audit_result(taskId, task["request"], raw_result)
        migrated_result["summary"]["submitTime"] = task["createdAt"]
        update_task(
            taskId,
            status="done",
            current_step=2,
            progress=100,
            result=migrated_result,
            error_message="",
            touch_updated=False,
        )
        task = get_task(taskId)
        if task is None:
            raise HTTPException(status_code=404, detail="任务不存在")

    created_at = datetime.fromisoformat(task["createdAt"])
    elapsed = (datetime.now(timezone.utc) - created_at.astimezone(timezone.utc)).total_seconds()

    if task["status"] in {"done", "error"}:
        pass
    elif elapsed < 1:
        update_task(taskId, status="pending", current_step=0, progress=10)
    elif elapsed < 2:
        update_task(taskId, status="processing", current_step=0, progress=33)
    elif elapsed < 3:
        update_task(taskId, status="processing", current_step=1, progress=66)
    elif elapsed < 4:
        update_task(taskId, status="processing", current_step=2, progress=90)
    else:
        if task["result"] is None:
            try:
                raw_result = run_audit(task["request"])
                result = build_complete_audit_result(taskId, task["request"], raw_result)
                result["summary"]["submitTime"] = task["createdAt"]
                update_task(taskId, status="done", current_step=2, progress=100, result=result, error_message="")
            except Exception as error:
                update_task(taskId, status="error", current_step=2, progress=100, error_message=str(error)[:500])
        elif task["status"] not in {"done", "error"}:
            update_task(taskId, status="done", current_step=2, progress=100)

    task = get_task(taskId)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")

    result = {
        "taskId": taskId,
        "status": task["status"],
        "currentStep": task["currentStep"],
        "progress": task["progress"],
    }
    if task["status"] == "done" and task["result"]:
        result.update(task["result"])
        record_report_view(taskId)
        result["createdAt"] = task["createdAt"]
        result["completedAt"] = task["completedAt"]

    AuditResult.model_validate(result)
    return UnifiedResponse(code=0, message="success", data=result)


@router.get(
    "/report/{taskId}/pdf",
    summary="下载审查报告 PDF",
    description="仅任务创建者或超级管理员可以下载已完成任务的 PDF 报告。",
)
async def download_audit_report(taskId: str, user: dict = Depends(current_user)) -> Response:
    task = get_task(taskId)
    if task is None or (
        task["userId"] != user["userId"] and user.get("role") != "superadmin"
    ):
        raise HTTPException(status_code=404, detail="任务不存在")
    if task["status"] != "done" or not task["result"]:
        raise HTTPException(status_code=409, detail="报告尚未生成完成")

    if task["result"].get("reportSchemaVersion") != 2:
        raw_result = run_audit(task["request"]) if task["request"].get("logo") else task["result"]
        migrated_result = build_complete_audit_result(taskId, task["request"], raw_result)
        migrated_result["summary"]["submitTime"] = task["createdAt"]
        update_task(
            taskId,
            status="done",
            current_step=2,
            progress=100,
            result=migrated_result,
            error_message="",
            touch_updated=False,
        )
        task = get_task(taskId)
        if task is None or not task["result"]:
            raise HTTPException(status_code=404, detail="任务不存在")

    pdf_bytes = build_audit_pdf(task["result"])
    if not pdf_bytes or not pdf_bytes.startswith(b"%PDF-"):
        raise HTTPException(status_code=503, detail="报告文件生成失败，请稍后重试")
    filename = f"outbound-guard-{taskId}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "private, no-store",
        },
    )

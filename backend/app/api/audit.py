from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.api.auth import current_user
from app.database import create_task, get_task, update_task
from app.models.audit import AuditRequest, AuditResponse, AuditResult, UnifiedResponse
from app.services.audit_engine import run_audit

router = APIRouter(prefix="/audit", tags=["商标审查"])

@router.post(
    "",
    response_model=UnifiedResponse,
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
        return UnifiedResponse(code=404, message="任务不存在", data=None)
    if task["userId"] != user["userId"] and user.get("role") != "superadmin":
        raise HTTPException(status_code=404, detail="任务不存在")

    created_at = datetime.fromisoformat(task["createdAt"])
    elapsed = (datetime.now(UTC) - created_at.astimezone(UTC)).total_seconds()

    if elapsed < 1:
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
                result = run_audit(task["request"])
                update_task(taskId, status="done", current_step=2, progress=100, result=result, error_message="")
            except Exception as error:
                update_task(taskId, status="error", current_step=2, progress=100, error_message=str(error)[:500])
        elif task["status"] != "error":
            update_task(taskId, status="done", current_step=2, progress=100)

    task = get_task(taskId)
    if task is None:
        return UnifiedResponse(code=404, message="任务不存在", data=None)

    result = {
        "taskId": taskId,
        "status": task["status"],
        "currentStep": task["currentStep"],
        "progress": task["progress"],
    }
    if task["status"] == "done" and task["result"]:
        result.update(task["result"])

    AuditResult.model_validate(result)
    return UnifiedResponse(code=0, message="success", data=result)

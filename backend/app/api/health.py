from fastapi import APIRouter

from app.core.config import settings
from app.database import get_statistics

router = APIRouter(tags=["系统"])


@router.get(
    "/health",
    summary="健康检查",
    description="检查 API 服务是否正常运行。前端可用于启动时探测后端可用性。",
    responses={
        200: {
            "description": "服务正常",
            "content": {
                "application/json": {
                    "example": {"status": "ok", "version": "1.0.0"},
                },
            },
        },
    },
)
async def health_check() -> dict[str, object]:
    """返回服务健康状态和当前 API 版本。"""

    return {
        "status": "ok",
        "version": settings.APP_VERSION,
        "aiStatus": "configured" if settings.model_api_key else "unconfigured",
        "aiProvider": settings.model_provider,
        "aiModel": settings.model_name if settings.model_api_key else "",
        "aiTasks": {
            "legalAssistant": {"provider": settings.model_provider, "model": settings.model_name if settings.model_api_key else "", "configured": bool(settings.model_api_key)},
            "publicDataTranslation": {"provider": settings.public_data_providers[0] if settings.public_data_providers else "unconfigured", "model": settings.model_config(settings.public_data_providers[0])[2] if settings.public_data_providers else "", "fallback": settings.public_data_providers[1:]},
        },
    }


@router.get(
    "/statistics",
    summary="首页统计",
    description="返回已持久化审查任务中的审查数量与高风险数量，用于首页统计卡片。",
)
async def statistics() -> dict[str, object]:
    """返回首页统计数据。"""

    return {
        "code": 0,
        "message": "success",
        "data": get_statistics(),
    }

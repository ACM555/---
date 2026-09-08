from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from app.api.auth import current_user
from app.core.config import settings
from app.models.assistant import AssistantChatRequest, AssistantChatResponse, AssistantUploadResponse
from app.services.assistant_orchestrator import AssistantOrchestrator
from app.services.bailian_client import BailianConfigurationError, BailianServiceError


router = APIRouter(prefix="/assistant", tags=["AI 助手"])
orchestrator = AssistantOrchestrator()
logger = logging.getLogger(__name__)


@router.post("/chat", response_model=AssistantChatResponse)
async def chat(payload: AssistantChatRequest, user: dict = Depends(current_user)) -> AssistantChatResponse:
    try:
        return await orchestrator.answer(payload, user["userId"])
    except BailianConfigurationError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except BailianServiceError as error:
        logger.exception("AI 助手调用百炼服务失败")
        raise HTTPException(status_code=503, detail=str(error)) from error


@router.post("/chat/stream")
async def chat_stream(payload: AssistantChatRequest, user: dict = Depends(current_user)) -> StreamingResponse:
    async def events() -> AsyncIterator[str]:
        try:
            async for delta in orchestrator.stream(payload, user["userId"]):
                yield f"data: {json.dumps({'delta': delta}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
        except BailianConfigurationError as error:
            yield f"data: {json.dumps({'error': str(error)}, ensure_ascii=False)}\n\n"
        except BailianServiceError as error:
            logger.exception("AI 助手流式调用百炼服务失败")
            yield f"data: {json.dumps({'error': str(error)}, ensure_ascii=False)}\n\n"
        except Exception:
            logger.exception("AI 助手发生未处理异常")
            yield "data: {\"error\": \"AI 服务暂时不可用，请稍后重试。\"}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")


@router.post("/knowledge/upload", response_model=AssistantUploadResponse)
async def upload_knowledge(file: UploadFile = File(...), user: dict = Depends(current_user)) -> AssistantUploadResponse:
    filename = file.filename or "document.txt"
    if not filename.lower().endswith((".txt", ".md")):
        raise HTTPException(status_code=415, detail="当前仅支持 TXT 或 Markdown 知识资料。")
    content = await file.read()
    if len(content) > settings.ASSISTANT_MAX_FILE_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail="资料文件超过大小限制。")
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as error:
        raise HTTPException(status_code=422, detail="资料必须为 UTF-8 编码。") from error
    if not text.strip():
        raise HTTPException(status_code=422, detail="资料内容不能为空。")
    document_id = orchestrator.store_text_document(user["userId"], filename, text)
    return AssistantUploadResponse(document_id=document_id, filename=filename, indexed=True, message="资料已入库，将仅用于当前用户的检索。")

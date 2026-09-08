from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.core.config import settings


class IFLYTEKConfigurationError(RuntimeError):
    pass


class IFLYTEKServiceError(RuntimeError):
    """讯飞星火服务不可用时向上层提供安全、可展示的错误信息。"""


class ModelClient:
    def _headers(self) -> dict[str, str]:
        if not settings.IFLYTEK_API_PASSWORD:
            raise IFLYTEKConfigurationError("科大讯飞星火模型尚未配置，请联系管理员。")
        return {
            "Authorization": f"Bearer {settings.IFLYTEK_API_PASSWORD}",
            "Content-Type": "application/json",
        }

    def _payload(self, messages: list[dict[str, Any]], stream: bool) -> dict[str, Any]:
        normalized: list[dict[str, str]] = []
        for message in messages:
            content = message.get("content")
            if isinstance(content, str):
                normalized.append({"role": str(message.get("role", "user")), "content": content})
                continue
            if isinstance(content, list):
                text_blocks = [item.get("text") for item in content if item.get("type") == "text"]
                if len(text_blocks) != len(content) or not all(isinstance(item, str) for item in text_blocks):
                    raise IFLYTEKServiceError("当前科大讯飞文本模型未启用图像输入，请移除图像后重试。")
                normalized.append(
                    {"role": str(message.get("role", "user")), "content": "\n".join(text_blocks)}
                )
                continue
            raise IFLYTEKServiceError("模型请求包含无法识别的消息内容。")
        return {
            "model": settings.IFLYTEK_MODEL,
            "messages": normalized,
            "stream": stream,
            # Keep a legal-assistant reply bounded so a reasoning model cannot
            # hold the browser request open with an unbounded response.
            "max_tokens": 2048,
            "temperature": 0.2,
            "thinking": {"type": "disabled"},
        }

    async def complete(self, messages: list[dict[str, Any]]) -> str:
        try:
            async with httpx.AsyncClient(timeout=90) as client:
                response = await client.post(
                    f"{settings.iflytek_base_url}/chat/completions",
                    headers=self._headers(),
                    json=self._payload(messages, stream=False),
                )
            response.raise_for_status()
        except httpx.HTTPError as error:
            raise IFLYTEKServiceError("科大讯飞服务连接失败，请稍后重试。") from error
        payload = response.json()
        if payload.get("code", 0) != 0:
            raise IFLYTEKServiceError("科大讯飞服务未返回可用结果，请稍后重试。")
        choices = payload.get("choices", [])
        content = choices[0].get("message", {}).get("content", "") if choices else ""
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("模型没有返回可用回答。")
        return content.strip()

    async def stream(self, messages: list[dict[str, Any]]) -> AsyncIterator[str]:
        try:
            async with httpx.AsyncClient(timeout=90) as client:
                async with client.stream(
                    "POST",
                    f"{settings.iflytek_base_url}/chat/completions",
                    headers={**self._headers(), "Accept": "text/event-stream"},
                    json=self._payload(messages, stream=True),
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line.startswith("data:"):
                            continue
                        data = line.removeprefix("data:").strip()
                        if data == "[DONE]":
                            return
                        try:
                            payload = json.loads(data)
                            delta = payload.get("choices", [{}])[0].get("delta", {}).get("content", "")
                        except (IndexError, TypeError, ValueError):
                            continue
                        if isinstance(delta, str) and delta:
                            yield delta
        except httpx.HTTPError as error:
            raise IFLYTEKServiceError("科大讯飞服务连接失败，请稍后重试。") from error


# Compatibility aliases keep the existing API error boundary stable while the provider is replaced.
BailianConfigurationError = IFLYTEKConfigurationError
BailianServiceError = IFLYTEKServiceError

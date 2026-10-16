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
    def __init__(self, provider: str | None = None) -> None:
        self.provider = provider or settings.model_provider
        self.api_key, self.base_url, self.model_name = settings.model_config(self.provider)

    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            raise IFLYTEKConfigurationError(
                "AI 模型尚未配置，请在 backend/.env 中填写 GLM_API_KEY、"
                "DEEPSEEK_API_KEY、IFLYTEK_API_PASSWORD 或 LLM_API_KEY。"
            )
        return {
            "Authorization": f"Bearer {self.api_key}",
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
                    raise IFLYTEKServiceError("当前 AI 接入仅启用文本，尚未启用图像输入；请改用文字描述或移除图像后重试。")
                normalized.append(
                    {"role": str(message.get("role", "user")), "content": "\n".join(text_blocks)}
                )
                continue
            raise IFLYTEKServiceError("模型请求包含无法识别的消息内容。")
        payload: dict[str, Any] = {
            "model": self.model_name,
            "messages": normalized,
            "stream": stream,
            # Keep a legal-assistant reply bounded so a reasoning model cannot
            # hold the browser request open with an unbounded response.
            "max_tokens": 2048,
            "temperature": 0.2,
        }
        if self.provider == "iflytek":
            payload["thinking"] = {"type": "disabled"}
        return payload

    async def complete(self, messages: list[dict[str, Any]]) -> str:
        try:
            async with httpx.AsyncClient(timeout=90) as client:
                response = await client.post(
                    f"{self.base_url.rstrip('/')}/chat/completions",
                    headers=self._headers(),
                    json=self._payload(messages, stream=False),
                )
            response.raise_for_status()
        except httpx.HTTPError as error:
            raise IFLYTEKServiceError("AI 模型服务连接失败，请稍后重试。") from error
        try:
            payload = response.json()
        except ValueError as error:
            raise IFLYTEKServiceError("AI 模型服务返回了无法解析的结果，请稍后重试。") from error
        if not isinstance(payload, dict):
            raise IFLYTEKServiceError("AI 模型服务未返回可用结果，请稍后重试。")
        if payload.get("code", 0) != 0:
            raise IFLYTEKServiceError("AI 模型服务未返回可用结果，请稍后重试。")
        choices = payload.get("choices", [])
        content = ""
        if isinstance(choices, list) and choices and isinstance(choices[0], dict):
            result_message = choices[0].get("message")
            if isinstance(result_message, dict):
                content = result_message.get("content", "")
        if not isinstance(content, str) or not content.strip():
            raise IFLYTEKServiceError("AI 模型服务未返回可用回答，请稍后重试。")
        return content.strip()

    async def stream(self, messages: list[dict[str, Any]]) -> AsyncIterator[str]:
        try:
            async with httpx.AsyncClient(timeout=90) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url.rstrip('/')}/chat/completions",
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
            raise IFLYTEKServiceError("AI 模型服务连接失败，请稍后重试。") from error


# Compatibility aliases keep the existing API error boundary stable while the provider is replaced.
BailianConfigurationError = IFLYTEKConfigurationError
BailianServiceError = IFLYTEKServiceError

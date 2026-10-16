from __future__ import annotations

import asyncio
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.database import create_task, update_task
from app.main import app
from app.services.bailian_client import IFLYTEKServiceError, ModelClient
from app.services.platform_service import MODULES
from app.services.rag_retrieval_service import RetrievalService


@pytest.fixture
def isolated_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "DATABASE_PATH", str(tmp_path / "features.sqlite3"))
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setattr(settings, "REPORT_DIR", str(tmp_path / "reports"))
    monkeypatch.setattr(settings, "ASSISTANT_KNOWLEDGE_DIR", str(tmp_path / "knowledge"))
    with TestClient(app) as client:
        yield client


def guest_session(client: TestClient) -> tuple[dict[str, str], dict]:
    response = client.post("/api/auth/guest")
    assert response.status_code == 200
    session = response.json()["data"]
    return {"Authorization": f"Bearer {session['token']}"}, session["user"]


def test_completed_audits_enter_private_assets_and_reports(isolated_client: TestClient) -> None:
    owner_headers, owner = guest_session(isolated_client)
    other_headers, _ = guest_session(isolated_client)
    task_id = uuid4().hex
    create_task(task_id, owner["userId"], {
        "brandName": "验收独立品牌",
        "englishName": "Private Acceptance",
        "niceClass": "第25类-服装鞋帽",
        "targetCountries": ["越南"],
    })
    update_task(task_id, status="done", progress=100, result={
        "riskLevel": "low", "riskScore": 18, "manualReviewRequired": False,
    })
    owner_assets = isolated_client.get("/api/brands", headers=owner_headers).json()["data"]
    private_asset = next(asset for asset in owner_assets if asset.get("taskId") == task_id)
    assert private_asset["englishName"] == "Private Acceptance"
    assert private_asset["isDemo"] is False
    assert private_asset["portfolioStatus"] == "待核验"
    assert private_asset["targetCountries"] == ["越南"]
    assert any(asset["isDemo"] for asset in owner_assets)
    other_assets = isolated_client.get("/api/brands", headers=other_headers).json()["data"]
    assert not any(asset.get("taskId") == task_id for asset in other_assets)
    assert any(report["taskId"] == task_id for report in isolated_client.get("/api/reports", headers=owner_headers).json()["data"])
    assert isolated_client.get("/api/reports", headers=other_headers).json()["data"] == []
    assert isolated_client.get("/api/audit/result/" + task_id, headers=other_headers).status_code == 404
    assert isolated_client.get("/api/admin/users", headers=owner_headers).status_code == 403


def test_markdown_upload_is_private_and_never_approved_evidence(isolated_client: TestClient) -> None:
    headers, user = guest_session(isolated_client)
    _, other = guest_session(isolated_client)
    response = isolated_client.post("/api/assistant/knowledge/upload", headers=headers, files={
        "file": ("materials.md", "验收唯一关键词：货物交付凭据。", "text/markdown"),
    })
    assert response.status_code == 200
    service = RetrievalService()
    documents = service._tenant_documents(user["userId"])
    assert len(documents) == 1
    assert "验收唯一关键词" in documents[0].content
    assert service._tenant_documents(other["userId"]) == []
    assert service.retrieve_legal("越南 M3 货物交付凭据") == []
    assert isolated_client.post("/api/assistant/knowledge/upload", headers=headers, files={
        "file": ("unsafe.exe", b"binary", "application/octet-stream"),
    }).status_code == 415


def test_six_modules_keep_the_explicit_selected_scope() -> None:
    assert [module["key"] for module in MODULES] == [f"M{number}" for number in range(1, 7)]
    assert MODULES[0]["name"] == "外商投资准入与公司设立"
    assert MODULES[-1]["name"] == "跨境争议解决与货款追偿"
    for number in range(1, 7):
        assert RetrievalService._detect_module(f"M{number} 模块：越南，合同、投资、运输与争议事实") == f"M{number}"
    assert RetrievalService._detect_module("比较 M2 和 M6 的区别") is None


@pytest.mark.parametrize("payload", [[], {}, {"choices": [None]}, {"choices": [{"message": None}]}, {"choices": [{"message": {"content": ""}}]}])
def test_invalid_model_payload_uses_recoverable_service_error(payload, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "GLM_API_KEY", "test-only")
    original_client = httpx.AsyncClient
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: original_client(transport=transport, **kwargs))
    with pytest.raises(IFLYTEKServiceError):
        asyncio.run(ModelClient().complete([{"role": "user", "content": "连通性测试"}]))

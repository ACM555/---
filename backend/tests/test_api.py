from __future__ import annotations

import base64
import tempfile
import time
from io import BytesIO
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

from app.config import settings
from app.database import reset_database
from app.main import app


_original_database_path = settings.DATABASE_PATH
_original_upload_dir = settings.UPLOAD_DIR
_test_directory: tempfile.TemporaryDirectory[str] | None = None


def image_base64(*, fourfold: bool) -> str:
    image = Image.new("RGB", (240, 240), "white")
    draw = ImageDraw.Draw(image)
    if fourfold:
        for box in ((85, 30, 155, 100), (140, 85, 210, 155), (85, 140, 155, 210), (30, 85, 100, 155)):
            draw.ellipse(box, outline="black", width=12)
    else:
        draw.line((35, 195, 205, 45), fill="black", width=12)
        draw.rectangle((45, 150, 105, 205), outline="black", width=8)
    output = BytesIO()
    image.save(output, format="PNG")
    return base64.b64encode(output.getvalue()).decode("ascii")


def submit_payload(*, safe: bool) -> dict:
    return {
        "brandName": "Xinglan Acceptance Studio" if safe else "榕溪验收茶饮",
        "englishName": "Xinglan Acceptance Studio" if safe else "",
        "niceClass": "第25类-服装鞋帽" if safe else "第43类-餐饮服务",
        "goodsServices": "计划在越南销售原创服装与鞋帽产品" if safe else "计划在越南提供茶饮及餐饮门店服务",
        "logo": image_base64(fourfold=not safe),
    }


def setup_module() -> None:
    global _test_directory
    _test_directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
    settings.DATABASE_PATH = str(Path(_test_directory.name) / "test.sqlite3")
    settings.UPLOAD_DIR = str(Path(_test_directory.name) / "uploads")
    reset_database()
    upload_dir = Path(settings.UPLOAD_DIR)
    if upload_dir.exists():
        for path in upload_dir.glob("*"):
            path.unlink()


def wait_for_result(client: TestClient, task_id: str, headers: dict[str, str]) -> dict:
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        response = client.get(f"/api/audit/result/{task_id}", headers=headers)
        assert response.status_code == 200
        data = response.json()["data"]
        if data["status"] in {"done", "error"}:
            return data
        time.sleep(0.25)
    raise AssertionError(f"审查任务 {task_id} 未在测试时限内完成")


def test_health_and_safe_audit() -> None:
    with TestClient(app) as client:
        health = client.get("/api/health")
        assert health.status_code == 200
        assert health.json()["status"] == "ok"
        assert health.json()["aiStatus"] in {"configured", "unconfigured"}

        login = client.post(
            "/api/auth/login",
            json={"username": settings.SUPERADMIN_USERNAME, "password": settings.SUPERADMIN_PASSWORD},
        )
        assert login.status_code == 200
        admin_token = login.json()["data"]["token"]
        me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {admin_token}"})
        assert me.status_code == 200
        assert me.json()["data"]["role"] == "superadmin"

        overview = client.get(
            "/api/platform/overview", headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert overview.status_code == 200
        assert len(overview.json()["data"]["modules"]) == 6

        countries = client.get(
            "/api/rules/countries", headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert countries.status_code == 200
        assert any(item["country"] == "越南" for item in countries.json()["data"])

        brands = client.get("/api/brands", headers={"Authorization": f"Bearer {admin_token}"})
        assert brands.status_code == 200
        assert any(item["name"] == "墨兰奶白" for item in brands.json()["data"])

        alerts = client.get(
            "/api/monitoring/alerts", headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert alerts.status_code == 200
        assert alerts.json()["data"] == []

        data_sources = client.get(
            "/api/data-sources/status", headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert data_sources.status_code == 200
        assert len(data_sources.json()["data"]) >= 4

        created = client.post(
            "/api/audit",
            json=submit_payload(safe=True),
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert created.status_code == 202
        task_id = created.json()["data"]["taskId"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        data = wait_for_result(client, task_id, admin_headers)
        assert data["status"] == "done"
        assert data["riskLevel"] == "low"
        assert data["absolute"]["hasRisk"] is False
        assert data["relative"]["hasRisk"] is False
        assert data["intelligence"]["registrationStrategy"]["route"]

        admin_tasks = client.get(
            "/api/admin/tasks", headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert admin_tasks.status_code == 200
        assert any(item["taskId"] == task_id for item in admin_tasks.json()["data"])

        admin_users = client.get(
            "/api/admin/users", headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert admin_users.status_code == 200
        assert any(item["role"] == "superadmin" for item in admin_users.json()["data"])

        system_status = client.get(
            "/api/admin/system-status", headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert system_status.status_code == 200
        assert system_status.json()["data"]["database"] == "online"

        reports = client.get("/api/reports", headers={"Authorization": f"Bearer {admin_token}"})
        assert reports.status_code == 200
        assert any(item["taskId"] == task_id for item in reports.json()["data"])

        forbidden = client.get("/api/admin/tasks")
        assert forbidden.status_code == 401

        protected_without_token = client.get("/api/brands")
        assert protected_without_token.status_code == 401


def test_high_risk_audit_and_pdf() -> None:
    with TestClient(app) as client:
        guest = client.post("/api/auth/guest")
        assert guest.status_code == 200
        token = guest.json()["data"]["token"]
        headers = {"Authorization": f"Bearer {token}"}
        created = client.post("/api/audit", json=submit_payload(safe=False), headers=headers)
        assert created.status_code == 202
        task_id = created.json()["data"]["taskId"]
        result = wait_for_result(client, task_id, headers)
        assert result["status"] == "done"
        assert result["assessmentStatus"] == "pending_verification"
        assert result["riskScore"] < 70
        assert result["absolute"]["hasRisk"] is True
        assert result["relative"]["hasRisk"] is False
        assert result["intelligence"]["crossClassShield"]["triggered"] is False
        assert result["intelligence"]["refusalHistory"]["triggered"] is True
        assert result["intelligence"]["culturalReview"]["triggered"] is True
        assert result["advice"]["documentDownloadUrl"].endswith(f"/{task_id}/pdf")

        other_guest = client.post("/api/auth/guest")
        assert other_guest.status_code == 200
        other_headers = {"Authorization": f"Bearer {other_guest.json()['data']['token']}"}
        assert client.get(f"/api/audit/result/{task_id}", headers=other_headers).status_code == 404
        assert client.get(f"/api/audit/report/{task_id}/pdf", headers=other_headers).status_code == 404
        other_reports = client.get("/api/reports", headers=other_headers)
        assert other_reports.status_code == 200
        assert all(item.get("taskId") != task_id for item in other_reports.json()["data"])

        pdf = client.get(f"/api/audit/report/{task_id}/pdf", headers=headers)
        assert pdf.status_code == 200
        assert pdf.headers["content-type"].startswith("application/pdf")
        assert pdf.content.startswith(b"%PDF")
        assert len(pdf.content) > 1500


def test_invalid_logo_and_missing_task() -> None:
    with TestClient(app) as client:
        registered = client.post(
            "/api/auth/register",
            json={"username": "demo_user", "password": "demo1234", "company": "Demo Co"},
        )
        assert registered.status_code == 200
        assert registered.json()["data"]["user"]["role"] == "user"

        duplicate = client.post(
            "/api/auth/register",
            json={"username": "demo_user", "password": "demo1234"},
        )
        assert duplicate.status_code == 409

        token = registered.json()["data"]["token"]
        headers = {"Authorization": f"Bearer {token}"}

        payload = submit_payload(safe=True)
        payload["logo"] = "not-valid-base64!!"
        invalid = client.post("/api/audit", json=payload, headers=headers)
        assert invalid.status_code == 422
        assert "Base64" in invalid.json()["detail"]

        missing = client.get("/api/audit/result/not-found", headers=headers)
        assert missing.status_code == 404
        assert missing.json()["detail"] == "任务不存在"


def teardown_module() -> None:
    global _test_directory
    settings.DATABASE_PATH = _original_database_path
    settings.UPLOAD_DIR = _original_upload_dir
    if _test_directory is not None:
        _test_directory.cleanup()
        _test_directory = None

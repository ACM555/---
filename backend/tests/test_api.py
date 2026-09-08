from __future__ import annotations

import base64
import os
from io import BytesIO
from pathlib import Path

TEST_RUNTIME = Path(__file__).resolve().parent / ".runtime"
os.environ["DATABASE_PATH"] = str(TEST_RUNTIME / "test.sqlite3")
os.environ["UPLOAD_DIR"] = str(TEST_RUNTIME / "uploads")

from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

from app.config import settings
from app.database import reset_database
from app.main import app


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
        "brandName": "Mộc Lan" if safe else "墨兰奶白",
        "englishName": "Moc Lan" if safe else "",
        "niceClass": "第25类-服装鞋帽" if safe else "第43类-餐饮服务",
        "goodsServices": "原创服装品牌" if safe else "茶饮及餐饮服务",
        "logo": image_base64(fourfold=not safe),
    }


def setup_module() -> None:
    reset_database()
    if settings.upload_dir.exists():
        for path in settings.upload_dir.glob("*"):
            path.unlink()


def test_health_and_safe_audit() -> None:
    with TestClient(app) as client:
        health = client.get("/api/health")
        assert health.status_code == 200
        assert health.json()["data"]["status"] == "ok"

        login = client.post(
            "/api/auth/login", json={"username": "superadmin", "password": "Flyteam@Admin2026"}
        )
        assert login.status_code == 200
        admin_token = login.json()["data"]["token"]
        me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {admin_token}"})
        assert me.status_code == 200
        assert me.json()["data"]["role"] == "superadmin"

        overview = client.get("/api/platform/overview")
        assert overview.status_code == 200
        assert len(overview.json()["data"]["modules"]) == 6

        countries = client.get("/api/rules/countries")
        assert countries.status_code == 200
        assert any(item["country"] == "越南" for item in countries.json()["data"])

        brands = client.get("/api/brands", headers={"Authorization": f"Bearer {admin_token}"})
        assert brands.status_code == 200
        assert any(item["name"] == "墨兰奶白" for item in brands.json()["data"])

        alerts = client.get(
            "/api/monitoring/alerts", headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert alerts.status_code == 200
        assert any(item["severity"] == "high" for item in alerts.json()["data"])

        data_sources = client.get(
            "/api/data-sources/status", headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert data_sources.status_code == 200
        assert len(data_sources.json()["data"]) >= 4

        created = client.post("/api/audit", json=submit_payload(safe=True))
        assert created.status_code == 202
        task_id = created.json()["data"]["taskId"]
        result = client.get(f"/api/audit/result/{task_id}")
        assert result.status_code == 200
        data = result.json()["data"]
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
        created = client.post("/api/audit", json=submit_payload(safe=False))
        assert created.status_code == 202
        task_id = created.json()["data"]["taskId"]
        result = client.get(f"/api/audit/result/{task_id}").json()["data"]
        assert result["status"] == "done"
        assert result["riskLevel"] == "high"
        assert result["absolute"]["hasRisk"] is True
        assert result["relative"]["hasRisk"] is True
        assert result["intelligence"]["crossClassShield"]["triggered"] is True
        assert result["intelligence"]["refusalHistory"]["triggered"] is True
        assert result["intelligence"]["culturalReview"]["triggered"] is True
        assert result["advice"]["documentDownloadUrl"].endswith(f"/{task_id}/pdf")

        pdf = client.get(f"/api/audit/report/{task_id}/pdf")
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

        payload = submit_payload(safe=True)
        payload["logo"] = "not-valid-base64!!"
        invalid = client.post("/api/audit", json=payload)
        assert invalid.status_code == 422
        assert invalid.json()["code"] == 422

        missing = client.get("/api/audit/result/not-found")
        assert missing.status_code == 404
        assert missing.json()["code"] == 404


def teardown_module() -> None:
    if settings.upload_dir.exists():
        for path in settings.upload_dir.glob("*"):
            path.unlink()

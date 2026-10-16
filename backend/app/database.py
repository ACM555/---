from __future__ import annotations

import hashlib
import json
import secrets
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import settings


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect() -> sqlite3.Connection:
    settings.database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(settings.database_path, timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL")
    return connection


def init_database() -> None:
    with _connect() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_tasks (
                task_id TEXT PRIMARY KEY,
                user_id TEXT,
                status TEXT NOT NULL,
                current_step INTEGER NOT NULL,
                progress INTEGER NOT NULL,
                request_json TEXT NOT NULL,
                result_json TEXT,
                error_message TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_audit_tasks_created_at ON audit_tasks(created_at)"
        )
        task_columns = {row["name"] for row in connection.execute("PRAGMA table_info(audit_tasks)")}
        if "user_id" not in task_columns:
            connection.execute("ALTER TABLE audit_tasks ADD COLUMN user_id TEXT")
        for column in ("completed_at", "archived_at", "last_viewed_at"):
            if column not in task_columns:
                connection.execute(f"ALTER TABLE audit_tasks ADD COLUMN {column} TEXT")
        connection.execute("UPDATE audit_tasks SET completed_at = COALESCE(completed_at, updated_at), archived_at = COALESCE(archived_at, updated_at) WHERE status = 'done'")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL,
                company TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS user_sessions (
                token TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            )
            """
        )
        if not connection.execute(
            "SELECT 1 FROM users WHERE username = ?", (settings.SUPERADMIN_USERNAME,)
        ).fetchone():
            connection.execute(
                """
                INSERT INTO users (
                    user_id, username, password_hash, role, company, created_at
                ) VALUES (?, ?, ?, 'superadmin', 'Outbound-Guard Platform', ?)
                """,
                (
                    secrets.token_hex(16),
                    settings.SUPERADMIN_USERNAME,
                    _hash_password(settings.SUPERADMIN_PASSWORD),
                    _now(),
                ),
            )
        connection.execute(
            """
            UPDATE audit_tasks
            SET user_id = (
                SELECT user_id FROM users WHERE role = 'superadmin' ORDER BY created_at LIMIT 1
            )
            WHERE user_id IS NULL
            """
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_audit_tasks_user_created ON audit_tasks(user_id, created_at DESC)"
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS legal_sources (
                source_id TEXT PRIMARY KEY,
                country_code TEXT NOT NULL,
                legal_module TEXT NOT NULL,
                evidence_level TEXT NOT NULL CHECK (evidence_level IN ('A', 'B')),
                title TEXT NOT NULL,
                source_type TEXT NOT NULL,
                source_url TEXT NOT NULL,
                source_language TEXT NOT NULL,
                effective_at TEXT,
                verified_at TEXT NOT NULL,
                supported_fact TEXT NOT NULL,
                prerequisites_json TEXT NOT NULL,
                non_inferences_json TEXT NOT NULL,
                review_triggers_json TEXT NOT NULL,
                approval_status TEXT NOT NULL CHECK (approval_status IN ('draft', 'approved', 'retired')),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS legal_passages (
                passage_id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL,
                locator TEXT NOT NULL,
                original_text TEXT NOT NULL,
                chinese_text TEXT,
                effective_at TEXT,
                prerequisites_json TEXT NOT NULL,
                non_inferences_json TEXT NOT NULL,
                approval_status TEXT NOT NULL CHECK (approval_status IN ('draft', 'approved', 'retired')),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(source_id) REFERENCES legal_sources(source_id)
            )
            """
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_legal_sources_lookup ON legal_sources(country_code, legal_module, approval_status)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_legal_passages_source ON legal_passages(source_id, approval_status)"
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS legal_source_provenance (
                provenance_id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL,
                role TEXT NOT NULL CHECK (role IN ('primary', 'cross_check')),
                publisher TEXT NOT NULL,
                source_type TEXT NOT NULL,
                source_url TEXT NOT NULL,
                source_language TEXT NOT NULL,
                checked_at TEXT NOT NULL,
                version_note TEXT NOT NULL DEFAULT '',
                conflict_note TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(source_id, role, source_url),
                FOREIGN KEY(source_id) REFERENCES legal_sources(source_id)
            )
            """
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_legal_provenance_source ON legal_source_provenance(source_id, role)"
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS assistant_session_memory (
                session_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                confirmed_facts_json TEXT NOT NULL,
                country_code TEXT,
                legal_module TEXT,
                source_ids_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                PRIMARY KEY(session_id, user_id)
            )
            """
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_assistant_memory_expiry ON assistant_session_memory(expires_at)"
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS legal_answer_audits (
                audit_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                question TEXT NOT NULL,
                country_code TEXT,
                legal_module TEXT,
                source_ids_json TEXT NOT NULL,
                answer_status TEXT NOT NULL,
                human_review_reasons_json TEXT NOT NULL,
                disclaimer_version TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_legal_answer_audits_user_session ON legal_answer_audits(user_id, session_id, created_at DESC)"
        )
        # Preserve existing data while making every legacy source's current URL
        # explicit as its primary provenance record.  It remains subject to the
        # normal review rules before any later approval decision.
        connection.execute(
            """
            INSERT OR IGNORE INTO legal_source_provenance (
                provenance_id, source_id, role, publisher, source_type,
                source_url, source_language, checked_at, version_note,
                conflict_note, created_at, updated_at
            )
            SELECT source_id || '-primary', source_id, 'primary',
                   '历史条目待补发布机构', source_type, source_url,
                   source_language, verified_at, '由原 source_url 回填', '',
                   created_at, updated_at
            FROM legal_sources
            """
        )


def _hash_password(password: str, salt: str | None = None) -> str:
    actual_salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), actual_salt.encode("utf-8"), 120_000
    ).hex()
    return f"{actual_salt}${digest}"


def _verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt, _ = stored_hash.split("$", 1)
    except ValueError:
        return False
    return secrets.compare_digest(_hash_password(password, salt), stored_hash)


def _public_user(row: sqlite3.Row | dict[str, Any]) -> dict[str, str]:
    return {
        "userId": row["user_id"],
        "username": row["username"],
        "role": row["role"],
        "company": row["company"],
        "createdAt": row["created_at"],
    }


def create_user(username: str, password: str, company: str = "", role: str = "user") -> dict[str, str]:
    user_id = secrets.token_hex(16)
    timestamp = _now()
    with _connect() as connection:
        if connection.execute("SELECT 1 FROM users WHERE username = ?", (username,)).fetchone():
            raise ValueError("用户名已存在")
        connection.execute(
            """
            INSERT INTO users (
                user_id, username, password_hash, role, company, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, username, _hash_password(password), role, company or "未填写", timestamp),
        )
        row = connection.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()
    return _public_user(row)


def authenticate_user(username: str, password: str) -> dict[str, Any] | None:
    with _connect() as connection:
        row = connection.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
    if row is None or not _verify_password(password, row["password_hash"]):
        return None
    return dict(row)


def create_session(user_id: str) -> str:
    token = secrets.token_urlsafe(32)
    with _connect() as connection:
        connection.execute(
            "INSERT INTO user_sessions (token, user_id, created_at) VALUES (?, ?, ?)",
            (token, user_id, _now()),
        )
    return token


def create_guest_session() -> tuple[str, dict[str, str]]:
    """Create an isolated, authenticated, non-admin reviewer session."""
    guest_suffix = secrets.token_hex(6)
    guest_username = f"judge_guest_{guest_suffix}"
    timestamp = _now()
    with _connect() as connection:
        guest_user_id = secrets.token_hex(16)
        connection.execute(
            """
            INSERT INTO users (
                user_id, username, password_hash, role, company, created_at
            ) VALUES (?, ?, ?, 'user', '评委游客体验', ?)
            """,
            (
                guest_user_id,
                guest_username,
                _hash_password(secrets.token_urlsafe(32)),
                timestamp,
            ),
        )
        row = connection.execute(
            "SELECT * FROM users WHERE user_id = ?", (guest_user_id,)
        ).fetchone()

        token = secrets.token_urlsafe(32)
        connection.execute(
            "INSERT INTO user_sessions (token, user_id, created_at) VALUES (?, ?, ?)",
            (token, row["user_id"], timestamp),
        )

    return token, _public_user(row)


def get_user_by_token(token: str) -> dict[str, str] | None:
    with _connect() as connection:
        row = connection.execute(
            """
            SELECT users.* FROM user_sessions
            JOIN users ON users.user_id = user_sessions.user_id
            WHERE user_sessions.token = ?
            """,
            (token,),
        ).fetchone()
    return _public_user(row) if row else None


def delete_session(token: str) -> None:
    with _connect() as connection:
        connection.execute("DELETE FROM user_sessions WHERE token = ?", (token,))


def create_task(task_id: str, user_id: str, request_data: dict[str, Any]) -> None:
    timestamp = _now()
    with _connect() as connection:
        connection.execute(
            """
            INSERT INTO audit_tasks (
                task_id, user_id, status, current_step, progress, request_json,
                result_json, error_message, created_at, updated_at
            ) VALUES (?, ?, 'pending', 0, 0, ?, NULL, NULL, ?, ?)
            """,
            (task_id, user_id, json.dumps(request_data, ensure_ascii=False), timestamp, timestamp),
        )


def update_task(
    task_id: str,
    *,
    status: str | None = None,
    current_step: int | None = None,
    progress: int | None = None,
    result: dict[str, Any] | None = None,
    error_message: str | None = None,
    touch_updated: bool = True,
) -> None:
    timestamp = _now()
    fields: list[str] = ["updated_at = ?"] if touch_updated else []
    values: list[Any] = [timestamp] if touch_updated else []
    if status is not None:
        fields.append("status = ?")
        values.append(status)
        if status == "done":
            fields.extend(["completed_at = COALESCE(completed_at, ?)", "archived_at = COALESCE(archived_at, ?)"])
            values.extend([timestamp, timestamp])
    if current_step is not None:
        fields.append("current_step = ?")
        values.append(current_step)
    if progress is not None:
        fields.append("progress = ?")
        values.append(max(0, min(100, progress)))
    if result is not None:
        fields.append("result_json = ?")
        values.append(json.dumps(result, ensure_ascii=False))
    if error_message is not None:
        fields.append("error_message = ?")
        values.append(error_message)
    values.append(task_id)
    if not fields:
        return
    with _connect() as connection:
        connection.execute(
            f"UPDATE audit_tasks SET {', '.join(fields)} WHERE task_id = ?",
            values,
        )


def get_task(task_id: str) -> dict[str, Any] | None:
    with _connect() as connection:
        row = connection.execute(
            "SELECT * FROM audit_tasks WHERE task_id = ?", (task_id,)
        ).fetchone()
    if row is None:
        return None
    task = dict(row)
    task["taskId"] = task.pop("task_id")
    task["userId"] = task.pop("user_id", "")
    task["createdAt"] = task.pop("created_at")
    task["updatedAt"] = task.pop("updated_at")
    task["completedAt"] = task.pop("completed_at", None)
    task["archivedAt"] = task.pop("archived_at", None)
    task["lastViewedAt"] = task.pop("last_viewed_at", None)
    task["currentStep"] = task.pop("current_step")
    task["request"] = json.loads(task.pop("request_json"))
    raw_result = task.pop("result_json")
    task["result"] = json.loads(raw_result) if raw_result else None
    return task


def record_report_view(task_id: str) -> None:
    with _connect() as connection:
        connection.execute("UPDATE audit_tasks SET last_viewed_at = ? WHERE task_id = ? AND status = 'done'", (_now(), task_id))


def get_statistics() -> dict[str, int]:
    with _connect() as connection:
        total = connection.execute(
            "SELECT COUNT(*) FROM audit_tasks WHERE status = 'done'"
        ).fetchone()[0]
        high_risk = connection.execute(
            """
            SELECT COUNT(*) FROM audit_tasks
            WHERE status = 'done' AND json_extract(result_json, '$.riskLevel') = 'high'
            """
        ).fetchone()[0]
    return {"auditedBrands": int(total), "highRiskBlocked": int(high_risk)}


def list_audit_tasks(limit: int = 50, user_id: str | None = None) -> list[dict[str, Any]]:
    where_clause = "WHERE user_id = ?" if user_id else ""
    parameters: list[Any] = [user_id] if user_id else []
    parameters.append(max(1, min(limit, 200)))
    with _connect() as connection:
        rows = connection.execute(
            f"""
            SELECT task_id, user_id, status, current_step, progress, request_json,
                   result_json, error_message, created_at, updated_at, completed_at, archived_at, last_viewed_at
            FROM audit_tasks
            {where_clause}
            ORDER BY created_at DESC
            LIMIT ?
            """,
            parameters,
        ).fetchall()
    tasks: list[dict[str, Any]] = []
    for row in rows:
        request = json.loads(row["request_json"])
        result = json.loads(row["result_json"]) if row["result_json"] else None
        tasks.append(
            {
                "taskId": row["task_id"],
                "userId": row["user_id"] or "",
                "status": row["status"],
                "currentStep": row["current_step"],
                "progress": row["progress"],
                "brandName": request.get("brandName", ""),
                "englishName": request.get("englishName", ""),
                "niceClass": request.get("niceClass", ""),
                "targetCountries": request.get("targetCountries") or request.get("targetMarkets", []),
                "riskLevel": result.get("riskLevel") if result else "",
                "riskScore": result.get("riskScore") if result else 0,
                "manualReviewRequired": bool(result.get("manualReviewRequired")) if result else False,
                "createdAt": row["created_at"],
                "updatedAt": row["updated_at"],
                "completedAt": row["completed_at"],
                "archivedAt": row["archived_at"],
                "lastViewedAt": row["last_viewed_at"],
                "assessmentStatus": result.get("assessmentStatus", "pending_verification") if result else "pending_verification",
                "errorMessage": row["error_message"] or "",
            }
        )
    return tasks


def get_admin_statistics() -> dict[str, Any]:
    base = get_statistics()
    with _connect() as connection:
        total_tasks = connection.execute("SELECT COUNT(*) FROM audit_tasks").fetchone()[0]
        processing = connection.execute(
            "SELECT COUNT(*) FROM audit_tasks WHERE status IN ('pending', 'processing')"
        ).fetchone()[0]
        users = connection.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        medium_risk = connection.execute(
            """
            SELECT COUNT(*) FROM audit_tasks
            WHERE status = 'done' AND json_extract(result_json, '$.riskLevel') = 'medium'
            """
        ).fetchone()[0]
    return {
        **base,
        "totalTasks": int(total_tasks),
        "processingTasks": int(processing),
        "registeredUsers": int(users),
        "mediumRisk": int(medium_risk),
    }


def list_users(limit: int = 100) -> list[dict[str, Any]]:
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT users.user_id, users.username, users.role, users.company, users.created_at,
                   COUNT(user_sessions.token) AS active_sessions
            FROM users
            LEFT JOIN user_sessions ON users.user_id = user_sessions.user_id
            GROUP BY users.user_id
            ORDER BY users.created_at DESC
            LIMIT ?
            """,
            (max(1, min(limit, 200)),),
        ).fetchall()
    return [
        {
            "userId": row["user_id"],
            "username": row["username"],
            "role": row["role"],
            "company": row["company"],
            "createdAt": row["created_at"],
            "activeSessions": int(row["active_sessions"]),
        }
        for row in rows
    ]


def get_system_status() -> dict[str, Any]:
    with _connect() as connection:
        task_counts = connection.execute(
            "SELECT status, COUNT(*) AS total FROM audit_tasks GROUP BY status"
        ).fetchall()
        session_count = connection.execute("SELECT COUNT(*) FROM user_sessions").fetchone()[0]
        legal_source_counts = {
            row["approval_status"]: int(row["total"])
            for row in connection.execute(
                "SELECT approval_status, COUNT(*) AS total FROM legal_sources GROUP BY approval_status"
            ).fetchall()
        }
        approved_passages = connection.execute(
            "SELECT COUNT(*) FROM legal_passages WHERE approval_status = 'approved'"
        ).fetchone()[0]
    approved_sources = legal_source_counts.get("approved", 0)
    return {
        "database": "online",
        "activeSessions": int(session_count),
        "taskStatus": {row["status"]: int(row["total"]) for row in task_counts},
        "ai": {
            "configured": bool(settings.model_api_key),
            "provider": settings.model_provider,
            "model": settings.model_name if settings.model_api_key else "",
        },
        "legalKnowledge": {
            "draftSources": legal_source_counts.get("draft", 0),
            "approvedSources": approved_sources,
            "retiredSources": legal_source_counts.get("retired", 0),
            "approvedPassages": int(approved_passages),
            "ragReady": bool(settings.model_api_key and approved_sources and approved_passages),
        },
        "checkedAt": _now(),
    }


def reset_database(path: Path | None = None) -> None:
    target = path or settings.database_path
    if target.exists():
        target.unlink()
    if path is None:
        init_database()

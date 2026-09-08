from __future__ import annotations

import json
import secrets
from datetime import UTC, datetime, timedelta

from app.database import _connect, _now


class AssistantSessionMemory:
    """Stores only user-confirmed facts, isolated by both user and session."""

    def load(self, user_id: str, session_id: str) -> dict[str, object] | None:
        with _connect() as connection:
            connection.execute("DELETE FROM assistant_session_memory WHERE expires_at <= ?", (_now(),))
            row = connection.execute(
                "SELECT * FROM assistant_session_memory WHERE user_id = ? AND session_id = ?",
                (user_id, session_id),
            ).fetchone()
        if row is None:
            return None
        return {
            "confirmed_facts": json.loads(row["confirmed_facts_json"]),
            "country_code": row["country_code"],
            "legal_module": row["legal_module"],
            "source_ids": json.loads(row["source_ids_json"]),
        }

    def save_confirmed(
        self, user_id: str, session_id: str, confirmed_facts: dict[str, str],
        country_code: str | None, legal_module: str | None, source_ids: list[str],
    ) -> None:
        expires_at = (datetime.now(UTC) + timedelta(hours=8)).isoformat()
        with _connect() as connection:
            connection.execute(
                """
                INSERT INTO assistant_session_memory (
                    session_id, user_id, confirmed_facts_json, country_code, legal_module,
                    source_ids_json, created_at, updated_at, expires_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id, user_id) DO UPDATE SET
                    confirmed_facts_json = excluded.confirmed_facts_json,
                    country_code = excluded.country_code, legal_module = excluded.legal_module,
                    source_ids_json = excluded.source_ids_json, updated_at = excluded.updated_at,
                    expires_at = excluded.expires_at
                """,
                (session_id, user_id, json.dumps(confirmed_facts, ensure_ascii=False), country_code,
                 legal_module, json.dumps(source_ids, ensure_ascii=False), _now(), _now(), expires_at),
            )

    def record_audit(
        self, user_id: str, session_id: str, question: str, country_code: str | None,
        legal_module: str | None, source_ids: list[str], answer_status: str,
        human_review_reasons: list[str],
    ) -> None:
        with _connect() as connection:
            connection.execute(
                """
                INSERT INTO legal_answer_audits (
                    audit_id, session_id, user_id, question, country_code, legal_module,
                    source_ids_json, answer_status, human_review_reasons_json,
                    disclaimer_version, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'v1', ?)
                """,
                (secrets.token_hex(16), session_id, user_id, question, country_code, legal_module,
                 json.dumps(source_ids, ensure_ascii=False), answer_status,
                 json.dumps(human_review_reasons, ensure_ascii=False), _now()),
            )

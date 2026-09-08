from __future__ import annotations

import json
import secrets
from datetime import date
from typing import Any

from app.database import _connect, _now
from app.models.legal import (
    ApprovalStatus,
    LegalPassageCreate,
    LegalPassageRecord,
    LegalSourceCreate,
    LegalSourceProvenance,
    LegalSourceProvenanceCreate,
    LegalSourceRecord,
    LegalSourceSearch,
)


def _passage_record(row: Any) -> LegalPassageRecord:
    return LegalPassageRecord(
        passage_id=row["passage_id"],
        source_id=row["source_id"],
        locator=row["locator"],
        original_text=row["original_text"],
        chinese_text=row["chinese_text"],
        effective_at=row["effective_at"],
        prerequisites=json.loads(row["prerequisites_json"]),
        non_inferences=json.loads(row["non_inferences_json"]),
        approval_status=row["approval_status"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _provenance_records(source_id: str) -> list[LegalSourceProvenance]:
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT * FROM legal_source_provenance
            WHERE source_id = ?
            ORDER BY CASE role WHEN 'primary' THEN 0 ELSE 1 END, checked_at DESC
            """,
            (source_id,),
        ).fetchall()
    return [
        LegalSourceProvenance(
            provenance_id=row["provenance_id"],
            role=row["role"],
            publisher=row["publisher"],
            source_type=row["source_type"],
            source_url=row["source_url"],
            source_language=row["source_language"],
            checked_at=row["checked_at"],
            version_note=row["version_note"],
            conflict_note=row["conflict_note"],
        )
        for row in rows
    ]


def _source_record(row: Any) -> LegalSourceRecord:
    with _connect() as connection:
        reviewable_passage_count = connection.execute(
            """
            SELECT COUNT(1) FROM legal_passages
            WHERE source_id = ? AND approval_status IN ('draft', 'approved')
            """,
            (row["source_id"],),
        ).fetchone()[0]
    return LegalSourceRecord(
        source_id=row["source_id"],
        country_code=row["country_code"],
        legal_module=row["legal_module"],
        evidence_level=row["evidence_level"],
        title=row["title"],
        source_type=row["source_type"],
        source_url=row["source_url"],
        source_language=row["source_language"],
        effective_at=row["effective_at"],
        verified_at=row["verified_at"],
        supported_fact=row["supported_fact"],
        prerequisites=json.loads(row["prerequisites_json"]),
        non_inferences=json.loads(row["non_inferences_json"]),
        review_triggers=json.loads(row["review_triggers_json"]),
        approval_status=row["approval_status"],
        provenance=_provenance_records(row["source_id"]),
        reviewable_passage_count=reviewable_passage_count,
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


class LegalRepository:
    def create_passage(self, passage: LegalPassageCreate) -> LegalPassageRecord | None:
        passage_id = f"psg_{secrets.token_hex(12)}"
        timestamp = _now()
        with _connect() as connection:
            if not connection.execute(
                "SELECT 1 FROM legal_sources WHERE source_id = ?", (passage.source_id,)
            ).fetchone():
                return None
            connection.execute(
                """
                INSERT INTO legal_passages (
                    passage_id, source_id, locator, original_text, chinese_text,
                    effective_at, prerequisites_json, non_inferences_json,
                    approval_status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    passage_id, passage.source_id, passage.locator, passage.original_text,
                    passage.chinese_text,
                    passage.effective_at.isoformat() if passage.effective_at else None,
                    json.dumps(passage.prerequisites, ensure_ascii=False),
                    json.dumps(passage.non_inferences, ensure_ascii=False),
                    passage.approval_status, timestamp, timestamp,
                ),
            )
            row = connection.execute(
                "SELECT * FROM legal_passages WHERE passage_id = ?", (passage_id,)
            ).fetchone()
        return _passage_record(row)

    def list_passages(self, source_id: str, approval_status: ApprovalStatus | None = None) -> list[LegalPassageRecord]:
        with _connect() as connection:
            if approval_status:
                rows = connection.execute(
                    "SELECT * FROM legal_passages WHERE source_id = ? AND approval_status = ? ORDER BY created_at",
                    (source_id, approval_status),
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT * FROM legal_passages WHERE source_id = ? ORDER BY created_at", (source_id,)
                ).fetchall()
        return [_passage_record(row) for row in rows]

    def set_passage_approval_status(self, passage_id: str, approval_status: ApprovalStatus) -> LegalPassageRecord | None:
        with _connect() as connection:
            connection.execute(
                "UPDATE legal_passages SET approval_status = ?, updated_at = ? WHERE passage_id = ?",
                (approval_status, _now(), passage_id),
            )
            row = connection.execute("SELECT * FROM legal_passages WHERE passage_id = ?", (passage_id,)).fetchone()
        return _passage_record(row) if row else None

    def create_source(self, source: LegalSourceCreate) -> LegalSourceRecord:
        source_id = f"src_{secrets.token_hex(12)}"
        timestamp = _now()
        with _connect() as connection:
            connection.execute(
                """
                INSERT INTO legal_sources (
                    source_id, country_code, legal_module, evidence_level, title, source_type,
                    source_url, source_language, effective_at, verified_at, supported_fact,
                    prerequisites_json, non_inferences_json, review_triggers_json, approval_status,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    source_id,
                    source.country_code,
                    source.legal_module,
                    source.evidence_level,
                    source.title,
                    source.source_type,
                    str(source.source_url),
                    source.source_language,
                    source.effective_at.isoformat() if source.effective_at else None,
                    source.verified_at.isoformat(),
                    source.supported_fact,
                    json.dumps(source.prerequisites, ensure_ascii=False),
                    json.dumps(source.non_inferences, ensure_ascii=False),
                    json.dumps(source.review_triggers, ensure_ascii=False),
                    source.approval_status,
                    timestamp,
                    timestamp,
                ),
            )
            row = connection.execute(
                "SELECT * FROM legal_sources WHERE source_id = ?", (source_id,)
            ).fetchone()
            connection.execute(
                """
                INSERT INTO legal_source_provenance (
                    provenance_id, source_id, role, publisher, source_type,
                    source_url, source_language, checked_at, version_note,
                    conflict_note, created_at, updated_at
                ) VALUES (?, ?, 'primary', ?, ?, ?, ?, ?, '', '', ?, ?)
                """,
                (
                    f"{source_id}-primary",
                    source_id,
                    "待审核主来源发布机构",
                    source.source_type,
                    str(source.source_url),
                    source.source_language,
                    source.verified_at.isoformat(),
                    timestamp,
                    timestamp,
                ),
            )
        if row is None:
            raise RuntimeError("法律资料保存后无法读取")
        return _source_record(row)

    def add_provenance(
        self, source_id: str, provenance: LegalSourceProvenanceCreate
    ) -> LegalSourceRecord | None:
        timestamp = _now()
        with _connect() as connection:
            source = connection.execute(
                "SELECT 1 FROM legal_sources WHERE source_id = ?", (source_id,)
            ).fetchone()
            if source is None:
                return None
            if provenance.role == "primary":
                primary_count = connection.execute(
                    "SELECT COUNT(1) FROM legal_source_provenance WHERE source_id = ? AND role = 'primary'",
                    (source_id,),
                ).fetchone()[0]
                if primary_count:
                    raise ValueError("每条资料只能有一个主法源；请新增交叉来源或先人工修订主法源")
            connection.execute(
                """
                INSERT INTO legal_source_provenance (
                    provenance_id, source_id, role, publisher, source_type,
                    source_url, source_language, checked_at, version_note,
                    conflict_note, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"prov_{secrets.token_hex(12)}",
                    source_id,
                    provenance.role,
                    provenance.publisher,
                    provenance.source_type,
                    str(provenance.source_url),
                    provenance.source_language,
                    provenance.checked_at.isoformat(),
                    provenance.version_note,
                    provenance.conflict_note,
                    timestamp,
                    timestamp,
                ),
            )
            row = connection.execute("SELECT * FROM legal_sources WHERE source_id = ?", (source_id,)).fetchone()
        return _source_record(row) if row else None

    def search_sources(self, query: LegalSourceSearch) -> list[LegalSourceRecord]:
        clauses = ["approval_status = 'approved'"]
        values: list[object] = []
        if query.country_code:
            clauses.append("country_code = ?")
            values.append(query.country_code.upper())
        if query.legal_module:
            clauses.append("legal_module = ?")
            values.append(query.legal_module)
        if query.evidence_level:
            clauses.append("evidence_level = ?")
            values.append(query.evidence_level)
        if query.as_of:
            clauses.append("(effective_at IS NULL OR effective_at <= ?)")
            values.append(query.as_of.isoformat())
        values.append(query.limit)
        with _connect() as connection:
            rows = connection.execute(
                f"""
                SELECT * FROM legal_sources
                WHERE {' AND '.join(clauses)}
                ORDER BY verified_at DESC, updated_at DESC
                LIMIT ?
                """,
                values,
            ).fetchall()
        return [_source_record(row) for row in rows]

    def retire_sources_before(self, cutoff: date) -> int:
        timestamp = _now()
        with _connect() as connection:
            cursor = connection.execute(
                """
                UPDATE legal_sources
                SET approval_status = 'retired', updated_at = ?
                WHERE approval_status = 'approved' AND effective_at IS NOT NULL AND effective_at < ?
                """,
                (timestamp, cutoff.isoformat()),
            )
        return cursor.rowcount

    def list_sources_for_review(
        self, approval_status: ApprovalStatus = "draft", limit: int = 100
    ) -> list[LegalSourceRecord]:
        with _connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM legal_sources
                WHERE approval_status = ?
                ORDER BY verified_at DESC, created_at ASC
                LIMIT ?
                """,
                (approval_status, max(1, min(limit, 200))),
            ).fetchall()
        return [_source_record(row) for row in rows]

    def set_approval_status(
        self, source_id: str, approval_status: ApprovalStatus
    ) -> LegalSourceRecord | None:
        timestamp = _now()
        with _connect() as connection:
            if approval_status == "approved":
                primary_count = connection.execute(
                    """
                    SELECT COUNT(1) FROM legal_source_provenance
                    WHERE source_id = ? AND role = 'primary'
                    """,
                    (source_id,),
                ).fetchone()[0]
                cross_check_count = connection.execute(
                    """
                    SELECT COUNT(1) FROM legal_source_provenance
                    WHERE source_id = ? AND role = 'cross_check'
                    """,
                    (source_id,),
                ).fetchone()[0]
                reviewable_passage_count = connection.execute(
                    """
                    SELECT COUNT(1) FROM legal_passages
                    WHERE source_id = ? AND approval_status IN ('draft', 'approved')
                    """,
                    (source_id,),
                ).fetchone()[0]
                unresolved_conflict = connection.execute(
                    """
                    SELECT COUNT(1) FROM legal_source_provenance
                    WHERE source_id = ? AND TRIM(conflict_note) <> ''
                    """,
                    (source_id,),
                ).fetchone()[0]
                if primary_count != 1 or cross_check_count < 1 or unresolved_conflict:
                    raise ValueError("资料缺少唯一主法源、交叉核验来源或存在未解决的来源冲突，不能审核通过")
                if reviewable_passage_count < 1:
                    raise ValueError("资料尚无可供确认的原文条款/章节摘录，不能审核通过")
                # The source-level approval is the project lead's single review action.
                # Promote the already-collected draft excerpts in the same transaction so
                # the UI does not require a second, duplicative confirmation click.
                connection.execute(
                    """
                    UPDATE legal_passages
                    SET approval_status = 'approved', updated_at = ?
                    WHERE source_id = ? AND approval_status = 'draft'
                    """,
                    (timestamp, source_id),
                )
            connection.execute(
                """
                UPDATE legal_sources
                SET approval_status = ?, updated_at = ?
                WHERE source_id = ?
                """,
                (approval_status, timestamp, source_id),
            )
            row = connection.execute(
                "SELECT * FROM legal_sources WHERE source_id = ?", (source_id,)
            ).fetchone()
        return _source_record(row) if row else None

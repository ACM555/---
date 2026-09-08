from __future__ import annotations

import json
from pathlib import Path

from app.database import _connect, _now
from app.models.legal import LegalSourceCreate


_DATA_DIRECTORY = Path(__file__).resolve().parents[2] / "data"
_SEED_PATHS = (
    _DATA_DIRECTORY / "legal_sources_seed.json",
    _DATA_DIRECTORY / "legal_sources_candidate_seed.json",
)
_PASSAGE_SEED_PATHS = tuple(sorted(_DATA_DIRECTORY.glob("legal_passages*_seed.json")))


def seed_legal_sources() -> int:
    """Load reviewed-source candidates as drafts; never auto-approve legal content."""
    inserted = 0
    with _connect() as connection:
        for seed_path in _SEED_PATHS:
            if not seed_path.exists():
                continue
            records = json.loads(seed_path.read_text(encoding="utf-8"))
            for raw_record in records:
                record = dict(raw_record)
                source_id = str(record.pop("source_id"))
                primary_publisher = str(record.pop("primary_publisher", "待审核主来源发布机构"))
                cross_checks = list(record.pop("cross_checks", []))
                source = LegalSourceCreate.model_validate({**record, "approval_status": "draft"})
                timestamp = _now()
                cursor = connection.execute(
                    """
                INSERT OR IGNORE INTO legal_sources (
                    source_id, country_code, legal_module, evidence_level, title, source_type,
                    source_url, source_language, effective_at, verified_at, supported_fact,
                    prerequisites_json, non_inferences_json, review_triggers_json, approval_status,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'draft', ?, ?)
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
                        timestamp,
                        timestamp,
                    ),
                )
                refresh_provenance = bool(cursor.rowcount)
                if not refresh_provenance:
                    existing = connection.execute(
                        "SELECT approval_status FROM legal_sources WHERE source_id = ?", (source_id,)
                    ).fetchone()
                    if existing and existing["approval_status"] == "draft":
                        connection.execute(
                            """
                            UPDATE legal_sources SET
                                country_code = ?, legal_module = ?, evidence_level = ?, title = ?,
                                source_type = ?, source_url = ?, source_language = ?, effective_at = ?,
                                verified_at = ?, supported_fact = ?, prerequisites_json = ?,
                                non_inferences_json = ?, review_triggers_json = ?, updated_at = ?
                            WHERE source_id = ?
                            """,
                            (
                                source.country_code, source.legal_module, source.evidence_level,
                                source.title, source.source_type, str(source.source_url),
                                source.source_language,
                                source.effective_at.isoformat() if source.effective_at else None,
                                source.verified_at.isoformat(), source.supported_fact,
                                json.dumps(source.prerequisites, ensure_ascii=False),
                                json.dumps(source.non_inferences, ensure_ascii=False),
                                json.dumps(source.review_triggers, ensure_ascii=False), timestamp, source_id,
                            ),
                        )
                        connection.execute(
                            "DELETE FROM legal_source_provenance WHERE source_id = ?", (source_id,)
                        )
                        refresh_provenance = True
                if refresh_provenance:
                    connection.execute(
                        """
                    INSERT INTO legal_source_provenance (
                        provenance_id, source_id, role, publisher, source_type,
                        source_url, source_language, checked_at, version_note,
                        conflict_note, created_at, updated_at
                    ) VALUES (?, ?, 'primary', ?, ?, ?, ?, ?, ?, '', ?, ?)
                        """,
                        (
                        f"{source_id}-primary",
                        source_id,
                        primary_publisher,
                        source.source_type,
                        str(source.source_url),
                        source.source_language,
                        source.verified_at.isoformat(),
                        "待审：须核原文、版本和适用前提",
                        timestamp,
                        timestamp,
                        ),
                    )
                    for index, raw_cross_check in enumerate(cross_checks, start=1):
                        cross_check = dict(raw_cross_check)
                        connection.execute(
                            """
                        INSERT INTO legal_source_provenance (
                            provenance_id, source_id, role, publisher, source_type,
                            source_url, source_language, checked_at, version_note,
                            conflict_note, created_at, updated_at
                        ) VALUES (?, ?, 'cross_check', ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                            f"{source_id}-cross-{index}",
                            source_id,
                            str(cross_check["publisher"]),
                            str(cross_check["source_type"]),
                            str(cross_check["source_url"]),
                            str(cross_check["source_language"]),
                            str(cross_check["checked_at"]),
                            str(cross_check.get("version_note", "待审：用于交叉核验")),
                            str(cross_check.get("conflict_note", "")),
                            timestamp,
                            timestamp,
                            ),
                        )
                    if cursor.rowcount:
                        inserted += 1
        for passage_seed_path in _PASSAGE_SEED_PATHS:
            passages = json.loads(passage_seed_path.read_text(encoding="utf-8"))
            for raw_passage in passages:
                passage = dict(raw_passage)
                source_id = str(passage.pop("source_id"))
                passage_key = str(passage.pop("passage_key"))
                connection.execute(
                    """
                    INSERT OR IGNORE INTO legal_passages (
                        passage_id, source_id, locator, original_text, chinese_text,
                        effective_at, prerequisites_json, non_inferences_json,
                        approval_status, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'draft', ?, ?)
                    """,
                    (
                        f"seed-{passage_key}",
                        source_id,
                        str(passage["locator"]),
                        str(passage["original_text"]),
                        passage.get("chinese_text"),
                        passage.get("effective_at"),
                        json.dumps(passage["prerequisites"], ensure_ascii=False),
                        json.dumps(passage["non_inferences"], ensure_ascii=False),
                        _now(),
                        _now(),
                    ),
                )
    return inserted

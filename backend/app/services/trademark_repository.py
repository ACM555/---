"""Local trademark database access and fuzzy matching."""

from __future__ import annotations

import json
import re
import unicodedata
from difflib import SequenceMatcher
from functools import lru_cache
from pathlib import Path
from typing import Any


BACKEND_ROOT = Path(__file__).resolve().parents[2]
TRADEMARK_DB_PATH = BACKEND_ROOT / "data" / "trademark_db.json"


def normalize_mark(text: str) -> str:
    """Normalize brand text for lightweight exact/fuzzy matching."""

    normalized = unicodedata.normalize("NFKD", text or "")
    normalized = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "", normalized.lower())


def parse_class_no(nice_class: str) -> str:
    """Extract Nice class number from strings like '第43类-餐饮服务'."""

    match = re.search(r"(\d{1,2})", nice_class or "")
    return match.group(1) if match else ""


@lru_cache(maxsize=1)
def load_trademarks() -> list[dict[str, Any]]:
    """Load trademark records from local JSON."""

    with TRADEMARK_DB_PATH.open("r", encoding="utf-8") as file:
        records = json.load(file)
    return records if isinstance(records, list) else []


def class_overlaps(record: dict[str, Any], nice_class: str) -> bool:
    """Return whether a trademark record covers the submitted Nice class."""

    class_no = parse_class_no(nice_class)
    classes = record.get("nice_classes") or []
    return bool(class_no and str(class_no) in {str(item) for item in classes})


def find_trademark_candidates(
    brand_name: str,
    english_name: str,
    nice_class: str,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Find exact and similar local trademark candidates."""

    query_variants = [normalize_mark(brand_name), normalize_mark(english_name)]
    query_variants = [item for item in query_variants if item]
    if not query_variants:
        return []

    candidates: list[dict[str, Any]] = []
    for record in load_trademarks():
        mark = normalize_mark(str(record.get("mark_name", "")))
        normalized_field = normalize_mark(str(record.get("mark_name_normalized", "")))
        record_mark = normalized_field or mark
        if not record_mark:
            continue

        best_score = max(SequenceMatcher(None, query, record_mark).ratio() for query in query_variants)
        exact = any(query == record_mark for query in query_variants)
        overlap = class_overlaps(record, nice_class)

        if exact or best_score >= 0.72:
            item = dict(record)
            item["_matchScore"] = 100 if exact else round(best_score * 100)
            item["_exactMatch"] = exact
            item["_classOverlap"] = overlap
            candidates.append(item)

    candidates.sort(
        key=lambda item: (
            int(item.get("_exactMatch", False)),
            int(item.get("_classOverlap", False)),
            int(item.get("_matchScore", 0)),
        ),
        reverse=True,
    )
    return candidates[:limit]


def build_trademark_reference(record: dict[str, Any], relevance: str) -> dict[str, Any]:
    """Build frontend-compatible trademark reference."""

    classes = "、".join(str(item) for item in (record.get("nice_classes") or []))
    summary_parts = [
        f"权利人：{record.get('owner_name') or '待核验'}",
        f"类别：{classes or '待核验'}",
        f"商品/服务：{record.get('goods_services') or '待核验'}",
        f"状态：{record.get('current_status') or '待核验'}",
    ]

    return {
        "refType": "trademark",
        "title": str(record.get("mark_name") or "未命名商标记录"),
        "source": str(record.get("source_type") or "本地商标底账"),
        "date": str(record.get("application_date") or record.get("last_verified_at") or ""),
        "registrationNo": str(record.get("application_or_registration_no") or ""),
        "summary": "；".join(summary_parts),
        "relevance": relevance,
    }

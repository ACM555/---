"""Local rule repository for Vietnam trademark audit.

The rules are authored by legal teammates and stored in ``rules/rules_v1.json``.
This module intentionally keeps loading and mapping logic small and explicit so
the legal data remains the source of truth.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


BACKEND_ROOT = Path(__file__).resolve().parents[2]
RULES_PATH = BACKEND_ROOT / "rules" / "rules_v1.json"


ARTICLE_BY_RULE_PREFIX = {
    "VN-ABS": "越南《工业产权法》第74.2(a)条",
    "VN-REL": "越南《工业产权法》第74.2(e)条",
    "VN-FAM": "越南《工业产权法》第74.2(i)条",
    "VN-INFO": "越南商标审查信息完整性要求",
}

SCORE_BY_RISK_LEVEL = {
    "low": 25,
    "medium": 55,
    "review": 60,
    "high": 80,
    "critical": 95,
}


@lru_cache(maxsize=1)
def load_ruleset() -> dict[str, Any]:
    """Load rule set from disk."""

    with RULES_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


@lru_cache(maxsize=1)
def load_rules_by_id() -> dict[str, dict[str, Any]]:
    """Return rules indexed by rule_id."""

    rules = load_ruleset().get("rules", [])
    return {rule["rule_id"]: rule for rule in rules}


def get_rule(rule_id: str) -> dict[str, Any]:
    """Get a single rule by id, raising KeyError if missing."""

    return load_rules_by_id()[rule_id]


def article_for_rule(rule_id: str) -> str:
    """Map rule id to the article label displayed in the frontend."""

    for prefix, article in ARTICLE_BY_RULE_PREFIX.items():
        if rule_id.startswith(prefix):
            return article
    return "越南商标审查规则"


def rule_type_for_category(category: str) -> str:
    """Map legal rule category to frontend ruleType."""

    if category == "absolute_refusal" or category == "insufficient_information":
        return "absolute"
    return "relative"


def score_for_rule(rule: dict[str, Any]) -> int:
    """Translate legal risk level to numeric score."""

    return SCORE_BY_RISK_LEVEL.get(str(rule.get("risk_level", "low")), 35)


def build_hit_rule(
    rule: dict[str, Any],
    *,
    applicable: bool,
    note: str,
    similarity_type: str = "",
    similarity_score: int = 0,
) -> dict[str, Any]:
    """Build frontend-compatible hitRules item."""

    return {
        "ruleId": str(rule.get("rule_id", "")),
        "ruleName": str(rule.get("rule_name", "")),
        "ruleType": rule_type_for_category(str(rule.get("category", ""))),
        "article": article_for_rule(str(rule.get("rule_id", ""))),
        "content": str(rule.get("system_message", "")),
        "applicable": applicable,
        "similarityType": similarity_type,
        "similarityScore": max(0, min(100, int(similarity_score))),
        "note": note,
    }


def build_law_reference(rule: dict[str, Any], relevance: str) -> dict[str, Any]:
    """Build a legal reference item for triggered rules."""

    return {
        "refType": "law",
        "title": f"{rule.get('rule_id')} · {rule.get('rule_name')}",
        "source": "法学规则库 rules_v1.json / legal_basis.md",
        "date": "",
        "registrationNo": "",
        "summary": str(rule.get("system_message", "")),
        "relevance": relevance,
    }

"""Local prior-right and precedent matching layer."""

from __future__ import annotations

from typing import Any

from app.services.rule_repository import build_hit_rule, build_law_reference, get_rule
from app.services.trademark_repository import build_trademark_reference, find_trademark_candidates


WELL_KNOWN_MARKS = {"louisvuitton", "chanel", "nike", "herms", "hermes", "starbucks", "mcdonalds", "kfc"}


def run_precedent_matcher(req: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Match submitted brand against local trademark bottom ledger."""

    candidates = find_trademark_candidates(
        str(req.get("brandName") or ""),
        str(req.get("englishName") or ""),
        str(req.get("niceClass") or ""),
    )
    hit_rules: list[dict[str, Any]] = []
    references: list[dict[str, Any]] = []

    for candidate in candidates:
        score = int(candidate.get("_matchScore", 0))
        exact = bool(candidate.get("_exactMatch"))
        overlap = bool(candidate.get("_classOverlap"))
        normalized = str(candidate.get("mark_name_normalized") or "").lower()

        if exact:
            rule = get_rule("VN-REL-001")
            note = (
                f"本地底账发现名称完全相同记录：{candidate.get('mark_name')}。"
                "该结果是重要冲突线索，仍需核验权利状态、地域范围和商品服务关系。"
            )
            hit_rules.append(
                build_hit_rule(
                    rule,
                    applicable=True,
                    note=note,
                    similarity_type="文字完全相同" if overlap else "文字完全相同-类别待核验",
                    similarity_score=100,
                )
            )
            references.append(build_law_reference(rule, note))
            references.append(build_trademark_reference(candidate, note))

            if str(candidate.get("current_status") or "") == "待复核":
                info_rule = get_rule("VN-INFO-003")
                info_note = "候选底账记录当前状态为待复核，来源、状态或核验日期不足，不能据此作出可靠结论。"
                hit_rules.append(build_hit_rule(info_rule, applicable=True, note=info_note))
                references.append(build_law_reference(info_rule, info_note))
            continue

        if score >= 72:
            rule = get_rule("VN-REL-002")
            note = (
                f"发现相似候选：{candidate.get('mark_name')}，算法筛查分值 {score}/100。"
                "该分值仅用于检索排序，不等同于法律上的混淆性近似结论。"
            )
            hit_rules.append(
                build_hit_rule(
                    rule,
                    applicable=True,
                    note=note,
                    similarity_type="文字近似候选" if overlap else "文字近似候选-跨类待核验",
                    similarity_score=score,
                )
            )
            references.append(build_law_reference(rule, note))
            references.append(build_trademark_reference(candidate, note))

            if str(candidate.get("current_status") or "") == "待复核" or "Firecrawl" in str(
                candidate.get("source_type") or ""
            ):
                info_rule = get_rule("VN-INFO-003")
                info_note = "候选记录来源或当前状态仍需复核，不能据此作出可靠结论。"
                hit_rules.append(build_hit_rule(info_rule, applicable=True, note=info_note))
                references.append(build_law_reference(info_rule, info_note))

        if normalized in WELL_KNOWN_MARKS or "高知名度" in str(candidate.get("risk_note") or ""):
            rule = get_rule("VN-FAM-001" if overlap else "VN-FAM-002")
            note = (
                f"{candidate.get('mark_name')} 在本地底账中被标注为高知名度/重点核验商标。"
                "如能依法证明为驰名商标，可能产生同类或跨类风险；系统只能提示驰名标识风险线索，不能自动认定其在越南构成驰名商标。"
            )
            hit_rules.append(
                build_hit_rule(
                    rule,
                    applicable=True,
                    note=note,
                    similarity_type="高知名度标识风险线索",
                    similarity_score=max(score, 75),
                )
            )
            references.append(build_law_reference(rule, note))

    return {"hitRules": hit_rules, "references": references}

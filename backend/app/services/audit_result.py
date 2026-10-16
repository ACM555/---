from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from app.services.legal_repository import LegalRepository


def _target_countries(request: dict[str, Any]) -> list[str]:
    values = request.get("targetMarkets") or request.get("targetCountries") or ["越南"]
    if not isinstance(values, list):
        return [str(values)]
    countries = [str(value).strip() for value in values if str(value).strip()]
    return countries or ["越南"]


def build_complete_audit_result(
    task_id: str,
    request: dict[str, Any],
    raw: dict[str, Any],
) -> dict[str, Any]:
    """Convert the active rule-engine output into the stable report API contract."""

    hit_rules = list(raw.get("hitRules") or [])
    references = list(raw.get("references") or [])
    suggestions = list(raw.get("suggestions") or [])
    risk_level = str(raw.get("riskLevel") or "low")
    risk_score = int(raw.get("riskScore") or 0)
    overall_result = str(raw.get("overallResult") or "")
    absolute_rules = [rule for rule in hit_rules if rule.get("ruleType") == "absolute"]
    relative_rules = [rule for rule in hit_rules if rule.get("ruleType") == "relative"]
    applicable_absolute = [rule for rule in absolute_rules if rule.get("applicable")]
    applicable_relative = [rule for rule in relative_rules if rule.get("applicable")]
    trademark_references = [item for item in references if item.get("refType") == "trademark"]
    case_references = [item for item in references if item.get("refType") == "case"]
    countries = _target_countries(request)
    country_codes = {"越南": "VN", "新加坡": "SG", "泰国": "TH", "印尼": "ID", "马来西亚": "MY"}
    selected_codes = {country_codes.get(country, country) for country in countries}
    for source in LegalRepository().list_sources_for_review():
        if source.country_code in selected_codes and source.legal_module == "M5":
            references.append({"refType": "law", "title": source.title, "source": "官方法源回查入口（法律内容待审核）", "sourceKind": "official_pointer", "sourceUrl": str(source.source_url), "date": source.verified_at.isoformat(), "version": "现行法规版本须在官方原文核验", "approvalStatus": "draft", "summary": source.supported_fact, "relevance": "只提供原文回查线索，不作为可注册性或侵权结论的依据。", "prerequisites": source.prerequisites, "registrationNo": ""})

    document_preview = str(raw.get("documentPreview") or "")
    official_references = [item for item in references if item.get("sourceKind") == "official_pointer"]
    if official_references:
        document_preview += "\n\n## 官方原文回查入口（法律内容待审核）\n\n内部筛查规则不是正式法源。以下入口不代替现行版本、具体条文及适用条件审核。\n"
        for reference in official_references:
            document_preview += f"\n- {reference['title']}\n  原文：{reference['sourceUrl']}\n  入口核对日期：{reference['date']}（不是法规生效日期）\n  版本：{reference['version']}\n  适用前提：{'；'.join(reference.get('prerequisites') or [])}\n"

    relative_score = max(
        [int(rule.get("similarityScore") or 0) for rule in applicable_relative] + [0]
    )
    visual_score = max(
        [
            int(rule.get("similarityScore") or 0)
            for rule in hit_rules
            if rule.get("similarityType")
        ]
        + [0]
    )
    cross_class_triggered = bool(applicable_relative and trademark_references)
    red_flags = [
        str(rule.get("note") or rule.get("content") or rule.get("article") or "需人工复核")
        for rule in hit_rules
        if rule.get("applicable")
    ]

    legacy_strategy = raw.get("registrationStrategy") or {}
    legacy_timeline = legacy_strategy.get("timeline") or []
    strategy_timeline = [
        {
            "stage": str(item.get("stage") or "人工复核"),
            "duration": str(item.get("duration") or "以主管机关现行流程为准"),
            "output": str(item.get("action") or item.get("output") or "复核记录"),
        }
        for item in legacy_timeline
    ]
    if not strategy_timeline:
        strategy_timeline = [
            {"stage": "提交前预检", "duration": "按项目安排", "output": "风险线索与待补事实"},
            {"stage": "本地代理复核", "duration": "以代理反馈为准", "output": "申请文件确认稿"},
            {"stage": "公告期监控", "duration": "以主管机关公告为准", "output": "异议线索与处置记录"},
        ]

    return {
        "taskId": task_id,
        "status": "done",
        "currentStep": 2,
        "progress": 100,
        "brandName": str(raw.get("brandName") or request.get("brandName") or ""),
        "niceClass": str(raw.get("niceClass") or request.get("niceClass") or ""),
        "goodsServices": str(raw.get("goodsServices") or request.get("goodsServices") or ""),
        "riskLevel": risk_level,
        "riskScore": risk_score,
        "overallResult": overall_result,
        "manualReviewRequired": bool(raw.get("manualReviewRequired")),
        "assessmentStatus": raw.get("assessmentStatus", "pending_verification"),
        "reportSchemaVersion": 2,
        "hitRules": hit_rules,
        "references": references,
        "suggestions": suggestions,
        "radarData": list(raw.get("radarData") or []),
        "matchedBrands": list(raw.get("matchedBrands") or []),
        "documentPreview": document_preview,
        "applicationDocumentPreview": str(raw.get("applicationDocumentPreview") or ""),
        "powerOfAttorneyPreview": str(raw.get("powerOfAttorneyPreview") or ""),
        "registrationStrategy": legacy_strategy,
        "summary": {
            "brandName": str(raw.get("brandName") or request.get("brandName") or ""),
            "niceClass": str(raw.get("niceClass") or request.get("niceClass") or ""),
            "submitTime": datetime.now(timezone.utc).isoformat(),
            "riskLevel": risk_level,
            "riskScore": risk_score,
            "overallResult": overall_result,
        },
        "absolute": {
            "hasRisk": bool(applicable_absolute),
            "rejectionProbability": max(
                [int(rule.get("similarityScore") or 0) for rule in applicable_absolute]
                + ([max(0, round(risk_score * 0.35))] if applicable_absolute else [0])
            ),
            "articles": [
                {
                    "article": str(rule.get("article") or "未命名规则"),
                    "content": str(rule.get("content") or ""),
                    "applicable": bool(rule.get("applicable")),
                    "note": str(rule.get("note") or ""),
                }
                for rule in absolute_rules
            ],
        },
        "relative": {
            "hasRisk": bool(applicable_relative),
            "conflicts": [
                {
                    "brandName": str(item.get("title") or "未知权利线索"),
                    "registeredClass": str(item.get("summary") or ""),
                    "registrationNo": str(item.get("registrationNo") or ""),
                    "similarityType": str(
                        applicable_relative[index].get("similarityType")
                        if index < len(applicable_relative)
                        else applicable_relative[0].get("similarityType") if applicable_relative else ""
                    ),
                    "similarityScore": int(
                        applicable_relative[index].get("similarityScore")
                        if index < len(applicable_relative)
                        else relative_score
                    ),
                }
                for index, item in enumerate(trademark_references)
            ],
            "precedents": [
                {
                    "caseName": str(item.get("title") or "未命名案例"),
                    "court": str(item.get("source") or ""),
                    "date": str(item.get("date") or ""),
                    "ruling": str(item.get("summary") or ""),
                    "relevance": str(item.get("relevance") or ""),
                }
                for item in case_references
            ],
        },
        "visual": {
            "radarData": list(raw.get("radarData") or []),
            "matchedBrands": list(raw.get("matchedBrands") or []),
            "analysisMode": "local-opencv",
            "summary": (
                "本地 OpenCV 仅提供图形特征与人工复核线索，不构成混淆或侵权判断。"
            ),
        },
        "intelligence": {
            "crossClassShield": {
                "triggered": cross_class_triggered,
                "score": relative_score,
                "title": "跨类保护线索扫描",
                "explanation": (
                    "已发现同时具备相对规则命中和可回查商标来源的跨类线索。"
                    if cross_class_triggered
                    else "当前本地资料未形成可验证的跨类权利冲突结论，仍建议正式提交前检索官方数据库。"
                ),
                "protectedElements": [str(item.get("title") or "") for item in trademark_references],
                "suggestedAction": "由目标国家代理人复核权利状态、类别覆盖和驰名保护适用条件。",
            },
            "refusalHistory": {
                "triggered": bool(red_flags),
                "title": "驳回与复核信号",
                "explanation": "汇总规则命中与图形筛查信号，不等同于主管机关历史驳回记录。",
                "redFlags": red_flags or ["当前未命中本地规则信号"],
                "evidence": [
                    "本地规则引擎命中记录",
                    "OpenCV 图形特征结果" if visual_score else "当前无图形高分线索",
                ],
            },
            "culturalReview": {
                "triggered": any("公共标志" in flag or "中文" in flag for flag in red_flags),
                "title": "文化与公共标志复核",
                "country": "、".join(countries),
                "rules": [
                    {
                        "label": "文字与公共标志适用性",
                        "severity": "medium" if red_flags else "low",
                        "note": "须结合目标国家语言、公共标志限制和完整图样由人工复核。",
                    }
                ],
            },
            "registrationStrategy": {
                "route": str(legacy_strategy.get("recommendedPath") or "目标国家单国申请优先评估"),
                "rationale": str(
                    legacy_strategy.get("reason")
                    or "先完成官方检索与本地代理复核，再确定单国或国际注册路径。"
                ),
                "marketCount": len(countries),
                "timeline": strategy_timeline,
                "costNotes": [
                    str(value)
                    for value in (
                        legacy_strategy.get("risks")
                        or ["费用与周期须以目标国家主管机关和代理机构的现行报价为准。"]
                    )
                ],
            },
            "monitoring": [
                {
                    "name": "目标国家商标公告监控",
                    "cadence": "建议每周",
                    "source": "目标国家知识产权主管机关公开公告",
                    "actionWindow": "以主管机关现行异议期限为准",
                },
                {
                    "name": "WIPO / TMview 近似线索复核",
                    "cadence": "建议每周",
                    "source": "WIPO Global Brand Database / TMview",
                    "actionWindow": "发现线索后转人工确认",
                },
            ],
        },
        "advice": {
            "recommendations": suggestions,
            "documentPreview": document_preview,
            "documentDownloadUrl": f"/api/audit/report/{task_id}/pdf",
        },
    }

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.config import settings
from app.database import get_task, update_task
from app.services.legal_engine import assess_absolute_rules
from app.services.trademark_service import find_text_conflicts, get_visual_benchmark_conflict
from app.services.vision_service import analyze_logo


def _load_cases() -> list[dict[str, Any]]:
    payload = json.loads(settings.case_db_path.read_text(encoding="utf-8"))
    return payload.get("records", [])


def _deduplicate_conflicts(conflicts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduplicated: dict[str, dict[str, Any]] = {}
    for conflict in conflicts:
        key = conflict.get("registrationNo") or f"{conflict.get('owner')}:{conflict.get('brandName')}"
        current = deduplicated.get(key)
        if current is None or conflict.get("similarityScore", 0) > current.get("similarityScore", 0):
            deduplicated[key] = conflict
    return sorted(deduplicated.values(), key=lambda item: item.get("similarityScore", 0), reverse=True)


def _countries(request: dict[str, Any]) -> list[str]:
    countries = request.get("targetCountries") or ["越南"]
    return [str(country) for country in countries if str(country).strip()] or ["越南"]


def _build_cross_class_shield(conflicts: list[dict[str, Any]], requested_class: str) -> dict[str, Any]:
    well_known_conflicts = [item for item in conflicts if item.get("wellKnown")]
    top_conflict = well_known_conflicts[0] if well_known_conflicts else (conflicts[0] if conflicts else None)
    requested_digits = "".join(ch for ch in requested_class if ch.isdigit()) or "目标类别"
    triggered = bool(top_conflict and (top_conflict.get("wellKnown") or top_conflict.get("similarityScore", 0) >= 80))
    protected_elements = ["国际大牌系列图形", "高识别度商业装潢", "跨类注册矩阵"]
    if top_conflict:
        protected_elements.insert(0, f"{top_conflict.get('brandName', '对标商标')} 权利族")
    return {
        "triggered": triggered,
        "score": int(top_conflict.get("similarityScore", 0)) if top_conflict else 12,
        "title": "跨类驰名保护扫描",
        "explanation": (
            f"系统将第 {requested_digits} 类请求同时放入同类近似层与跨类驰名保护层。"
            "若命中国际驰名品牌或跨类别注册矩阵，即使商品服务不完全相同，也会提示商业使用风险。"
        ),
        "protectedElements": protected_elements,
        "suggestedAction": (
            "先完成图形改稿与权利人系列商标检索，再进入越南提交。"
            if triggered
            else "当前未触发红牌，但正式提交前仍建议做 NOIP 与 TMview 复核。"
        ),
    }


def _build_refusal_history(
    brand_name: str,
    conflicts: list[dict[str, Any]],
    visual_score: int,
) -> dict[str, Any]:
    red_flags: list[str] = []
    if any(conflict.get("similarityScore", 0) >= 82 for conflict in conflicts):
        red_flags.append("相似标识已达到高置信冲突阈值")
    if visual_score >= 68:
        red_flags.append("图形结构触发四向对称/花瓣式高频元素")
    if any("\u4e00" <= char <= "\u9fff" for char in brand_name):
        red_flags.append("中文品牌名在越南可能被视为不常见文字，需补充越文/拉丁识别要素")
    triggered = bool(red_flags)
    return {
        "triggered": triggered,
        "title": "驳回前科红牌",
        "explanation": (
            "参照文档中的茉莉奶白案例逻辑，系统不只看当前是否近似，"
            "还会把历史驳回、无效、异议和持续商用事实作为主观攀附风险信号。"
        ),
        "redFlags": red_flags or ["未发现明显驳回前科信号"],
        "evidence": [
            "CNIPA/WIPO/NOIP 近似图形历史记录",
            "同一权利人跨类注册覆盖",
            "公开判例中的持续商用与获利推定逻辑",
        ],
    }


def _build_cultural_review(request: dict[str, Any], absolute_risk: bool) -> dict[str, Any]:
    countries = _countries(request)
    country = "、".join(countries)
    rules: list[dict[str, str]] = []
    if "越南" in countries:
        rules.extend(
            [
                {
                    "label": "纯汉字可注册性",
                    "severity": "high" if absolute_risk else "low",
                    "note": "越南审查中，纯汉字可能因不常见文字与显著性不足触发第 74.2(a) 风险。",
                },
                {
                    "label": "国旗国徽与民族英雄",
                    "severity": "medium",
                    "note": "标识不得误用国家机关、国旗国徽、民族英雄姓名肖像等绝对禁用元素。",
                },
                {
                    "label": "先公告后实审",
                    "severity": "medium",
                    "note": "越南存在约 5 个月公告异议窗口，参赛版会把该窗口纳入监控计划。",
                },
            ]
        )
    if any(country_name in countries for country_name in ["泰国", "印尼", "马来西亚"]):
        rules.append(
            {
                "label": "东盟公序良俗差异",
                "severity": "medium",
                "note": "泰国王室/佛像、印尼马来西亚宗教与酒猪元素需单独规则审查。",
            }
        )
    return {
        "triggered": any(rule["severity"] in {"high", "medium"} for rule in rules),
        "title": "文化禁忌审查",
        "country": country,
        "rules": rules,
    }


def _build_registration_strategy(
    request: dict[str, Any],
    risk_level: str,
) -> dict[str, Any]:
    market_count = max(int(request.get("plannedMarkets") or len(_countries(request)) or 1), len(_countries(request)))
    has_base_mark = bool(request.get("hasChinaBaseMark"))
    if market_count >= 3 and has_base_mark:
        route = "马德里国际注册 + 越南单国重点复核"
        rationale = "目标市场不少于 3 个且已有中国基础标，适合用马德里降低多国提交成本，同时对越南高风险类别做单国精修。"
    elif market_count >= 3:
        route = "先补中国基础标，再采用单国 + 马德里混合路径"
        rationale = "目标市场不少于 3 个，但尚缺中国基础标，直接全量单国提交成本较高，建议先补基础权利。"
    else:
        route = "越南单国申请优先"
        rationale = "目标市场较少，单国申请更快、更可控，便于围绕 NOIP 审查意见做本地化修改。"
    timeline = [
        {"stage": "提交前预检", "duration": "1-3 天", "output": "近似检索、禁忌审查、改稿建议"},
        {"stage": "申请文件本地化", "duration": "3-7 天", "output": "商品项越南化、委托书、申请信息确认"},
        {"stage": "公告异议监控", "duration": "约 5 个月", "output": "公告期抢注/异议提醒"},
        {"stage": "注册后风控", "duration": "持续", "output": "周公告扫描、相似新申请预警"},
    ]
    cost_notes = [
        "少于 3 国通常优先单国申请，降低中央打击风险。",
        "3 国以上可评估马德里路径，综合节省约 40%-60% 的多国代理成本。",
    ]
    if risk_level != "low":
        cost_notes.append("当前存在风险信号，应先改稿或补证据，避免把问题带入正式申请。")
    return {
        "route": route,
        "rationale": rationale,
        "marketCount": market_count,
        "timeline": timeline,
        "costNotes": cost_notes,
    }


def _build_monitoring() -> list[dict[str, str]]:
    return [
        {
            "name": "NOIP 周公告抢注预警",
            "cadence": "每周",
            "source": "越南工业产权官方公报 PDF",
            "actionWindow": "公告后约 5 个月异议窗口",
        },
        {
            "name": "TMview / WIPO 近似新申请",
            "cadence": "每 7 天",
            "source": "TMview、WIPO Global Brand Database",
            "actionWindow": "发现近似申请后进入异议或撤销评估",
        },
        {
            "name": "法规变动摘要",
            "cadence": "每月",
            "source": "ipvietnam.gov.vn Thông báo",
            "actionWindow": "影响申请、异议、维权流程时推送复核任务",
        },
    ]


def _recommendations(
    absolute_risk: bool,
    relative_risk: bool,
    cross_class_risk: bool = False,
    refusal_red_flag: bool = False,
) -> list[dict[str, str]]:
    recommendations: list[dict[str, str]] = []
    if absolute_risk:
        recommendations.append(
            {
                "priority": "P0",
                "title": "补充越南语或拉丁文字识别要素",
                "description": "避免仅以汉字作为申请标志，并由越南执业代理人复核显著性与翻译表达。",
            }
        )
    if relative_risk:
        recommendations.extend(
            [
                {
                    "priority": "P0",
                    "title": "暂停当前图形提交与商业投放",
                    "description": "在完成图形重构和越南官方数据库近似检索前，暂停使用当前高风险识别要素。",
                },
                {
                    "priority": "P1",
                    "title": "开展重点权利人跨类检索",
                    "description": "针对冲突权利人的文字、图形和系列商标进行同类及跨类检索，并保留官方检索记录。",
                },
            ]
        )
    if cross_class_risk:
        recommendations.append(
            {
                "priority": "P0",
                "title": "启动跨类驰名保护专项复核",
                "description": "围绕国际驰名品牌在越南的全类别注册、关联权利族和公共纹样私有化边界进行人工复核，避免只按尼斯同类判断。",
            }
        )
    if refusal_red_flag:
        recommendations.append(
            {
                "priority": "P1",
                "title": "补齐驳回前科与改稿证据链",
                "description": "保存每轮设计修改记录、公开检索截图和驳回/无效历史，证明独立创作与善意避让。",
            }
        )
    recommendations.append(
        {
            "priority": "P2",
            "title": "保全独立创作与首次使用证据",
            "description": "整理设计源文件、委托合同、修改记录、发布时间和商业使用材料，形成可核验时间线。",
        }
    )
    return recommendations


def _document_preview(
    brand_name: str,
    nice_class: str,
    overall_result: str,
    recommendations: list[dict[str, str]],
) -> str:
    recommendation_text = "\n".join(
        f"- [{item['priority']}] {item['title']}：{item['description']}" for item in recommendations
    )
    return f"""# 中国企业赴越商标防御性合规规划书

## 一、项目概况
审查对象：{brand_name}\n申请类别：{nice_class}

## 二、风险结论
{overall_result}

## 三、处置建议
{recommendation_text}

## 四、证据保全
建议保留商标设计源文件、委托协议、版本记录、首次公开及商业使用证据。

## 五、重要声明
本报告由公开数据和自动化规则生成，仅用于比赛演示与提交前风险筛查，不替代越南执业律师或商标代理人的正式法律意见。"""


def process_audit_task(task_id: str, image_path: Path) -> None:
    try:
        task = get_task(task_id)
        if task is None:
            raise RuntimeError("审查任务不存在")
        request = task["request"]
        update_task(task_id, status="processing", current_step=0, progress=15)

        legal = assess_absolute_rules(request["brandName"], request.get("englishName", ""))
        update_task(task_id, current_step=1, progress=45)

        vision = analyze_logo(image_path)
        text_conflicts = find_text_conflicts(
            request["brandName"],
            request.get("englishName", ""),
            request["niceClass"],
        )
        visual_conflict = get_visual_benchmark_conflict(vision.fourfold_score)
        conflicts = _deduplicate_conflicts(
            text_conflicts + ([visual_conflict] if visual_conflict else [])
        )
        relative_risk = bool(conflicts)
        update_task(task_id, current_step=2, progress=62)

        hit_rules = legal.hit_rules
        relative_score = max((conflict["similarityScore"] for conflict in conflicts), default=0)
        for rule in hit_rules:
            if rule["ruleType"] == "relative":
                rule["applicable"] = relative_risk
                rule["similarityType"] = (
                    conflicts[0]["similarityType"] if conflicts else ""
                )
                rule["similarityScore"] = relative_score
                rule["note"] = (
                    "本地商标库或图形基准检出跨类近似风险。"
                    if relative_risk
                    else "当前知识库未检出高置信度跨类攀附风险。"
                )

        references = list(legal.references)
        references.extend(
            {
                "refType": "trademark",
                "title": conflict["brandName"],
                "source": "IP Viet Nam public trademark search",
                "date": "",
                "registrationNo": conflict["registrationNo"],
                "summary": (
                    f"权利人：{conflict.get('owner') or '未知'}；类别："
                    f"{conflict.get('registeredClass') or '未标注'}；状态："
                    f"{conflict.get('status') or '未标注'}。"
                ),
                "relevance": (
                    f"{conflict['similarityType']}，评分 {conflict['similarityScore']}/100。"
                ),
                "sourceUrl": conflict.get("sourceUrl", ""),
            }
            for conflict in conflicts
        )

        precedents = [
            {
                "caseName": case["caseName"],
                "court": case.get("court", ""),
                "date": case.get("date", ""),
                "ruling": case.get("ruling", ""),
                "relevance": case.get("relevance", ""),
            }
            for case in _load_cases()
            if case.get("verified") and case.get("sourceUrl")
        ]

        score_candidates = [8]
        if legal.absolute_risk:
            score_candidates.append(legal.rejection_probability)
        if relative_score:
            score_candidates.append(relative_score)
        risk_score = min(100, max(score_candidates) + (5 if legal.absolute_risk and relative_risk else 0))
        risk_level = "high" if risk_score >= 75 else "medium" if risk_score >= 45 else "low"
        cross_class_shield = _build_cross_class_shield(conflicts, request["niceClass"])
        refusal_history = _build_refusal_history(
            request["brandName"], conflicts, vision.fourfold_score
        )
        cultural_review = _build_cultural_review(request, legal.absolute_risk)
        update_task(task_id, current_step=3, progress=78)
        if cross_class_shield["triggered"] and risk_score < 75:
            risk_score = min(100, max(risk_score, cross_class_shield["score"] + 6))
            risk_level = "high" if risk_score >= 75 else "medium" if risk_score >= 45 else "low"
        registration_strategy = _build_registration_strategy(request, risk_level)
        update_task(task_id, current_step=4, progress=88)
        if legal.absolute_risk and relative_risk:
            overall_result = "同时检出显著性绝对驳回风险与跨类近似风险，建议暂缓提交并进行人工复核。"
        elif legal.absolute_risk:
            overall_result = "检出汉字显著性风险，建议补充越南语或拉丁文字识别要素后再申请。"
        elif relative_risk:
            overall_result = "检出文字或图形近似风险，建议暂停提交并完成权利冲突专项检索。"
        elif cross_class_shield["triggered"]:
            overall_result = "检出跨类驰名保护信号，建议进入权利族与公共纹样边界专项复核后再提交。"
        else:
            overall_result = "当前规则库与视觉基准未检出高风险项，可进入人工复核与正式检索阶段。"

        recommendations = _recommendations(
            legal.absolute_risk,
            relative_risk,
            bool(cross_class_shield["triggered"]),
            bool(refusal_history["triggered"]),
        )
        visual_matches = [
            {
                "name": conflict["brandName"],
                "thumbnailUrl": conflict.get("thumbnailUrl") or "/lv-placeholder.svg",
                "matchScore": conflict["similarityScore"],
            }
            for conflict in conflicts
            if conflict["similarityType"].startswith("图形")
        ]
        submit_time = datetime.now(UTC).isoformat()
        result = {
            "taskId": task_id,
            "status": "done",
            "currentStep": 4,
            "progress": 100,
            "brandName": request["brandName"],
            "niceClass": request["niceClass"],
            "goodsServices": request["goodsServices"],
            "riskLevel": risk_level,
            "riskScore": risk_score,
            "overallResult": overall_result,
            "manualReviewRequired": risk_level != "low",
            "hitRules": hit_rules,
            "references": references,
            "summary": {
                "brandName": request["brandName"],
                "niceClass": request["niceClass"],
                "submitTime": submit_time,
                "riskLevel": risk_level,
                "riskScore": risk_score,
                "overallResult": overall_result,
            },
            "absolute": {
                "hasRisk": legal.absolute_risk,
                "rejectionProbability": legal.rejection_probability,
                "articles": [
                    {
                        "article": rule["article"],
                        "content": rule["content"],
                        "applicable": rule["applicable"],
                        "note": rule["note"],
                    }
                    for rule in hit_rules
                    if rule["ruleType"] == "absolute"
                ],
            },
            "relative": {
                "hasRisk": relative_risk,
                "conflicts": [
                    {
                        key: conflict[key]
                        for key in (
                            "brandName",
                            "registeredClass",
                            "registrationNo",
                            "similarityType",
                            "similarityScore",
                        )
                    }
                    for conflict in conflicts
                ],
                "precedents": precedents,
            },
            "visual": {
                "radarData": vision.radar_data,
                "matchedBrands": visual_matches,
                "analysisMode": "remote-assisted" if vision.model_analysis else "local-opencv",
                "summary": (
                    vision.model_analysis.get("summary")
                    if vision.model_analysis and vision.model_analysis.get("summary")
                    else vision.local_summary
                ),
            },
            "intelligence": {
                "crossClassShield": cross_class_shield,
                "refusalHistory": refusal_history,
                "culturalReview": cultural_review,
                "registrationStrategy": registration_strategy,
                "monitoring": _build_monitoring(),
            },
            "advice": {
                "recommendations": recommendations,
                "documentPreview": _document_preview(
                    request["brandName"], request["niceClass"], overall_result, recommendations
                ),
                "documentDownloadUrl": f"/api/audit/report/{task_id}/pdf",
            },
        }
        update_task(
            task_id,
            status="done",
            current_step=4,
            progress=100,
            result=result,
            error_message="",
        )
    except Exception as error:
        update_task(
            task_id,
            status="error",
            progress=100,
            error_message=str(error)[:500],
        )
    finally:
        image_path.unlink(missing_ok=True)

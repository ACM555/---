"""M4 cross-border trademark registration strategy engine."""

from __future__ import annotations

import re
from typing import Any


CORE_MARKETS = {"越南", "泰国", "印尼", "印度尼西亚"}


def _normalize_markets(markets: list[str] | None) -> list[str]:
    result: list[str] = []
    for market in markets or []:
        value = str(market or "").strip()
        if value and value not in result:
            result.append(value)
    return result or ["越南"]


def _is_broad_goods_services(goods_services: str) -> bool:
    text = goods_services.strip()
    if len(text) <= 12:
        return True
    broad_terms = {"商品", "服务", "餐饮", "食品", "饮料", "服装", "零售"}
    return text in broad_terms


def _localize_for_market(market: str, goods_services: str, nice_class: str) -> dict[str, str]:
    original = goods_services or "未填写商品/服务描述"
    class_no = re.search(r"(\d{1,2})", nice_class or "")
    class_label = f"第{class_no.group(1)}类" if class_no else "对应类别"

    if market == "越南":
        if _is_broad_goods_services(original):
            localized = f"{class_label}：请将“{original}”细化为具体商品/服务项目，例如服务场景、销售渠道、主要品类和目标消费对象。"
            note = "越南申请不宜使用过宽泛描述，建议按本地可接受注释细化。"
        else:
            localized = f"{class_label}：{original}。建议补充越南语/英文对应描述，并拆分过宽泛项目。"
            note = "越南市场需重点检查商品/服务描述是否具体、清晰。"
    else:
        localized = f"{class_label}：{original}。建议按{market}当地审查口径确认可接受表述。"
        note = "非越南市场当前给出策略级提示，正式提交前需由当地代理人复核。"

    return {
        "market": market,
        "original": original,
        "localized": localized,
        "note": note,
    }


def _cost_comparison(recommended_path: str, market_count: int, has_china_base: bool) -> list[dict[str, str]]:
    madrid_note = (
        "已有中国基础商标/申请，可作为马德里路径前提。"
        if has_china_base
        else "尚未确认中国基础商标/申请，马德里路径存在前置条件不足。"
    )

    return [
        {
            "option": "单国申请",
            "costLevel": "低-中" if market_count <= 2 else "高",
            "speed": "较快",
            "suitableFor": "目标市场不超过 2 国，或越南等核心市场需要优先落地",
            "note": "流程直接，便于按各国审查口径精细处理。",
        },
        {
            "option": "马德里体系",
            "costLevel": "中",
            "speed": "中等",
            "suitableFor": "目标市场达到 3 国以上，且已有中国基础商标/申请",
            "note": f"{madrid_note} 多国布局通常可节省约 40-60% 的重复申请成本。",
        },
        {
            "option": "单国 + 马德里混合",
            "costLevel": "中-高",
            "speed": "核心市场较快，其余市场统一推进",
            "suitableFor": "包含越南、泰国、印尼等核心市场，同时又需要多国防御布局",
            "note": "核心市场单国优先，其余市场用马德里体系补齐覆盖。",
        },
    ]


def _timeline(recommended_path: str, markets: list[str], has_china_base: bool) -> list[dict[str, str]]:
    base_step = (
        {
            "stage": "中国基础确认",
            "duration": "1-2 周",
            "action": "确认中国基础商标注册/申请状态，评估是否可作为马德里基础。",
        }
        if has_china_base
        else {
            "stage": "中国基础准备",
            "duration": "2-4 周",
            "action": "如选择马德里路径，需先准备或确认中国基础申请；否则优先单国申请。",
        }
    )

    return [
        {
            "stage": "提交前检索",
            "duration": "1-2 周",
            "action": "完成目标市场文字、图形和商品/服务近似检索。",
        },
        base_step,
        {
            "stage": "核心市场提交",
            "duration": "2-4 周",
            "action": f"优先处理{', '.join(markets[:3])}等重点市场的申请材料和本地代理确认。",
        },
        {
            "stage": "多国扩展",
            "duration": "3-6 个月",
            "action": f"按“{recommended_path}”推进后续国家覆盖，并监控异议、补正和基础标稳定性。",
        },
    ]


def build_registration_strategy(req: dict[str, Any]) -> dict[str, Any]:
    """Build M4 structured strategy result using the agreed decision tree."""

    markets = _normalize_markets(req.get("targetMarkets"))
    market_count = len(markets)
    has_china_base = bool(req.get("hasChinaBase"))
    goods_services = str(req.get("goodsServices") or req.get("businessDescription") or "")
    nice_class = str(req.get("niceClass") or "")
    has_core_market = bool(CORE_MARKETS.intersection(markets))

    risks: list[str] = []

    if market_count <= 2:
        recommended_path = "单国申请"
        reason = "目标市场不超过 2 国，优先采用单国申请，路径更直接，便于按当地审查口径快速处理。"
        cost_saving = "成本节省不作为主要目标，重点是速度、确定性和本地化质量。"
    elif has_core_market:
        recommended_path = "单国 + 马德里混合路径"
        reason = "目标市场达到 3 国以上，且包含越南、泰国或印尼等核心市场，建议核心市场单国优先，其余市场用马德里体系扩展。"
        cost_saving = "相较全部单国申请，多国部分可通过马德里体系节省约 40-60% 的重复申请成本。"
    else:
        recommended_path = "马德里体系"
        reason = "目标市场达到 3 国以上，可考虑以马德里体系统一推进多国覆盖。"
        cost_saving = "相较逐国重复申请，通常可节省约 40-60% 的多国申请成本。"

    if market_count >= 3 and not has_china_base:
        risks.append("马德里体系通常需要中国基础商标注册或申请；当前未确认中国基础，需先补齐前置条件或改走单国申请。")

    if market_count >= 3 and has_china_base:
        risks.append("需防范“5年中央打击”：基础标在 5 年内被撤销、无效或驳回，可能影响马德里国际注册。")

    if "越南" in markets and _is_broad_goods_services(goods_services):
        risks.append("越南不宜使用过宽泛商品/服务描述，需按本地注释细化，否则可能影响审查稳定性。")

    if not risks:
        risks.append("正式提交前仍需由目标市场当地代理人复核商品/服务描述和在先权利检索结果。")

    return {
        "targetMarkets": markets,
        "hasChinaBase": has_china_base,
        "recommendedPath": recommended_path,
        "reason": reason,
        "costSaving": cost_saving,
        "costComparison": _cost_comparison(recommended_path, market_count, has_china_base),
        "timeline": _timeline(recommended_path, markets, has_china_base),
        "localizedGoodsServices": [
            _localize_for_market(market, goods_services, nice_class)
            for market in markets
        ],
        "risks": risks,
    }

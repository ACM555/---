"""Deterministic hard-rule checks for submitted trademark text."""

from __future__ import annotations

import re
from typing import Any

from app.services.rule_repository import build_hit_rule, build_law_reference, get_rule


HAN_RE = re.compile(r"^[\u4e00-\u9fff]+$")
GENERIC_TERMS = {
    "咖啡",
    "奶茶",
    "茶饮",
    "餐厅",
    "服装",
    "食品",
    "美妆",
    "化妆品",
    "饮料",
}
BROAD_SERVICE_TERMS = {"商品", "服务", "产品", "业务", "零售", "餐饮", "食品"}
PUBLIC_SYMBOL_TERMS = {"国旗", "国徽", "国歌", "胡志明", "政府", "机关", "军队", "红十字"}
SUCCESS_RATE_TERMS = {"成功率", "通过率", "驳回率", "几率", "概率"}


def run_hard_rules(req: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Run local deterministic checks and return hit rules + references."""

    brand_name = str(req.get("brandName") or "").strip()
    english_name = str(req.get("englishName") or "").strip()
    nice_class = str(req.get("niceClass") or "").strip()
    goods_services = str(req.get("goodsServices") or req.get("businessDescription") or "").strip()

    hit_rules: list[dict[str, Any]] = []
    references: list[dict[str, Any]] = []

    if not nice_class:
        rule = get_rule("VN-INFO-001")
        note = "缺少有效的尼斯类别，系统不能完成同类/类似类别冲突筛查。"
        hit_rules.append(build_hit_rule(rule, applicable=True, note=note))
        references.append(build_law_reference(rule, note))

    if not goods_services or len(goods_services) < 8 or goods_services in BROAD_SERVICE_TERMS:
        rule = get_rule("VN-INFO-002")
        note = "商品或服务描述为空、过短或过于宽泛，需补充主营业务、目标市场和具体商品/服务。"
        hit_rules.append(build_hit_rule(rule, applicable=True, note=note))
        references.append(build_law_reference(rule, note))

    if brand_name and HAN_RE.fullmatch(brand_name) and not english_name:
        rule = get_rule("VN-ABS-001")
        note = "品牌名仅由中文构成，且未提供拉丁文字或越南语读音辅助识别，建议人工复核整体显著性。"
        hit_rules.append(build_hit_rule(rule, applicable=True, note=note))
        references.append(build_law_reference(rule, note))

    if brand_name in GENERIC_TERMS:
        rule = get_rule("VN-ABS-003")
        note = "品牌名接近商品或服务通用名称，可能缺乏区分商品/服务来源的显著性。"
        hit_rules.append(build_hit_rule(rule, applicable=True, note=note))
        references.append(build_law_reference(rule, note))

    merged_text = f"{brand_name} {english_name} {goods_services}"
    if any(term in merged_text for term in PUBLIC_SYMBOL_TERMS):
        rule = get_rule("VN-ABS-005")
        note = "输入信息疑似包含公共标志、国家机关或受保护人物相关元素，需要人工核验授权和适用限制。"
        hit_rules.append(build_hit_rule(rule, applicable=True, note=note))
        references.append(build_law_reference(rule, note))

    if any(term in merged_text for term in SUCCESS_RATE_TERMS):
        rule = get_rule("VN-INFO-005")
        note = "不能提供注册成功率、通过率或驳回率；系统只能基于现有输入输出风险线索和需人工核验事项。"
        hit_rules.append(build_hit_rule(rule, applicable=True, note=note))
        references.append(build_law_reference(rule, note))

    return {"hitRules": hit_rules, "references": references}

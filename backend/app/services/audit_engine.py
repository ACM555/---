"""Orchestrates the local Outbound-Guard audit pipeline."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.services.hard_rules import run_hard_rules
from app.services.precedent_matcher import run_precedent_matcher
from app.services.registration_strategy import build_registration_strategy
from app.services.rule_repository import get_rule, score_for_rule
from app.services.vision_agent import run_vision_agent


def _risk_level(score: int) -> str:
    if score >= 70:
        return "high"
    if score >= 40:
        return "medium"
    return "low"


def _priority_for_score(score: int) -> str:
    if score >= 70:
        return "P0"
    if score >= 40:
        return "P1"
    return "P2"


def _dedupe_items(items: list[dict[str, Any]], keys: tuple[str, ...]) -> list[dict[str, Any]]:
    seen: set[tuple[str, ...]] = set()
    result: list[dict[str, Any]] = []
    for item in items:
        signature = tuple(str(item.get(key, "")) for key in keys)
        if signature in seen:
            continue
        seen.add(signature)
        result.append(item)
    return result


def _estimate_score(hit_rules: list[dict[str, Any]]) -> int:
    score = 18
    for hit_rule in hit_rules:
        if not hit_rule.get("applicable"):
            continue
        article = str(hit_rule.get("article") or "")
        content = str(hit_rule.get("content") or "")
        if "公共标志" in content or "重大法律风险" in content:
            score = max(score, 95)
        elif "完全相同" in str(hit_rule.get("similarityType") or ""):
            score = max(score, 82)
        elif "视觉相似候选" in str(hit_rule.get("note") or ""):
            score = max(score, 60)
        elif "驰名" in content or "高知名度" in str(hit_rule.get("note") or ""):
            score = max(score, 78)
        elif "缺少" in content or "不足" in content or "信息" in article:
            score = max(score, 48)
        elif "缺乏显著性" in content:
            score = max(score, 58)
        else:
            score = max(score, 55)

        score = max(score, int(hit_rule.get("similarityScore") or 0))
    return min(score, 100)


def _build_overall_result(risk_level: str, score: int, hit_rules: list[dict[str, Any]]) -> str:
    triggered = [rule for rule in hit_rules if rule.get("applicable")]
    if not triggered:
        return "当前有限范围内未命中明显风险；仍建议在正式提交前由越南代理人进行数据库复核。"

    if risk_level == "high":
        return f"发现高风险审查线索，综合风险分值 {score}/100。建议暂缓直接提交，先完成法律人工复核和标识调整。"
    if risk_level == "medium":
        return f"发现需关注的审查线索，综合风险分值 {score}/100。建议补充材料并进行人工复核后再提交。"
    return f"当前仅发现低风险或信息性提示，综合风险分值 {score}/100。可进入下一轮人工确认。"


def _build_suggestions(hit_rules: list[dict[str, Any]], score: int) -> list[dict[str, str]]:
    suggestions: list[dict[str, str]] = []
    priority = _priority_for_score(score)

    for hit_rule in hit_rules:
        if not hit_rule.get("applicable"):
            continue
        note = str(hit_rule.get("note") or "")
        title = "处理规则命中项"
        if "尼斯类别" in note:
            title = "补充尼斯分类"
        elif "商品或服务描述" in note:
            title = "细化商品/服务描述"
        elif "底账" in note or "相似候选" in note:
            title = "复核在先商标冲突"
        elif "中文" in note:
            title = "增强越南市场可识别性"
        elif "视觉" in note or "图形" in note:
            title = "进行图形人工复核"

        suggestions.append({"priority": priority, "title": title, "description": note})

    if not suggestions:
        suggestions.append(
            {
                "priority": "P2",
                "title": "进行正式提交前复核",
                "description": "当前本地规则未发现明确命中，但本系统不能替代越南主管机关数据库检索和律师审查。",
            }
        )

    return _dedupe_items(suggestions, ("title", "description"))[:6]


def _build_graphic_description(hit_rules: list[dict[str, Any]]) -> str:
    """Summarize image-analysis related notes for the report template."""

    visual_notes = [
        str(rule.get("note") or "")
        for rule in hit_rules
        if "视觉" in str(rule.get("note") or "")
        or "图形" in str(rule.get("note") or "")
        or "OpenCV" in str(rule.get("note") or "")
    ]
    if visual_notes:
        return "；".join(visual_notes[:2])
    return "当前未提取到明确高风险图形要素；建议结合上传图样由人工复核。"


def _rule_code(rule: dict[str, Any], index: int) -> str:
    return str(rule.get("ruleId") or rule.get("ruleName") or f"VN_R{index:02d}")


def _build_issue_section(triggered_rules: list[dict[str, Any]], risk_level: str) -> str:
    if not triggered_rules:
        return "⚠️ **当前本地规则未命中明确风险线索，不等于不存在法律风险。**"

    rows = [
        "| 序号 | 规则 | 标题 | 具体问题 |",
        "|------|------|------|--------|",
    ]
    for index, rule in enumerate(triggered_rules[:8], start=1):
        rule_code = _rule_code(rule, index)
        title = str(rule.get("content") or rule.get("article") or "需人工复核")
        note = str(rule.get("note") or rule.get("similarityType") or "当前规则命中，需进一步复核。")
        rows.append(f"| {index} | {rule_code} | {title} | {note} |")

    if risk_level == "high":
        rows.append("")
        rows.append("> ⚠️ 上述规则包含高风险或严重冲突线索，建议先修改再提交。")
    elif risk_level == "medium":
        rows.append("")
        rows.append("> 🟡 上述问题可通过补充材料、调整名称/图形或细化商品服务描述降低风险。")

    return "\n".join(rows)


def _build_legal_basis_section(
    references: list[dict[str, Any]],
    hit_rules: list[dict[str, Any]],
    risk_level: str,
) -> str:
    law_refs = [reference for reference in references if reference.get("refType") == "law"]
    lines: list[str] = []

    for reference in law_refs[:4]:
        title = str(reference.get("title") or "越南《知识产权法》相关条款")
        summary = str(reference.get("summary") or reference.get("relevance") or "需结合法条原文进行人工复核。")
        source = str(reference.get("source") or "本地法条知识库")
        lines.append(f"**{title}**（来源：{source}）")
        lines.append(f"> \"{summary}\"")
        lines.append("")

    if not lines:
        if risk_level == "low":
            lines.append("越南《知识产权法》第72条可作为核验标识区分性要件的条文线索；当前资料不足以判断可注册性：")
            lines.append("> \"商标应包含足以将其所有者的商品或服务与他人的商品或服务区分开的特征\"")
        else:
            lines.append("**越南《知识产权法》第73、74条相关审查规则**")
            lines.append("> \"商标不得包含法律禁止使用的标志，且应具备足以区分商品或服务来源的显著性。\"")
        lines.append("")

    trademark_refs = [reference for reference in references if reference.get("refType") == "trademark"]
    case_refs = [reference for reference in references if reference.get("refType") == "case"]
    if trademark_refs:
        lines.append("**在先商标/底账引用**")
        for reference in trademark_refs[:3]:
            registration_no = str(reference.get("registrationNo") or "未提供注册号")
            lines.append(
                f"- {reference.get('title') or '未命名商标'}（{registration_no}）："
                f"{reference.get('summary') or reference.get('relevance') or '需人工复核'}"
            )
        lines.append("")

    if case_refs:
        lines.append("**相关判例/案例线索**")
        for reference in case_refs[:3]:
            lines.append(
                f"- {reference.get('title') or '未命名案例'}："
                f"{reference.get('summary') or reference.get('relevance') or '需人工复核'}"
            )
        lines.append("")

    if hit_rules and risk_level != "low":
        lines.append("**规则命中补充说明**")
        for index, rule in enumerate([rule for rule in hit_rules if rule.get("applicable")][:4], start=1):
            lines.append(f"- {_rule_code(rule, index)}：{rule.get('article') or rule.get('content') or '需人工复核'}")

    return "\n".join(lines).strip()


def _build_document_preview(
    req: dict[str, Any],
    risk_level: str,
    score: int,
    overall: str,
    hit_rules: list[dict[str, Any]],
    references: list[dict[str, Any]],
    suggestions: list[dict[str, str]],
) -> str:
    triggered_rules = [rule for rule in hit_rules if rule.get("applicable")]
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    brand_name = str(req.get("brandName") or "")
    nice_class = str(req.get("niceClass") or "")
    goods_services = str(req.get("goodsServices") or req.get("businessDescription") or "")
    graphic_description = _build_graphic_description(hit_rules)
    rule_count = len(triggered_rules)
    legal_basis = _build_legal_basis_section(references, hit_rules, risk_level)
    issue_section = _build_issue_section(triggered_rules, risk_level)

    return f"""# M5 商标与技术出海风险提示清单（内测）
**生成时间**：{generated_at}
**风险线索等级**：{risk_level}

## 已提供事实
- 标识/名称：{brand_name or '待补充'}
- 类别或范围：{nice_class or '待补充'}
- 商品/服务或业务场景：{goods_services or '待补充'}
- 图样说明：{graphic_description}

## 风险提示与资料线索
{overall}

{issue_section}

## 可回查资料线索
{legal_basis or '当前没有可用于实质判断的已审核法律资料；需人工复核。'}

## 待补事实与建议动作
1. 核对标识权属、申请/注册状态、商品服务范围及使用或公开情况。
2. 核对目标国主管机关原文、现行版本和具体办理要求。
3. 如涉及相似标识、权属、许可、侵权或申请策略，交由当地专业人士人工复核。

## 使用边界
本清单仅依据当前本地规则和资料线索生成，不能判断商标是否可注册、是否构成侵权、是否应提交申请或任何结果；不构成律师法律意见、主管机关决定或结果保证。
"""

    if risk_level == "high":
        return f"""# 📋 越南商标注册合规预检报告
**生成时间**：{generated_at}  
**风险评级**：🔴 **高风险**

## 1. 基本信息
- **审查品牌**：{brand_name}
- **注册类别**：{nice_class}
- **图形描述**：{graphic_description}
- **商品/服务描述**：{goods_services}

## 2. 风险等级
🔴 **高风险**

**结论**：强烈不建议直接向越南知识产权局提交该商标申请。

**原因**：{overall} 当前触发 **{rule_count}** 条核心风险规则，综合风险分值为 **{score}/100**。如不修改后直接提交，存在较高驳回或被异议风险。

---

## 3. 发现的问题

触发了以下 **{rule_count}** 条核心规则：

{issue_section}

---

## 4. 法律依据

{legal_basis}

---

## 5. 建议类别
**⛔ C. 强烈不建议提交**

在完成重新设计、命名优化或冲突排查之前，不应直接提交申请。

---

## 6. 行动清单

**立即行动**（第1周内）：
1. 暂缓提交当前商标申请。
2. 组织内部评审，确认品牌名称、图形和商品/服务描述的修改方向。
3. 联系越南本地 IP 代理机构进行人工复核。

**修改设计**（第2-4周）：
1. 如涉及纯中文或描述性词汇，建议增加拉丁字母、英文或越南语元素。
2. 如涉及图形相似候选，调整图形轮廓、对称结构、视觉重心和主要装饰元素。
3. 保留独立创作过程、设计稿迭代记录和品牌使用证据。

**提交前准备**（第5-8周）：
1. 委托越南本地代理机构进行 NOIP 近似检索。
2. 准备品牌使用证据、授权文件和差异化说明。
3. 修改定稿后再评估是否正式提交。

**成本估算**：
- 重新设计：¥5,000-20,000
- 近似检索：¥3,000-5,000
- 代理申请：¥2,000-3,000
- **总计**：¥10,000-28,000（用于降低驳回与异议成本）

---

## 7. 免责声明

本报告基于 **2025年版越南《知识产权法》** 的公开条款、本地规则库和本地商标底账生成，仅供商业决策参考，**不构成任何正式的法律意见**。

- ⚠️ 本工具基于规则库自动判断，可能存在边界情况或法律解释差异。
- ⚠️ 实际商标注册的成功与否最终由越南国家知识产权局（NOIP）决定。
- ⚠️ 该报告不能替代专业律师或 IP 代理机构的咨询意见。

**强烈建议**：在提交任何正式申请前，咨询具有越南执业资格的商标律师或 IP 代理机构。

---

**更新日期**：2025年7月  
**报告版本**：1.0
"""

    if risk_level == "medium":
        return f"""# 📋 越南商标注册合规预检报告
**生成时间**：{generated_at}  
**风险评级**：🟡 **中风险**

## 1. 基本信息
- **审查品牌**：{brand_name}
- **注册类别**：{nice_class}
- **图形描述**：{graphic_description}
- **商品/服务描述**：{goods_services}

## 2. 风险等级
🟡 **中风险**

**结论**：建议进行修改后再向越南知识产权局提交。

**原因**：{overall} 当前触发 **{rule_count}** 条风险或信息性规则，综合风险分值为 **{score}/100**。通过修改名称、图形或商品/服务描述，可进一步降低驳回风险。

---

## 3. 发现的问题

触发了以下 **{rule_count}** 条规则：

{issue_section}

---

## 4. 法律依据

{legal_basis}

---

## 5. 建议类别
**🟡 B. 修改后提交**

通过以下修改，可将风险降至较低水平。

---

## 6. 行动清单

**优化设计**（第1-2周）：
1. 改进品牌显著性，避免纯描述性表达。
2. 如包含纯中文，建议增加拉丁字母、英文或越南语版本。
3. 如图形存在视觉复核提示，调整轮廓、对称结构和主要装饰元素。

**近似检索**（第2-3周）：
1. 委托越南代理机构检索相同或近似商标。
2. 核对同类和类似类别中是否存在在先冲突。
3. 如发现相近商标，准备差异化说明。

**修改定稿**（第3周）：
1. 确定最终名称和图形版本。
2. 准备正式申请材料。
3. 选择越南本地代理机构代理提交。

**费用参考**：
- 近似检索：¥2,500-4,000
- 代理申请：¥2,000-3,000
- **总计**：¥4,500-7,000

**人工复核提示**：办理周期取决于主管机关流程、材料与个案事实，须核验原文与最新程序要求。

---

## 7. 免责声明

本报告仅供决策参考，不构成法律意见。实际申请前请咨询越南本地律师或 IP 代理机构。

---

**版本**：1.0
"""

    return f"""# 📋 越南商标注册合规预检报告
**生成时间**：{generated_at}  
**风险评级**：✅ **低风险**

## 1. 基本信息
- **审查品牌**：{brand_name}
- **注册类别**：{nice_class}
- **图形描述**：{graphic_description}
- **商品/服务描述**：{goods_services}

## 2. 风险等级
✅ **低风险**

**结论**：该商标可进入越南知识产权局注册准备流程。

**原因**：{overall} 当前未发现明显的绝对驳回理由或高强度在先冲突线索，综合风险分值为 **{score}/100**。

---

## 3. 发现的问题

✅ **未发现明显违规问题**

该商标在以下方面表现良好：
- ✅ 具有一定显著性。
- ✅ 未命中当前规则库中的国家象征或人物肖像类严重风险。
- ✅ 未发现明显描述性或欺骗性标志风险。
- ✅ 未发现高强度驰名商标冲突线索。

---

## 4. 法律依据

{legal_basis}

---

## 5. 建议类别
**⚠️ A. 当前资料线索有限，需人工复核**

---

## 6. 行动清单

**准备申请材料**（第1-2周）：
1. 收集品牌使用证据，例如发票、宣传材料、网站或社交媒体证据。
2. 确认商标所有人信息，包括企业名称、注册地址和联系方式。
3. 整理 Logo 文件、类别信息和商品/服务描述。

**近似检索**（第2周）：
1. 委托越南本地代理机构进行 NOIP 数据库检索。
2. 确认不存在高度近似商标。
3. 如发现潜在冲突，准备差异化说明。

**提交申请**（第3周）：
1. 选择信誉良好的越南 IP 代理机构。
2. 准备正式申请文件。
3. 提交至越南知识产权局（NOIP）。
4. 获取申请号和确认信息。

**后续维护**（申请后）：
1. 关注 NOIP 审查通知。
2. 如有驳回通知，及时准备答辩材料。
3. 最终获得注册证书通常需结合官方审查周期判断。

**费用参考**：
- 近似检索：¥2,000-3,500
- 代理申请费：¥1,500-2,500
- 政府申请费：约¥1,500
- **总计**：¥5,000-7,500

**推荐时间表**：
```text
第1周：准备材料
第2周：近似检索 + 定稿
第3周：正式提交
预期结果时间：通常需 12-18 个月内结合官方流程取得结果
```

---

## 7. 免责声明

本报告基于现有商标审查规则生成，仅供参考。

- ⚠️ 报告反映的是当前风险评估，实际审查结果由越南知识产权局最终决定。
- ⚠️ 商标审查涉及多个因素，本报告无法覆盖所有情况。
- ⚠️ 如果申请过程中商标法或审查口径发生变化，结论可能需要调整。

**建议**：虽然风险评估为低，但仍建议与越南本地 IP 专业人士咨询，确保申请流程顺利。

---

**版本**：1.0
"""


def _value_or_pending(value: Any) -> str:
    text = str(value or "").strip()
    return text or "待补充"


def _target_country(req: dict[str, Any]) -> str:
    markets = req.get("targetMarkets") or ["越南"]
    if isinstance(markets, list) and markets:
        return str(markets[0] or "越南")
    return "越南"


def _localized_name(req: dict[str, Any]) -> str:
    english_name = str(req.get("englishName") or "").strip()
    brand_name = str(req.get("brandName") or "").strip()
    return english_name or brand_name or "待补充"


def _build_application_document(req: dict[str, Any], hit_rules: list[dict[str, Any]]) -> str:
    """Build Document 01 from the uploaded DOCX template: trademark application form."""

    brand_name = _value_or_pending(req.get("brandName"))
    english_name = _value_or_pending(req.get("englishName"))
    localized_name = _localized_name(req)
    nice_class = _value_or_pending(req.get("niceClass"))
    goods_services = _value_or_pending(req.get("goodsServices") or req.get("businessDescription"))
    logo_description = _build_graphic_description(hit_rules)
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return f"""# Document 01
# 商标注册申请书
## Trademark Application Form
### Đơn đăng ký nhãn hiệu

---

## AI Metadata（文书生成信息）

| 项目 | 内容 |
|------|------|
| Document ID | AUTO-{datetime.now().strftime("%Y%m%d%H%M%S")}-APP |
| AI Engine | GPT + RAG + Rule Engine |
| Rule Version | Vietnam Rule Set v2025.1 |
| Document Version | M6 v2.0 |
| Target Country | {_target_country(req)} |
| Output Language | 中文 / English / Vietnamese |
| Generate Time | {generated_at} |
| Related Risk Report | 自动关联当前审查任务 |

---

## 一、申请人信息（Applicant Information）

| 中文 | English | 目标国家语言 |
|------|----------|-------------|
| 企业名称 | Company Name | 待补充 |
| 企业英文名称 | English Name | 待补充 |
| 企业注册地址 | Registered Address | 待补充 |
| 联系电话 | Phone | 待补充 |
| Email | Email | 待补充 |
| 官网 | Website | 待补充 |
| 企业注册号 | Registration Number | 待补充 |

---

## 二、商标信息（Trademark Information）

| 中文 | English | 目标国家语言 |
|------|----------|-------------|
| 商标名称 | Trademark | {brand_name} |
| 商标英文 | English Trademark | {english_name} |
| 本地化名称 | Localized Trademark | {localized_name} |
| 商标类型 | Trademark Type | 文字 + 图形 / Word + Device |
| Nice分类 | Nice Classification | {nice_class} |

---

## 三、Logo 信息（Logo Information）

### Logo

【AI自动关联用户上传 Logo，正式提交前请替换为 NOIP 接受的清晰图样文件】

---

### Logo Description

| 中文 | English | 目标国家语言 |
|------|----------|-------------|
| {logo_description} | AI visual description pending legal review. | Mô tả logo cần đại diện sở hữu trí tuệ Việt Nam rà soát. |

---

## 四、商品/服务

| 中文 | English | 目标国家语言 |
|------|----------|-------------|
| 商品描述 | Goods | {goods_services} |
| 服务描述 | Services | {goods_services} |

---

## 五、申请声明（Applicant Declaration）

| 中文 | English | 目标国家语言 |
|------|----------|-------------|
| 本申请信息真实有效。 | The information provided is true and accurate. | Thông tin trong đơn là trung thực và chính xác. |
| 本申请人拥有合法商标权利。 | Applicant declares lawful ownership. | Người nộp đơn tuyên bố có quyền hợp pháp đối với nhãn hiệu. |

---

## 六、Applicant Signature

```text
Applicant Signature

_________________________

Date

_________________________

Company Seal

_________________________
```

---

# AI 自动填充来源

✅ 企业档案（当前未填写部分保留为“待补充”）  
✅ Logo识别  
✅ 品牌名称  
✅ AI三语本地化  
✅ 国家规则库
"""


def _build_power_of_attorney_document(req: dict[str, Any]) -> str:
    """Build Document 02 from the uploaded DOCX template: trademark agent POA."""

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return f"""# Document 02
# 商标代理委托书
## Power of Attorney
### Giấy ủy quyền

---

## AI Metadata（文书生成信息）

| 项目 | 内容 |
|------|------|
| Document ID | AUTO-{datetime.now().strftime("%Y%m%d%H%M%S")}-POA |
| AI Engine | GPT + RAG + Rule Engine |
| Rule Version | Vietnam Rule Set v2025.1 |
| Document Version | M6 v2.0 |
| Target Country | {_target_country(req)} |
| Output Language | 中文 / English / Vietnamese |
| Generate Time | {generated_at} |
| Related Risk Report | 自动关联当前审查任务 |

---

## 一、委托人（Applicant）

| 中文 | English | 目标国家语言 |
|------|----------|-------------|
| 企业名称 | Applicant | 待补充 |
| 地址 | Address | 待补充 |
| 法定代表人 | Legal Representative | 待补充 |

---

## 二、代理机构（Trademark Agent）

| 中文 | English | 目标国家语言 |
|------|----------|-------------|
| 代理机构 | Trademark Agent | 待补充 |
| 联系方式 | Contact | 待补充 |
| 地址 | Address | 待补充 |

---

## 三、授权事项（Authorization Scope）

☑ 提交商标申请  
☑ Respond to Office Action  
☑ 修改申请  
☑ 官方缴费  
☑ 领取注册证书  
☑ 提交异议  
☑ 提交复审  
☑ 商标续展

---

## 四、授权声明（Authorization Statement）

| 中文 | English | 目标国家语言 |
|------|----------|-------------|
| 本人授权上述代理机构办理目标国家商标注册事项。 | Applicant authorizes the above representative to act on its behalf. | Người nộp đơn ủy quyền cho đại diện nêu trên thực hiện thủ tục đăng ký nhãn hiệu tại quốc gia mục tiêu. |

---

## 五、Applicant Signature

```text
Applicant Signature

_________________________

Date

_________________________

Company Seal

_________________________
```

---

### AI 自动生成依据

- 企业档案
- 国家代理规则
- 国家授权模板
- 国家法律术语库

> 注：本委托书为模板化草案，正式提交前应由越南本地代理机构确认签章、认证、公证及语言版本要求。
"""

    return f"""# 📋 越南商标注册合规预检报告
**生成时间**：{generated_at}  
**风险评级**：✅ **低风险**

## 1. 基本信息
- **审查品牌**：{brand_name}
- **注册类别**：{nice_class}
- **图形描述**：{graphic_description}
- **商品/服务描述**：{goods_services}

## 2. 风险等级
✅ **低风险**

**结论**：该商标可进入越南知识产权局注册准备流程。

**原因**：{overall} 当前未发现明显的绝对驳回理由或高强度在先冲突线索，综合风险分值为 **{score}/100**。

---

## 3. 发现的问题

✅ **未发现明显违规问题**

该商标在以下方面表现良好：
- ✅ 具有一定显著性。
- ✅ 未命中当前规则库中的国家象征或人物肖像类严重风险。
- ✅ 未发现明显描述性或欺骗性标志风险。
- ✅ 未发现高强度驰名商标冲突线索。

---

## 4. 法律依据

{legal_basis}

---

## 5. 建议类别
**⚠️ A. 当前资料线索有限，需人工复核**

---

## 6. 行动清单

**准备申请材料**（第1-2周）：
1. 收集品牌使用证据，例如发票、宣传材料、网站或社交媒体证据。
2. 确认商标所有人信息，包括企业名称、注册地址和联系方式。
3. 整理 Logo 文件、类别信息和商品/服务描述。

**近似检索**（第2周）：
1. 委托越南本地代理机构进行 NOIP 数据库检索。
2. 确认不存在高度近似商标。
3. 如发现潜在冲突，准备差异化说明。

**提交申请**（第3周）：
1. 选择信誉良好的越南 IP 代理机构。
2. 准备正式申请文件。
3. 提交至越南知识产权局（NOIP）。
4. 获取申请号和确认信息。

**后续维护**（申请后）：
1. 关注 NOIP 审查通知。
2. 如有驳回通知，及时准备答辩材料。
3. 最终获得注册证书通常需结合官方审查周期判断。

**费用参考**：
- 近似检索：¥2,000-3,500
- 代理申请费：¥1,500-2,500
- 政府申请费：约¥1,500
- **总计**：¥5,000-7,500

**推荐时间表**：
```text
第1周：准备材料
第2周：近似检索 + 定稿
第3周：正式提交
预期结果时间：通常需 12-18 个月内结合官方流程取得结果
```

---

## 7. 免责声明

本报告基于现有商标审查规则生成，仅供参考。

- ⚠️ 报告反映的是当前风险评估，实际审查结果由越南知识产权局最终决定。
- ⚠️ 商标审查涉及多个因素，本报告无法覆盖所有情况。
- ⚠️ 如果申请过程中商标法或审查口径发生变化，结论可能需要调整。

**建议**：虽然风险评估为低，但仍建议与越南本地 IP 专业人士咨询，确保申请流程顺利。

---

**版本**：1.0
"""


def run_audit(req: dict[str, Any]) -> dict[str, Any]:
    """Run the local three-layer audit pipeline."""

    hard = run_hard_rules(req)
    precedent = run_precedent_matcher(req)
    vision = run_vision_agent(req)
    registration_strategy = build_registration_strategy(req)

    hit_rules = _dedupe_items(
        hard["hitRules"] + precedent["hitRules"] + vision["hitRules"],
        ("article", "content", "similarityType", "note"),
    )
    references = _dedupe_items(
        hard["references"] + precedent["references"] + vision["references"],
        ("refType", "title", "source", "summary"),
    )

    score = _estimate_score(hit_rules)
    risk_level = _risk_level(score)
    overall = _build_overall_result(risk_level, score, hit_rules)
    manual_review_required = bool([rule for rule in hit_rules if rule.get("applicable")]) or score >= 40

    suggestions = _build_suggestions(hit_rules, score)

    return {
        "brandName": req.get("brandName") or "",
        "niceClass": req.get("niceClass") or "",
        "goodsServices": req.get("goodsServices") or req.get("businessDescription") or "",
        "riskLevel": risk_level,
        "riskScore": score,
        "overallResult": overall,
        "hitRules": hit_rules,
        "references": references,
        "suggestions": suggestions,
        "manualReviewRequired": manual_review_required,
        "radarData": vision.get("radarData", []),
        "matchedBrands": vision.get("matchedBrands", []),
        "documentPreview": _build_document_preview(req, risk_level, score, overall, hit_rules, references, suggestions),
        "applicationDocumentPreview": _build_application_document(req, hit_rules),
        "powerOfAttorneyPreview": _build_power_of_attorney_document(req),
        "registrationStrategy": registration_strategy,
    }

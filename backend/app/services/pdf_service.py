from __future__ import annotations

from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))


def _text(value: object) -> str:
    return escape(str(value or ""))


def build_audit_pdf(result: dict) -> bytes:
    output = BytesIO()
    document = SimpleDocTemplate(
        output,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=f"{result.get('brandName', '')} 越南商标合规报告",
        author="Outbound-Guard",
    )
    styles = getSampleStyleSheet()
    base = ParagraphStyle(
        "ChineseBody",
        parent=styles["BodyText"],
        fontName="STSong-Light",
        fontSize=10.5,
        leading=17,
        textColor=colors.HexColor("#1f2937"),
        wordWrap="CJK",
        spaceAfter=7,
    )
    title = ParagraphStyle(
        "ChineseTitle",
        parent=base,
        fontSize=22,
        leading=30,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#0f3d66"),
        spaceAfter=10,
    )
    heading = ParagraphStyle(
        "ChineseHeading",
        parent=base,
        fontSize=14,
        leading=20,
        textColor=colors.HexColor("#0f3d66"),
        spaceBefore=8,
        spaceAfter=8,
    )
    small = ParagraphStyle(
        "ChineseSmall",
        parent=base,
        fontSize=8.5,
        leading=13,
        textColor=colors.HexColor("#6b7280"),
    )
    story = [
        Paragraph("中国企业赴越商标防御性合规规划书", title),
        Paragraph("Outbound-Guard 自动化初筛报告", base),
        Spacer(1, 8 * mm),
    ]
    summary = result["summary"]
    summary_rows = [
        ["品牌名称", _text(summary.get("brandName"))],
        ["尼斯分类", _text(summary.get("niceClass"))],
        ["风险等级", _text(summary.get("riskLevel", "").upper())],
        ["风险分值", f"{summary.get('riskScore', 0)}/100"],
        ["审查时间", _text(summary.get("submitTime"))],
    ]
    summary_table = Table(summary_rows, colWidths=[34 * mm, 122 * mm])
    summary_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), "STSong-Light"),
                ("FONTSIZE", (0, 0), (-1, -1), 9.5),
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#e8f1f8")),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#0f3d66")),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    story.extend(
        [
            summary_table,
            Spacer(1, 7 * mm),
            Paragraph("审查结论", heading),
            Paragraph(_text(result.get("overallResult")), base),
            Paragraph("规则命中", heading),
        ]
    )
    for rule in result.get("hitRules", []):
        status = "触发" if rule.get("applicable") else "未触发"
        story.append(
            Paragraph(
                f"<b>{_text(rule.get('article'))}</b> [{status}]<br/>"
                f"{_text(rule.get('content'))}<br/>审查说明：{_text(rule.get('note'))}",
                base,
            )
        )
    story.append(Paragraph("冲突商标", heading))
    conflicts = result.get("relative", {}).get("conflicts", [])
    if conflicts:
        conflict_rows = [["品牌", "类别", "注册/申请号", "类型", "评分"]]
        conflict_rows.extend(
            [
                _text(item.get("brandName")),
                _text(item.get("registeredClass")),
                _text(item.get("registrationNo")),
                _text(item.get("similarityType")),
                _text(item.get("similarityScore")),
            ]
            for item in conflicts
        )
        conflict_table = Table(
            conflict_rows,
            repeatRows=1,
            colWidths=[31 * mm, 20 * mm, 34 * mm, 49 * mm, 17 * mm],
        )
        conflict_table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, -1), "STSong-Light"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f3d66")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#cbd5e1")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        story.append(conflict_table)
    else:
        story.append(Paragraph("当前知识库未检出冲突商标。", base))
    intelligence = result.get("intelligence", {})
    if intelligence:
        story.append(Paragraph("参赛版智能情报", heading))
        cross_class = intelligence.get("crossClassShield", {})
        refusal = intelligence.get("refusalHistory", {})
        cultural = intelligence.get("culturalReview", {})
        strategy = intelligence.get("registrationStrategy", {})
        story.append(
            Paragraph(
                f"<b>{_text(cross_class.get('title'))}</b><br/>"
                f"评分：{_text(cross_class.get('score'))}/100<br/>"
                f"{_text(cross_class.get('explanation'))}<br/>"
                f"建议：{_text(cross_class.get('suggestedAction'))}",
                base,
            )
        )
        story.append(
            Paragraph(
                f"<b>{_text(refusal.get('title'))}</b><br/>"
                f"{_text(refusal.get('explanation'))}<br/>"
                f"红牌信号：{_text('；'.join(refusal.get('redFlags', [])))}",
                base,
            )
        )
        story.append(
            Paragraph(
                f"<b>{_text(cultural.get('title'))}</b><br/>"
                f"目标国家：{_text(cultural.get('country'))}<br/>"
                f"推荐路径：{_text(strategy.get('route'))}<br/>"
                f"{_text(strategy.get('rationale'))}",
                base,
            )
        )
    story.extend([PageBreak(), Paragraph("处置建议", heading)])
    for item in result.get("advice", {}).get("recommendations", []):
        story.append(
            Paragraph(
                f"<b>[{_text(item.get('priority'))}] {_text(item.get('title'))}</b><br/>"
                f"{_text(item.get('description'))}",
                base,
            )
        )
    story.extend(
        [
            Paragraph("法律与数据来源", heading),
        ]
    )
    for reference in result.get("references", []):
        story.append(
            Paragraph(
                f"<b>{_text(reference.get('title'))}</b><br/>"
                f"来源：{_text(reference.get('source'))}；编号："
                f"{_text(reference.get('registrationNo'))}<br/>"
                f"{_text(reference.get('summary'))}",
                small,
            )
        )
    story.extend(
        [
            Spacer(1, 8 * mm),
            Paragraph("重要声明", heading),
            Paragraph(
                "本报告基于公开数据、本地规则和自动化视觉特征生成，仅用于比赛演示及提交前风险筛查。"
                "它不构成正式法律意见，最终申请策略应由越南执业律师或商标代理人结合最新法律、审查实践及完整证据作出。",
                small,
            ),
        ]
    )
    document.build(story)
    return output.getvalue()

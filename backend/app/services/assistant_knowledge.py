from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class KnowledgeDocument:
    id: str
    title: str
    content: str


SYSTEM_GUIDES: tuple[KnowledgeDocument, ...] = (
    KnowledgeDocument(
        id="system-workflow",
        title="Outbound Guard 使用流程",
        content=(
            "Outbound Guard 用于中国企业进入越南市场前的商标合规审查。"
            "推荐流程：先在品牌资产录入品牌名称、图样与类别；再在智能审查页面选择目标国家和尼斯分类；"
            "提交后到审查进度查看任务；完成后在报告中心阅读风险、命中规则和注册建议。"
        ),
    ),
    KnowledgeDocument(
        id="audit-boundary",
        title="审查结论与人工复核边界",
        content=(
            "系统的规则引擎和审查报告用于风险提示与材料准备，不构成律师意见或官方注册决定。"
            "高风险、近似商标冲突、跨语种翻译、权属争议和时效问题应交由专业人士复核。"
        ),
    ),
    KnowledgeDocument(
        id="document-checklist",
        title="提交审查前的材料清单",
        content=(
            "建议准备：商标文字和图样、商品或服务类别、目标国家、申请主体名称、授权或使用证明、"
            "已知近似标识及历史申请资料。图像应清晰，扫描件应包含完整页码和印章信息。"
        ),
    ),
    KnowledgeDocument(
        id="image-guidance",
        title="图样材料说明",
        content=(
            "上传图样后，助手可协助识别可见文字、颜色、图形构成和可能需要人工确认的模糊区域。"
            "图像理解只用于辅助资料整理和风险解释，不能替代商标近似判定或人工检索。"
        ),
    ),
)

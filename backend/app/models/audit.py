from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class AuditRequest(BaseModel):
    """POST /api/audit request body."""

    brandName: str = Field(..., description="品牌名称", max_length=50)
    englishName: str = Field("", description="品牌英文名称", max_length=100)
    niceClass: str = Field(..., description="尼斯分类，如 '第43类-餐饮服务'")
    goodsServices: str = Field(..., description="商品/服务描述，品牌主营业务和目标市场")
    targetMarkets: list[str] = Field(default_factory=lambda: ["越南"], description="目标市场列表")
    hasChinaBase: bool = Field(False, description="是否已有中国基础商标注册/申请")
    logo: str = Field(..., description="Logo 图片 Base64 字符串（不含 data:image 前缀）")


class AuditResponse(BaseModel):
    """POST /api/audit synchronous response body."""

    taskId: str = Field(..., description="审查任务ID，UUID格式")
    status: Literal["pending", "processing", "done", "error"] = Field(
        "pending",
        description="审查状态",
    )
    message: str = Field("审查已提交，正在处理中", description="提示信息")


class HitRule(BaseModel):
    """命中规则条目。"""

    ruleId: str = Field("", description="内部筛查规则编号，用于溯源，不是法条编号")
    ruleName: str = Field("", description="内部筛查规则名称")
    ruleType: Literal["absolute", "relative"] = Field(
        ...,
        description="规则线索类型：absolute=标识/公共规则线索，relative=在先权利或相似线索",
    )
    article: str = Field(..., description="内部规则或资料定位标签，不能作为官方法条引用")
    content: str = Field("", description="内部规则提示摘要，不是正式法律原文")
    applicable: bool = Field(..., description="是否适用/触发")
    similarityType: str = Field("", description="相似类型，如'图形相似-四叶花卉几何结构'")
    similarityScore: int = Field(0, description="技术特征或本地匹配信号，不代表法律风险或结果概率", ge=0, le=100)
    note: str = Field("", description="审查说明")


class Reference(BaseModel):
    """引用依据条目。"""

    model_config = ConfigDict(extra="allow")

    refType: Literal["law", "case", "trademark"] = Field(
        ...,
        description="依据类型：law=法条, case=判例, trademark=商标注册记录",
    )
    title: str = Field(..., description="标题/案件名/品牌名")
    source: str = Field("", description="来源，如'WIPO Madrid Monitor'或'苏州市中级人民法院'")
    date: str = Field("", description="日期，YYYY-MM-DD 格式")
    registrationNo: str = Field("", description="注册号（trademark类型时）")
    summary: str = Field("", description="摘要/判决摘要")
    relevance: str = Field("", description="与本案的关联性说明")


class Suggestion(BaseModel):
    """建议条目。"""

    priority: Literal["P0", "P1", "P2"] = Field(..., description="优先级")
    title: str = Field(..., description="建议标题")
    description: str = Field(..., description="建议详细描述")


class CostComparisonItem(BaseModel):
    """跨域注册策略成本对比项。"""

    option: str = Field(..., description="注册路径选项")
    costLevel: str = Field(..., description="成本等级")
    speed: str = Field(..., description="速度/周期特征")
    suitableFor: str = Field(..., description="适用场景")
    note: str = Field("", description="说明")


class TimelineItem(BaseModel):
    """跨域注册策略时间轴项。"""

    stage: str = Field(..., description="阶段")
    duration: str = Field(..., description="流程信息（须以主管机关现行要求核验）")
    action: str = Field(..., description="关键动作")


class LocalizedGoodsServiceItem(BaseModel):
    """商品/服务本地化改写项。"""

    market: str = Field(..., description="目标市场")
    original: str = Field(..., description="原始商品/服务描述")
    localized: str = Field(..., description="本地化改写建议")
    note: str = Field("", description="说明")


class RegistrationStrategy(BaseModel):
    """M4 跨域注册策略。"""

    targetMarkets: list[str] = Field(default_factory=list, description="目标市场")
    hasChinaBase: bool = Field(False, description="是否已有中国基础商标注册/申请")
    recommendedPath: str = Field("", description="推荐路径")
    reason: str = Field("", description="推荐理由")
    costSaving: str = Field("", description="成本节省说明")
    costComparison: list[CostComparisonItem] = Field(default_factory=list, description="成本对比表")
    timeline: list[TimelineItem] = Field(default_factory=list, description="时间轴")
    localizedGoodsServices: list[LocalizedGoodsServiceItem] = Field(
        default_factory=list,
        description="商品/服务本地化改写",
    )
    risks: list[str] = Field(default_factory=list, description="策略风险提示")


class AuditResult(BaseModel):
    """GET /api/audit/result/{taskId} response body."""

    model_config = ConfigDict(extra="allow")

    taskId: str = Field(..., description="审查任务ID")
    status: Literal["pending", "processing", "done", "error"] = Field(..., description="审查状态")
    currentStep: int = Field(
        0,
        description="当前步骤 0=法条匹配 1=视觉比对 2=综合评估",
        ge=0,
        le=2,
    )
    progress: int = Field(0, description="进度百分比 0-100", ge=0, le=100)
    errorMessage: str = Field("", description="错误信息，status=error 时有值")
    brandName: str = Field("", description="品牌名称")
    niceClass: str = Field("", description="尼斯分类")
    goodsServices: str = Field("", description="商品/服务描述")
    riskLevel: Literal["high", "medium", "low"] = Field("low", description="风险等级")
    riskScore: int = Field(0, description="风险分值 0-100", ge=0, le=100)
    overallResult: str = Field("", description="总体结论，一句话")
    hitRules: list[HitRule] = Field(default_factory=list, description="命中的规则列表")
    references: list[Reference] = Field(default_factory=list, description="引用依据列表")
    suggestions: list[Suggestion] = Field(default_factory=list, description="合规建议列表")
    manualReviewRequired: bool = Field(False, description="是否需要人工复核")
    radarData: list[dict[str, Any]] = Field(
        default_factory=list,
        description="雷达图数据，每项含 dimension/target/benchmark",
    )
    matchedBrands: list[dict[str, Any]] = Field(
        default_factory=list,
        description="匹配品牌列表，每项含 name/thumbnailUrl/matchScore",
    )
    documentPreview: str = Field("", description="M5 商标与技术出海风险提示清单 Markdown 预览")
    applicationDocumentPreview: str = Field("", description="商标注册申请书 Markdown 预览")
    powerOfAttorneyPreview: str = Field("", description="商标代理委托书 Markdown 预览")
    registrationStrategy: RegistrationStrategy = Field(
        default_factory=RegistrationStrategy,
        description="M4 跨域注册策略",
    )


class UnifiedResponse(BaseModel):
    """统一响应格式。"""

    code: int = Field(0, description="0=成功，非0=失败")
    message: str = Field("success", description="提示信息")
    data: AuditResponse | AuditResult | dict[str, Any] | None = Field(None, description="业务数据")

from __future__ import annotations

from typing import Any


MODULES: list[dict[str, Any]] = [
    {
        "key": "M1",
        "name": "外商投资准入与公司设立",
        "status": "demo",
        "coverage": 0,
        "features": ["主体类型", "行业准入", "股权控制", "许可登记"],
        "output": "核验投资结构与适用前提，列出待补事实与人工复核事项",
    },
    {
        "key": "M2",
        "name": "跨境商事合同审查与违约风险防控",
        "status": "demo",
        "coverage": 0,
        "features": ["合同主体", "交付付款", "适用法", "违约证据"],
        "output": "依据已审核资料提示合同核验事项，不保证履约或回款",
    },
    {
        "key": "M3",
        "name": "跨境货物运输与贸易合规",
        "status": "demo",
        "coverage": 0,
        "features": ["货物与路线", "贸易术语", "原产地单证", "清关主体"],
        "output": "形成贸易与运输资料核验清单，提示许可与责任事实缺口",
    },
    {
        "key": "M4",
        "name": "东盟劳动用工与签证合规",
        "status": "demo",
        "coverage": 0,
        "features": ["雇主与岗位", "人员国籍", "工作地点", "签证材料"],
        "output": "核验用工与工作许可的适用事实，不承诺许可或办理期限",
    },
    {
        "key": "M5",
        "name": "知识产权布局与技术出海保护",
        "status": "demo",
        "coverage": 0,
        "features": ["商标资料", "权属证据", "技术保护", "审查报告"],
        "output": "提供有限范围的商标资料核验、风险提示与 PDF 报告",
    },
    {
        "key": "M6",
        "name": "跨境争议解决与货款追偿",
        "status": "demo",
        "coverage": 0,
        "features": ["争议事实", "通知证据", "管辖约定", "人工复核"],
        "output": "列出争议程序与证据核验事项，不保证胜诉、执行或回款",
    },
]


COUNTRY_RULES: list[dict[str, Any]] = [
    {
        "country": "越南",
        "riskTags": ["纯汉字", "国旗国徽", "先公告后实审", "5个月异议窗口"],
        "legalBasis": "Vietnam IP Law Article 72-76",
        "reviewFocus": "显著性、公共秩序、相对近似和公告异议",
        "timeline": "形式审查 1 个月，公告 2 个月，实质审查约 9-12 个月",
        "strategy": "高风险标识建议先做本地文字可读性改稿，再提交单国申请。",
    },
    {
        "country": "泰国",
        "riskTags": ["王室符号", "佛像", "宗教敬意", "公序良俗"],
        "legalBasis": "Trademark Act and criminal/public order rules",
        "reviewFocus": "王室、宗教和公共秩序风险",
        "timeline": "审查周期约 12-18 个月，公告后可异议",
        "strategy": "含宗教/王室联想图形必须先做人工复核。",
    },
    {
        "country": "印尼",
        "riskTags": ["宗教符号", "酒类", "猪元素", "欺骗性描述"],
        "legalBasis": "Trademark Law and public morality rules",
        "reviewFocus": "宗教与清真消费语境",
        "timeline": "形式审查、公告、实质审查合计约 10-16 个月",
        "strategy": "食品饮料、日化和服饰类优先检查宗教敏感语义。",
    },
    {
        "country": "马来西亚",
        "riskTags": ["伊斯兰符号", "酒类", "猪元素", "政府标识"],
        "legalBasis": "Trade Marks Act and examination practice",
        "reviewFocus": "宗教、公序良俗和政府标识",
        "timeline": "通常 12-18 个月完成注册流程",
        "strategy": "避免将清真语境与酒类、猪元素、政府符号混用。",
    },
    {
        "country": "菲律宾",
        "riskTags": ["欺骗性描述", "暴力元素", "官方徽章"],
        "legalBasis": "IP Code and examination guidelines",
        "reviewFocus": "欺骗性、冒犯性和官方标识",
        "timeline": "约 8-14 个月，公告期可被第三方异议",
        "strategy": "营销夸张语应转成描述性较弱的品牌表达。",
    },
    {
        "country": "新加坡",
        "riskTags": ["欺骗性", "官方标识", "公共利益"],
        "legalBasis": "Trade Marks Act",
        "reviewFocus": "相对宽松，但仍需排除欺骗性和官方标识",
        "timeline": "约 6-12 个月，适合作为区域化布局首站之一",
        "strategy": "适合低风险品牌先做英文/本地化名称试水。",
    },
]


BRAND_ASSETS: list[dict[str, Any]] = [
    {
        "brandId": "BR-2026-001",
        "name": "墨兰奶白",
        "englishName": "Molan Milk White",
        "owner": "广州墨兰餐饮管理有限公司",
        "niceClasses": ["第43类", "第30类", "第35类"],
        "targetCountries": ["越南", "泰国", "新加坡"],
        "portfolioStatus": "待改稿",
        "riskLevel": "high",
        "riskScore": 87,
        "lastAuditAt": "2026-07-18 21:40",
        "nextAction": "移除四叶花高相似图形，补充越南语可读名称。",
    },
    {
        "brandId": "BR-2026-002",
        "name": "Mộc Lan",
        "englishName": "Moc Lan",
        "owner": "杭州木兰服饰有限公司",
        "niceClasses": ["第25类", "第35类"],
        "targetCountries": ["越南", "马来西亚"],
        "portfolioStatus": "可提交",
        "riskLevel": "low",
        "riskScore": 18,
        "lastAuditAt": "2026-07-18 19:25",
        "nextAction": "建议追加图形黑白稿与中英文主体证明。",
    },
    {
        "brandId": "BR-2026-003",
        "name": "蓝莲供应链",
        "englishName": "Blue Lotus Supply",
        "owner": "深圳蓝莲跨境供应链有限公司",
        "niceClasses": ["第39类", "第42类"],
        "targetCountries": ["泰国", "印尼", "菲律宾"],
        "portfolioStatus": "人工复核",
        "riskLevel": "medium",
        "riskScore": 56,
        "lastAuditAt": "2026-07-17 16:12",
        "nextAction": "确认莲花图形是否触发宗教联想，必要时替换为抽象物流符号。",
    },
    {
        "brandId": "BR-2026-004",
        "name": "云杉出海",
        "englishName": "SpruceGo",
        "owner": "上海云杉科技有限公司",
        "niceClasses": ["第9类", "第42类"],
        "targetCountries": ["新加坡", "越南"],
        "portfolioStatus": "监控中",
        "riskLevel": "low",
        "riskScore": 22,
        "lastAuditAt": "2026-07-16 10:08",
        "nextAction": "进入公告期监控，观察近似英文组合申请。",
    },
]


MONITORING_ALERTS: list[dict[str, Any]] = [
    {
        "alertId": "AL-7001",
        "title": "越南公告期出现近似“MO LAN”餐饮服务申请",
        "severity": "high",
        "country": "越南",
        "brandName": "墨兰奶白",
        "source": "NOIP Official Gazette",
        "window": "剩余 23 天",
        "status": "需处理",
        "owner": "法务负责人",
        "createdAt": "2026-07-18 09:30",
        "recommendation": "准备异议材料，重点证明在先使用与消费者混淆可能。",
    },
    {
        "alertId": "AL-7002",
        "title": "印尼食品饮料类新增宗教敏感词审查提示",
        "severity": "medium",
        "country": "印尼",
        "brandName": "蓝莲供应链",
        "source": "Local Counsel Bulletin",
        "window": "规则更新",
        "status": "跟进中",
        "owner": "区域代理人",
        "createdAt": "2026-07-17 14:05",
        "recommendation": "涉及食品类延伸申请时，增加清真语境人工复核。",
    },
    {
        "alertId": "AL-7003",
        "title": "新加坡第42类近似英文组合低风险观察",
        "severity": "low",
        "country": "新加坡",
        "brandName": "云杉出海",
        "source": "IPOS Search",
        "window": "持续监控",
        "status": "观察",
        "owner": "系统自动",
        "createdAt": "2026-07-16 18:42",
        "recommendation": "保持周报推送，无需立即发起异议。",
    },
]


DATA_SOURCE_STATUS: list[dict[str, Any]] = [
    {
        "name": "NOIP 越南商标检索",
        "type": "官方检索",
        "status": "online",
        "coverage": 91,
        "freshness": "T+1",
        "lastSync": "2026-07-18 23:10",
        "note": "覆盖文字商标、申请人、公告期状态与基础类别。",
    },
    {
        "name": "WIPO Madrid Monitor",
        "type": "国际注册",
        "status": "online",
        "coverage": 88,
        "freshness": "T+1",
        "lastSync": "2026-07-18 22:35",
        "note": "用于马德里路线与国际指定国状态核验。",
    },
    {
        "name": "TMview / EUIPO 聚合库",
        "type": "聚合检索",
        "status": "online",
        "coverage": 84,
        "freshness": "T+2",
        "lastSync": "2026-07-17 21:10",
        "note": "用于跨区域近似与权利族线索补强。",
    },
    {
        "name": "本地案例与法律规则库",
        "type": "规则引擎",
        "status": "online",
        "coverage": 79,
        "freshness": "实时",
        "lastSync": "2026-07-19 08:00",
        "note": "沉淀比赛文档规则、示例案例和禁忌审查策略。",
    },
]


def get_platform_overview() -> dict[str, Any]:
    return {
        "positioning": "面向中国企业进入东盟市场的跨境商事法律 AI 助手",
        "slogan": "投资、合同、贸易、用工、知识产权与争议六模块资料核验",
        "healthScore": 86,
        "riskTrend": [
            {"date": "07-13", "high": 3, "medium": 8, "low": 18},
            {"date": "07-14", "high": 5, "medium": 6, "low": 22},
            {"date": "07-15", "high": 4, "medium": 11, "low": 19},
            {"date": "07-16", "high": 6, "medium": 10, "low": 24},
            {"date": "07-17", "high": 8, "medium": 13, "low": 28},
            {"date": "07-18", "high": 7, "medium": 16, "low": 31},
        ],
        "modules": MODULES,
        "dataSources": [item["name"] for item in DATA_SOURCE_STATUS],
        "sla": [
            {"name": "文本近似检索", "target": "<200ms", "status": "production-ready"},
            {"name": "图形粗筛 + 精排", "target": "<2s", "status": "demo-ready"},
            {"name": "规则引擎", "target": "<50ms", "status": "production-ready"},
            {"name": "综合报告生成", "target": "<3s", "status": "demo-ready"},
        ],
        "businessModel": [
            {"name": "Starter", "price": "基础预检免费", "buyer": "跨境卖家"},
            {"name": "Pro", "price": "¥1999/月起", "buyer": "出海企业法务"},
            {"name": "Expert Report", "price": "¥800/次", "buyer": "品牌与代理机构"},
            {"name": "Legal Referral", "price": "15%-25% 分成", "buyer": "律所/代理所"},
        ],
    }


def get_country_rules() -> list[dict[str, Any]]:
    return COUNTRY_RULES


def get_brand_assets(
    tasks: list[dict[str, Any]] | None = None, owner: str = "当前用户"
) -> list[dict[str, Any]]:
    assets = []
    for task in tasks or []:
        if task["status"] != "done":
            continue
        risk_level = task["riskLevel"] or "low"
        review_required = task["manualReviewRequired"] or risk_level != "low"
        assets.append(
            {
                "brandId": f"BR-{task['taskId']}",
                "taskId": task["taskId"],
                "name": task["brandName"] or "未命名品牌",
                "englishName": task.get("englishName", ""),
                "owner": owner,
                "niceClasses": [task["niceClass"]] if task["niceClass"] else [],
                "targetCountries": task["targetCountries"],
                "portfolioStatus": "人工复核" if review_required else "待核验",
                "riskLevel": risk_level,
                "riskScore": task["riskScore"] or 0,
                "assessmentStatus": task.get("assessmentStatus", "pending_verification"),
                "lastAuditAt": task["updatedAt"],
                "nextAction": "查看审查报告，核对资料适用前提并完成必要的人工复核。",
                "isDemo": False,
            }
        )
    return assets + [{**asset, "isDemo": True} for asset in BRAND_ASSETS]


def get_monitoring_alerts() -> list[dict[str, Any]]:
    return MONITORING_ALERTS


def get_data_source_status() -> list[dict[str, Any]]:
    return [
        {
            **source,
            "status": "scheduled",
            "freshness": "演示数据",
            "lastSync": "未接入实时同步",
            "note": f"演示状态，不代表外部服务实时可用或已同步。{source['note']}",
        }
        for source in DATA_SOURCE_STATUS
    ]


def build_report_center(tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    reports = []
    for task in tasks:
        if task["status"] != "done":
            continue
        reports.append(
            {
                "reportId": f"RP-{task['taskId'][:8].upper()}",
                "taskId": task["taskId"],
                "brandName": task["brandName"] or "未命名品牌",
                "niceClass": task["niceClass"] or "未选择类别",
                "targetCountries": task["targetCountries"],
                "riskLevel": task["riskLevel"] or "low",
                "riskScore": task["riskScore"] or 0,
                "manualReviewRequired": task["manualReviewRequired"],
                "createdAt": task["createdAt"],
                "updatedAt": task["updatedAt"],
                "completedAt": task.get("completedAt"),
                "archivedAt": task.get("archivedAt"),
                "lastViewedAt": task.get("lastViewedAt"),
                "assessmentStatus": task.get("assessmentStatus", "pending_verification"),
                "owner": "当前团队",
                "status": "已归档",
                "summary": "包含文字近似、图形近似、绝对理由、跨类驰护、文化禁忌和注册路径建议。",
            }
        )

    return reports

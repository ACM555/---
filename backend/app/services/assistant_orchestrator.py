from __future__ import annotations

import re
from collections.abc import AsyncIterator
from typing import Any

from app.models.assistant import AssistantChatRequest, AssistantChatResponse
from app.services.bailian_client import ModelClient
from app.services.rag_retrieval_service import RetrievalService
from app.services.assistant_session_memory import AssistantSessionMemory


class AssistantOrchestrator:
    def __init__(self) -> None:
        self._retrieval = RetrievalService()
        self._model = ModelClient()
        self._memory = AssistantSessionMemory()

    def _messages(self, request: AssistantChatRequest, user_id: str) -> tuple[list[dict[str, Any]], list[str], list]:
        retrieved = self._retrieval.retrieve_legal(request.question)
        context = "\n\n".join(f"[{item.source.id}] {item.source.title}\n{item.content}" for item in retrieved)
        system = (
            "你是东盟跨境商事法律 AI 助手，服务于中国企业出海。"
            "仅基于提供的已审核资料回答；资料不足时明确写“需人工复核”，并说明需要补充的事实。"
            "不得编造法条、持股比例、许可豁免、审批期限、执行结果或律师意见。"
            "A 级资料可以在适用前提下说明其有限事实；B 级资料只能说明官方来源或办理入口，不能输出实质法律结论。"
            "回答使用中文，逐项引用 [资料ID]，并提醒这不是律师法律意见书。"
            f"\n\n当前页面：{request.page or '未指定'}\n\n可用资料：\n{context}"
        )
        user_content: list[dict[str, Any]] = [{"type": "text", "text": request.question}]
        if request.image_data_url:
            user_content.append({"type": "image_url", "image_url": {"url": request.image_data_url}})
        return [{"role": "system", "content": system}, {"role": "user", "content": user_content}], self._actions_for_page(request.page), retrieved

    @staticmethod
    def _safety_assessment(question: str) -> tuple[str, list[str], list[str]] | None:
        """Return a deterministic downgrade before the model can make a legal conclusion."""
        country = RetrievalService._detect_country(question)
        module = RetrievalService._detect_module(question)
        if country is None:
            if any(name in question.lower() for name in ("越南", "泰国", "新加坡", "vietnam", "thailand", "singapore")):
                return ("human_review_required", ["问题同时涉及多个国家，不能混用任何一国资料。"], ["拆分后的目标国家", "每个国家对应的交易事实"])
            return ("clarification_needed", ["未明确单一目标国家，不能检索或套用国家法律资料。"], ["目标国家"])
        if module is None:
            return ("clarification_needed", ["未识别对应的 M1–M6 业务模块。"], ["业务模块", "项目或交易类型"])
        policy_rules: tuple[tuple[tuple[str, ...], str, list[str]], ...] = (
            (("保证", "一定", "必然", "成功率", "胜诉", "回款"), "不得保证许可、登记、胜诉、执行或回款结果。", ["业务事实", "主管机关或争议程序进展"]),
            (("违法", "合法吗", "合规吗", "是否合法"), "不能在事实不完整时作确定违法或合规结论。", ["完整交易事实", "适用版本与例外条件"]),
            (("冲突", "不一致"), "资料或事实存在冲突，不能择一得出法律结论。", ["冲突资料原文", "事实差异"]),
            (("最新", "现行", "过期", "版本"), "需核验资料版本、修订状态和最近核验时间。", ["法规或权威资料的现行版本"]),
            (("不满足", "不符合", "豁免"), "资料适用前提尚未确认，不能直接套用。", ["资料适用前提", "项目事实"]),
            (("几天", "期限", "持股比例", "罚款", "处罚", "违约金", "时效"), "当前资料不得用于补全高风险具体数值或期限。", ["原文章节", "程序类型", "最新版本"]),
        )
        normalized = re.sub(r"\s+", "", question.lower())
        for keywords, reason, facts in policy_rules:
            if any(keyword in normalized for keyword in keywords):
                return ("human_review_required", [reason], facts)
        return None

    def _safe_response(
        self,
        request: AssistantChatRequest,
        user_id: str,
        status: str,
        reasons: list[str],
        facts: list[str],
        retrieved: list,
    ) -> AssistantChatResponse:
        sources = [item.source for item in retrieved]
        country_code = sources[0].country_code if sources else None
        legal_module = sources[0].legal_module if sources else None
        response = AssistantChatResponse(
            answer="当前问题需人工复核或补充信息后再处理；系统不会据此作出确定性法律结论。",
            answer_status=status,
            sources=sources,
            scope_and_preconditions=[],
            facts_to_confirm=facts,
            suggested_actions=["补充所列事实", "核对权威资料原文与现行版本", "必要时咨询当地专业人士"],
            human_review_reasons=reasons,
            disclaimer="本内容不构成律师法律意见、主管机关决定或结果保证。",
        )
        self._memory.record_audit(
            user_id, request.session_id, request.question, country_code, legal_module,
            [source.id for source in sources], response.answer_status, reasons,
        )
        return response

    async def answer(self, request: AssistantChatRequest, user_id: str) -> AssistantChatResponse:
        messages, actions, retrieved = self._messages(request, user_id)
        assessment = self._safety_assessment(request.question)
        if assessment is not None:
            return self._safe_response(request, user_id, *assessment, retrieved)
        if not retrieved:
            return self._safe_response(
                request, user_id, "human_review_required",
                ["当前没有与该国家和问题匹配的已审核法律资料。"],
                ["项目或交易类型", "关键事实", "可核验的权威资料"],
                [],
            )
        sources = [item.source for item in retrieved]
        country_code = sources[0].country_code
        legal_module = sources[0].legal_module
        preconditions = [item.content.split("适用前提：", 1)[1].split("\n", 1)[0] for item in retrieved if "适用前提：" in item.content]
        reasons = ["资料仅支持有限事实；具体版本、适用前提和业务事实须人工复核。"]
        response = AssistantChatResponse(
            answer=await self._model.complete(messages),
            answer_status="source_backed",
            sources=sources,
            scope_and_preconditions=preconditions,
            facts_to_confirm=["资料版本与生效状态", "业务事实是否满足资料适用前提"],
            suggested_actions=actions,
            human_review_reasons=reasons,
            disclaimer="本内容仅基于已审核资料作初步参考，不构成律师法律意见、主管机关决定或结果保证。",
        )
        self._memory.record_audit(user_id, request.session_id, request.question, country_code, legal_module, [source.id for source in sources], response.answer_status, reasons)
        return response

    async def stream(self, request: AssistantChatRequest, user_id: str) -> AsyncIterator[str]:
        messages, _, retrieved = self._messages(request, user_id)
        assessment = self._safety_assessment(request.question)
        if assessment is not None:
            _, reasons, facts = assessment
            yield f"当前问题需人工复核：{'；'.join(reasons)}。请补充：{'；'.join(facts)}。"
            return
        if not retrieved:
            yield "当前没有与该国家和问题匹配的已审核法律资料，需人工复核。"
            return
        async for delta in self._model.stream(messages):
            yield delta

    def store_text_document(self, user_id: str, filename: str, content: str) -> str:
        return self._retrieval.store_text_document(user_id, filename, content)

    @staticmethod
    def _actions_for_page(page: str) -> list[str]:
        mappings = {
            "/assets": ["补充品牌资产", "前往智能审查"],
            "/submit": ["检查提交材料", "查看规则库"],
            "/reviewing": ["查看审查进度", "查看报告中心"],
            "/reports": ["查看审查报告", "前往规则库"],
        }
        return mappings.get(page, ["新建智能审查", "查看品牌资产", "浏览规则库"])

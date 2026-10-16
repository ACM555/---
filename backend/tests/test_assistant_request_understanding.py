import asyncio

import pytest

from app.core.config import settings
from app.database import init_database
from app.models.assistant import AssistantChatRequest
from app.services.assistant_orchestrator import AssistantOrchestrator
from app.services.legal_repository import LegalRepository
from app.services.legal_seed import seed_legal_sources
from app.services.rag_retrieval_service import RetrievalService


class RecordingModel:
    def __init__(self):
        self.messages = []

    async def complete(self, messages):
        self.messages.append(messages)
        return "仅根据已审核资料列出待核验事项。"

    async def stream(self, messages):
        self.messages.append(messages)
        yield "仅根据已审核资料列出待核验事项。"


@pytest.fixture
def orchestrator(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATABASE_PATH", str(tmp_path / "requests.sqlite3"))
    monkeypatch.setattr(settings, "ASSISTANT_KNOWLEDGE_DIR", str(tmp_path / "knowledge"))
    init_database()
    seed_legal_sources()
    repository = LegalRepository()
    for source_id in (
        "sg-m5-ip-legislation-2026",
        "vn-m2-commercial-law-index-2026",
        "vn-m3-import-procedure-2026",
        "th-m4-labour-protection-2026",
        "th-m6-arbitration-act-2026",
    ):
        repository.set_approval_status(source_id, "approved")
    service = AssistantOrchestrator()
    service._model = RecordingModel()
    return service


@pytest.mark.parametrize(("question", "module"), [
    ("我们公司想在新加坡申请商标，需要准备什么材料？", "M5"),
    ("我公司出口设备到越南，报关需要哪些资料？", "M3"),
    ("我公司和越南客户的合同要核验什么？", "M2"),
    ("泰国劳动合同需要准备什么材料？", "M4"),
    ("我们公司在泰国的合同发生争议，怎么申请仲裁？", "M6"),
    ("在泰国设立公司需要准备哪些材料？", "M1"),
    ("M5模块：新加坡商标申请", "M5"),
    ("m3模块：越南进口报关", "M3"),
    ("比较 M2模块和 M6模块的适用范围", None),
    ("新加坡商标和劳动用工分别需要什么材料？", None),
])
def test_module_detection_reads_business_request_instead_of_company_background(question, module):
    assert RetrievalService._detect_module(question) == module


def test_company_question_retrieves_the_requested_module(orchestrator):
    request = AssistantChatRequest(question="我们公司想在新加坡申请商标，需要准备什么材料？")
    response = asyncio.run(orchestrator.answer(request, "owner"))
    assert response.answer_status == "source_backed"
    assert response.sources
    assert all(source.country_code == "SG" and source.legal_module == "M5" for source in response.sources)
    assert request.question in str(orchestrator._model.messages[-1])


def test_follow_up_uses_the_same_user_session_scope(orchestrator):
    initial = AssistantChatRequest(question="新加坡商标申请要核验什么？", session_id="followup-session")
    asyncio.run(orchestrator.answer(initial, "owner"))
    follow_up = initial.model_copy(update={"question": "那需要准备哪些材料？"})
    response = asyncio.run(orchestrator.answer(follow_up, "owner"))
    assert response.answer_status == "source_backed"
    assert all(source.country_code == "SG" and source.legal_module == "M5" for source in response.sources)
    assert "那需要准备哪些材料？" in str(orchestrator._model.messages[-1])
    assert asyncio.run(orchestrator.answer(follow_up, "another-user")).answer_status == "clarification_needed"
    other_session = follow_up.model_copy(update={"session_id": "another-session"})
    assert asyncio.run(orchestrator.answer(other_session, "owner")).answer_status == "clarification_needed"


def test_new_country_without_a_follow_up_does_not_inherit_old_module(orchestrator):
    initial = AssistantChatRequest(question="新加坡商标申请要核验什么？", session_id="changed-country")
    asyncio.run(orchestrator.answer(initial, "owner"))
    changed = initial.model_copy(update={"question": "越南出海要注意什么？"})
    response = asyncio.run(orchestrator.answer(changed, "owner"))
    assert response.answer_status == "clarification_needed"
    assert response.sources == []


def test_multi_country_or_module_question_never_inherits_a_single_scope(orchestrator):
    initial = AssistantChatRequest(question="新加坡商标申请要核验什么？", session_id="ambiguous-scope")
    asyncio.run(orchestrator.answer(initial, "owner"))
    for question in ("那马来西亚和印尼的商标呢？", "那 M2模块和 M6模块呢？", "那需要哪些材料？"):
        response = asyncio.run(orchestrator.answer(initial.model_copy(update={"question": question}), "owner"))
        assert response.answer_status in {"clarification_needed", "human_review_required"}
        assert response.sources == []
    assert len(orchestrator._model.messages) == 1


def test_streaming_follow_up_uses_the_same_scope(orchestrator):
    async def conversation():
        request = AssistantChatRequest(question="泰国劳动用工需要核验什么？", session_id="streaming-scope")
        first = [part async for part in orchestrator.stream(request, "owner")]
        follow_up = request.model_copy(update={"question": "那劳动合同需要哪些材料？"})
        second = [part async for part in orchestrator.stream(follow_up, "owner")]
        return first, second

    first, second = asyncio.run(conversation())
    assert first == second == ["仅根据已审核资料列出待核验事项。"]
    assert len(orchestrator._model.messages) == 2


def test_chinese_user_documents_reach_the_model_without_becoming_legal_evidence(orchestrator):
    retrieval = orchestrator._retrieval
    retrieval.store_text_document("owner", "application.md", "商标申请材料包括青竹项目的图样文件和商品清单。")
    retrieval.store_text_document("another-user", "private.md", "商标申请材料包括绝不能泄露的其他用户资料。")
    request = AssistantChatRequest(question="我们公司在新加坡申请商标，需要核对哪些申请材料？")
    response = asyncio.run(orchestrator.answer(request, "owner"))
    messages = str(orchestrator._model.messages[-1])
    assert "青竹项目" in messages
    assert "尚未审核" in messages
    assert "绝不能泄露" not in messages
    assert all(not source.id.startswith("tenant-") for source in response.sources)


def test_uploads_cannot_bypass_missing_approved_legal_sources(orchestrator):
    orchestrator._retrieval.store_text_document("owner", "unapproved.md", "越南商标申请肯定可以成功。")
    request = AssistantChatRequest(question="越南商标申请需要核验什么？")
    response = asyncio.run(orchestrator.answer(request, "owner"))
    assert response.answer_status == "human_review_required"
    assert response.sources == []
    assert orchestrator._model.messages == []
    assert "目标国家：越南（VN）" in response.answer
    assert "业务模块：M5" in response.answer


def test_plain_chinese_user_query_matches_document_fragments(orchestrator):
    retrieval = orchestrator._retrieval
    retrieval.store_text_document("owner", "application.md", "商标申请材料包括青竹项目的图样文件和商品清单。")
    documents = retrieval.retrieve_user_context("商标申请需要准备什么材料", "owner")
    assert len(documents) == 1
    assert "青竹项目" in documents[0].content
    assert retrieval.retrieve_user_context("商标申请需要准备什么材料", "another-user") == []


def test_two_turn_clarification_converges_instead_of_looping(orchestrator):
    """系统追问「补目标国家」后用户只回「新加坡」，必须继承已识别的 M5，而不是反过来再要模块。"""
    first = AssistantChatRequest(question="商标出海要注意什么？", session_id="slot-filling")
    first_reply = asyncio.run(orchestrator.answer(first, "owner"))
    assert first_reply.answer_status == "clarification_needed"
    assert "业务模块：M5" in first_reply.answer

    second = asyncio.run(orchestrator.answer(first.model_copy(update={"question": "新加坡"}), "owner"))
    assert second.answer_status == "source_backed"
    assert second.sources
    assert all(source.country_code == "SG" and source.legal_module == "M5" for source in second.sources)
    # 模型必须拿到原来的完整问题，而不是只看到「新加坡」两个字。
    assert "商标出海要注意什么" in str(orchestrator._model.messages[-1])
    assert "新加坡" in str(orchestrator._model.messages[-1])


def test_two_turn_clarification_converges_when_the_module_is_filled_last(orchestrator):
    first = AssistantChatRequest(question="新加坡出海要注意什么？", session_id="slot-filling-reverse")
    assert asyncio.run(orchestrator.answer(first, "owner")).answer_status == "clarification_needed"
    second = asyncio.run(orchestrator.answer(first.model_copy(update={"question": "M5"}), "owner"))
    assert second.answer_status == "source_backed"
    assert all(source.country_code == "SG" and source.legal_module == "M5" for source in second.sources)


@pytest.mark.parametrize("answer", ["新加坡", "选新加坡", "目标国家：新加坡", "新加坡吧"])
def test_various_slot_answer_phrasings_all_inherit(orchestrator, answer):
    first = AssistantChatRequest(question="商标出海要注意什么？", session_id="slot-" + answer)
    asyncio.run(orchestrator.answer(first, "owner"))
    reply = asyncio.run(orchestrator.answer(first.model_copy(update={"question": answer}), "owner"))
    assert reply.answer_status == "source_backed"
    assert all(source.country_code == "SG" for source in reply.sources)


def test_a_short_but_substantive_new_question_does_not_inherit(orchestrator):
    """「越南公司」是新话题（公司设立），不是「只补国家」，不能继承上一轮的 M5。"""
    initial = AssistantChatRequest(question="新加坡商标申请要核验什么？", session_id="short-new-topic")
    asyncio.run(orchestrator.answer(initial, "owner"))
    response = asyncio.run(orchestrator.answer(initial.model_copy(update={"question": "越南公司"}), "owner"))
    assert response.answer_status == "clarification_needed"
    assert response.sources == []


def test_multi_country_assessment_is_not_limited_to_three_countries():
    status, reasons, _facts = AssistantOrchestrator._safety_assessment("马来西亚和印尼的商标申请有什么区别？")
    assert status == "human_review_required"
    assert "多个国家" in "".join(reasons)


@pytest.mark.parametrize("question", [
    "你是谁？", "你是谁", "你好", "您好！", "你能做什么？", "这有什么功能",
    "这个系统怎么用？", "如何操作本系统？", "什么是M1到M6？", "M5模块是什么意思", "谢谢", "好的",
])
def test_guide_questions_are_answered_without_the_legal_gate_or_the_model(orchestrator, question):
    """身份/问候/能力/用法/模块说明类问题不是法律问题，不该被「补目标国家」拦住。"""
    response = asyncio.run(orchestrator.answer(AssistantChatRequest(question=question), "owner"))
    assert response.answer_status == "guidance"
    assert response.sources == []
    assert response.facts_to_confirm == []
    assert response.human_review_reasons == []
    assert "未明确单一目标国家" not in response.answer
    # 引导回答是固定文案，不经过模型，因此没有法律结论也没有幻觉空间。
    assert orchestrator._model.messages == []


@pytest.mark.parametrize("question", [
    "你好，我们公司想在新加坡申请商标，需要准备什么材料？",
    "谢谢，那越南商标注册要核验什么？",
    "M5模块：新加坡商标申请",
])
def test_greeting_or_module_prefix_does_not_hijack_a_legal_question(orchestrator, question):
    """规则是整句锚定的：问候语后面还跟着真实法律问题时，必须继续走法律链路。"""
    response = asyncio.run(orchestrator.answer(AssistantChatRequest(question=question), "owner"))
    assert response.answer_status != "guidance"


def test_guide_question_does_not_erase_the_session_scope(orchestrator):
    initial = AssistantChatRequest(question="新加坡商标申请要核验什么？", session_id="guide-keeps-scope")
    asyncio.run(orchestrator.answer(initial, "owner"))
    asyncio.run(orchestrator.answer(initial.model_copy(update={"question": "你好"}), "owner"))
    follow_up = asyncio.run(orchestrator.answer(initial.model_copy(update={"question": "那需要准备哪些材料？"}), "owner"))
    assert follow_up.answer_status == "source_backed"
    assert all(source.country_code == "SG" for source in follow_up.sources)


@pytest.mark.parametrize("question", [
    "现在是几点钟？", "今天天气怎么样？", "帮我写一首诗", "1+1 等于几", "你会做饭吗",
])
def test_non_compliance_questions_are_not_asked_to_supply_a_country(orchestrator, question):
    """国家门槛只对合规问题成立：闲聊/常识问题回「未明确单一目标国家」是错的。"""
    response = asyncio.run(orchestrator.answer(AssistantChatRequest(question=question), "owner"))
    assert response.answer_status == "out_of_scope"
    assert response.sources == []
    assert response.human_review_reasons == []
    assert "未明确单一目标国家" not in response.answer
    assert "不在我的处理范围" in response.answer
    # 不是法律问题，因此不调模型，也不产生任何法律结论。
    assert orchestrator._model.messages == []


@pytest.mark.parametrize("question", [
    "商标注册需要什么材料？", "出口报关要准备什么？", "劳动合同要注意什么？",
    "这个项目需要审批吗？", "需要准备哪些材料？",
])
def test_compliance_questions_without_a_country_still_ask_for_the_country(orchestrator, question):
    """合规问题缺国家时仍要追问国家——不能因为加了范围判断就放松这道闸门。"""
    response = asyncio.run(orchestrator.answer(AssistantChatRequest(question=question), "owner"))
    assert response.answer_status == "clarification_needed"
    assert response.sources == []
    assert "未明确单一目标国家" in response.answer
    assert orchestrator._model.messages == []


@pytest.mark.parametrize(("question", "alias"), [
    ("阿联酋商标怎么注册？", "阿联酋"),
    ("美国商标申请需要什么材料？", "美国"),
    ("Japan trademark filing requirements", "japan"),
])
def test_out_of_scope_jurisdiction_is_named_instead_of_asking_for_a_country(question, alias):
    """用户已经指明了国家，只是不在覆盖范围；不能回「未明确单一目标国家」。"""
    status, reasons, facts = AssistantOrchestrator._safety_assessment(question)
    assert status == "clarification_needed"
    joined = "".join(reasons)
    assert alias in joined
    assert "不在当前覆盖的东盟国家范围内" in joined
    assert "未明确单一目标国家" not in joined
    assert "越南" in "".join(facts)


@pytest.mark.parametrize("question", ["印度尼西亚商标怎么注册？", "越南商标怎么注册？"])
def test_covered_countries_are_not_mistaken_for_out_of_scope_ones(question):
    """"印度尼西亚" 不是「印度」，覆盖国仍走正常链路。"""
    assert AssistantOrchestrator._detect_out_of_scope(question) is None
    assert AssistantOrchestrator._safety_assessment(question) is None

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


def test_multi_country_assessment_is_not_limited_to_three_countries():
    status, reasons, _facts = AssistantOrchestrator._safety_assessment("马来西亚和印尼的商标申请有什么区别？")
    assert status == "human_review_required"
    assert "多个国家" in "".join(reasons)

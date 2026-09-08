import asyncio
import unittest

from app.database import init_database
from app.models.assistant import AssistantChatRequest
from app.services.assistant_orchestrator import AssistantOrchestrator
from app.services.legal_seed import seed_legal_sources


class RecordingModel:
    def __init__(self) -> None:
        self.calls = 0

    async def complete(self, _messages: object) -> str:
        self.calls += 1
        return "仅基于已审核资料作初步参考。"


class P2EndToEndTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        init_database()
        seed_legal_sources()

    def setUp(self) -> None:
        self.model = RecordingModel()
        self.orchestrator = AssistantOrchestrator()
        self.orchestrator._model = self.model

    def test_three_source_backed_cases_include_traceable_passages(self) -> None:
        cases = (
            "越南买卖合同的违约风险需要核验什么？",
            "泰国工程人员的工作许可和劳动用工需要核验什么？",
            "新加坡商标和技术保护应核验哪些事项？",
        )
        for index, question in enumerate(cases):
            with self.subTest(question=question):
                response = asyncio.run(self.orchestrator.answer(AssistantChatRequest(question=question, session_id=f"p2-source-{index}"), "p2-e2e"))
                self.assertEqual(response.answer_status, "source_backed")
                self.assertTrue(response.sources)
                self.assertTrue(all(source.source_url and source.verified_at and source.passages for source in response.sources))
                self.assertTrue(response.disclaimer)
        self.assertEqual(self.model.calls, 3)

    def test_three_downgrade_cases_do_not_call_model(self) -> None:
        cases = (
            "向东盟出口设备应如何处理？",
            "越南和泰国的贸易规则是否相同？",
            "泰国投资许可需要几天？",
        )
        for index, question in enumerate(cases):
            with self.subTest(question=question):
                response = asyncio.run(self.orchestrator.answer(AssistantChatRequest(question=question, session_id=f"p2-safe-{index}"), "p2-e2e"))
                self.assertIn(response.answer_status, {"clarification_needed", "human_review_required"})
                self.assertTrue(response.human_review_reasons)
                self.assertTrue(response.facts_to_confirm)
        self.assertEqual(self.model.calls, 0)


if __name__ == "__main__":
    unittest.main()

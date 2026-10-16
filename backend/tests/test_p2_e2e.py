import asyncio
import tempfile
import unittest
from pathlib import Path

from app.core.config import settings
from app.database import init_database
from app.models.assistant import AssistantChatRequest
from app.services.assistant_orchestrator import AssistantOrchestrator
from app.services.legal_seed import seed_legal_sources
from app.services.legal_repository import LegalRepository


class RecordingModel:
    def __init__(self) -> None:
        self.calls = 0

    async def complete(self, _messages: object) -> str:
        self.calls += 1
        return "仅基于已审核资料作初步参考。"


class P2EndToEndTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.original_database_path = settings.DATABASE_PATH
        cls.temporary_directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        settings.DATABASE_PATH = str(Path(cls.temporary_directory.name) / "p2.sqlite3")
        init_database()
        seed_legal_sources()
        repository = LegalRepository()
        for source_id in (
            "vn-m2-commercial-law-index-2026",
            "th-m4-labour-protection-2026",
            "sg-m5-ip-legislation-2026",
        ):
            repository.set_approval_status(source_id, "approved")

    @classmethod
    def tearDownClass(cls) -> None:
        settings.DATABASE_PATH = cls.original_database_path
        cls.temporary_directory.cleanup()

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

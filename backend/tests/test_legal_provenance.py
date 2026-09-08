import tempfile
import unittest
from datetime import date
from pathlib import Path

from app.core.config import settings
from app.database import init_database
from app.models.legal import LegalPassageCreate, LegalSourceCreate, LegalSourceProvenanceCreate
from app.services.legal_repository import LegalRepository


class LegalProvenanceTest(unittest.TestCase):
    def setUp(self) -> None:
        self._database_path = settings.DATABASE_PATH
        # SQLite WAL handles can remain briefly open on Windows after a
        # connection context exits; test assertions remain isolated either way.
        self._temporary_directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        settings.DATABASE_PATH = str(Path(self._temporary_directory.name) / "legal.sqlite3")
        init_database()
        self.repository = LegalRepository()

    def tearDown(self) -> None:
        settings.DATABASE_PATH = self._database_path
        self._temporary_directory.cleanup()

    def _draft_source(self):
        return self.repository.create_source(
            LegalSourceCreate(
                country_code="SG",
                legal_module="M5",
                evidence_level="B",
                title="测试用官方知识产权入口",
                source_type="主管机关页面",
                source_url="https://example.gov/source",
                source_language="English",
                verified_at=date(2026, 9, 5),
                supported_fact="该测试仅验证来源溯源和审核隔离行为。",
                prerequisites=["仅用于测试"],
                non_inferences=["不构成法律结论"],
                review_triggers=["需要人工审核"],
            )
        )

    def test_new_source_receives_primary_provenance(self) -> None:
        source = self._draft_source()
        self.assertEqual(len(source.provenance), 1)
        self.assertEqual(source.provenance[0].role, "primary")

    def test_conflicting_cross_check_cannot_be_approved(self) -> None:
        source = self._draft_source()
        updated = self.repository.add_provenance(
            source.source_id,
            LegalSourceProvenanceCreate(
                role="cross_check",
                publisher="测试交叉核验机构",
                source_type="官方法规库",
                source_url="https://example.org/cross-check",
                source_language="English",
                checked_at=date(2026, 9, 5),
                conflict_note="版本状态尚待人工处理",
            ),
        )
        self.assertIsNotNone(updated)
        with self.assertRaises(ValueError):
            self.repository.set_approval_status(source.source_id, "approved")

    def test_source_without_approved_clause_excerpt_cannot_be_approved(self) -> None:
        source = self._draft_source()
        self.repository.add_provenance(
            source.source_id,
            LegalSourceProvenanceCreate(
                role="cross_check",
                publisher="测试交叉核验机构",
                source_type="官方法规库",
                source_url="https://example.org/cross-check",
                source_language="English",
                checked_at=date(2026, 9, 5),
            ),
        )
        with self.assertRaisesRegex(ValueError, "条款/章节"):
            self.repository.set_approval_status(source.source_id, "approved")

    def test_source_approval_confirms_collected_draft_excerpt_in_one_action(self) -> None:
        source = self._draft_source()
        self.repository.add_provenance(
            source.source_id,
            LegalSourceProvenanceCreate(
                role="cross_check",
                publisher="测试交叉核验机构",
                source_type="官方法规库",
                source_url="https://example.org/cross-check",
                source_language="English",
                checked_at=date(2026, 9, 5),
            ),
        )
        passage = self.repository.create_passage(
            LegalPassageCreate(
                source_id=source.source_id,
                locator="Section 1",
                original_text="A controlled test excerpt.",
                chinese_text="受控测试摘录。",
                prerequisites=["仅用于测试"],
                non_inferences=["不构成法律结论"],
            )
        )
        self.assertIsNotNone(passage)
        approved = self.repository.set_approval_status(source.source_id, "approved")
        self.assertEqual(approved.approval_status, "approved")
        passages = self.repository.list_passages(source.source_id)
        self.assertEqual(passages[0].approval_status, "approved")


if __name__ == "__main__":
    unittest.main()

"""Coverage and provenance gates for the non-public legal-source candidate pack."""

from __future__ import annotations

import json
import unittest
from pathlib import Path


COUNTRIES = ("BN", "KH", "ID", "LA", "MY", "MM", "PH", "SG", "TH", "TL", "VN")
MODULES = tuple(f"M{number}" for number in range(1, 7))
SEED_PATH = Path(__file__).resolve().parents[1] / "data" / "legal_sources_candidate_seed.json"
DATA_DIRECTORY = Path(__file__).resolve().parents[1] / "data"


class CandidateCoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.items = json.loads(SEED_PATH.read_text(encoding="utf-8"))
        cls.passages = []
        for passage_path in sorted(DATA_DIRECTORY.glob("legal_passages*_seed.json")):
            cls.passages.extend(json.loads(passage_path.read_text(encoding="utf-8")))

    def test_every_candidate_has_a_primary_and_cross_check_source(self) -> None:
        for item in self.items:
            with self.subTest(source_id=item["source_id"]):
                self.assertTrue(item["source_url"].startswith("https://"))
                self.assertTrue(item["primary_publisher"].strip())
                self.assertEqual(len(item["cross_checks"]), 1)
                self.assertTrue(item["cross_checks"][0]["source_url"].startswith("https://"))
                self.assertTrue(item["cross_checks"][0]["publisher"].strip())

    def test_candidate_pack_covers_all_unapproved_country_module_slots(self) -> None:
        """VN M1/M4/M6 are legacy approved records; all other 63 slots need candidates."""
        pairs = {(item["country_code"], item["legal_module"]) for item in self.items}
        legacy_approved = {("VN", "M1"), ("VN", "M4"), ("VN", "M6")}
        expected = {(country, module) for country in COUNTRIES for module in MODULES}
        self.assertTrue(expected - legacy_approved <= pairs)

    def test_singapore_first_batch_passages_are_traceable_drafts(self) -> None:
        source_ids = {item["source_id"] for item in self.items}
        passage_pairs = {(item["source_id"], item["passage_key"]) for item in self.passages}
        expected_sources = {
            "sg-m1-companies-act-2026",
            "sg-m2-sale-goods-act-2026",
            "sg-m3-import-export-act-2026",
            "sg-m4-foreign-manpower-act-2026",
            "sg-m5-ip-legislation-2026",
            "sg-m6-international-arbitration-act-2026",
        }
        self.assertTrue(expected_sources <= {source_id for source_id, _ in passage_pairs})
        for passage in self.passages:
            with self.subTest(source_id=passage["source_id"]):
                self.assertIn(passage["source_id"], source_ids)
                self.assertTrue(passage["locator"].strip())
                self.assertTrue(passage["original_text"].strip())
                self.assertTrue(passage["prerequisites"])
                self.assertTrue(passage["non_inferences"])


if __name__ == "__main__":
    unittest.main()

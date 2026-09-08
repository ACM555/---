import unittest

from app.services.rag_retrieval_service import RetrievalService


class CountryDetectionTests(unittest.TestCase):
    def test_recognises_all_eleven_supported_countries(self) -> None:
        cases = {
            "文莱公司设立": "BN", "柬埔寨合同审查": "KH", "印尼贸易合规": "ID",
            "老挝劳动用工": "LA", "马来西亚商标": "MY", "缅甸仲裁": "MM",
            "菲律宾公司设立": "PH", "新加坡知识产权": "SG", "泰国投资": "TH",
            "东帝汶海关": "TL", "越南合同": "VN",
        }
        for question, expected in cases.items():
            with self.subTest(question=question):
                self.assertEqual(RetrievalService._detect_country(question), expected)

    def test_multiple_countries_require_manual_review(self) -> None:
        self.assertIsNone(RetrievalService._detect_country("越南和泰国的合同是否相同"))


if __name__ == "__main__":
    unittest.main()

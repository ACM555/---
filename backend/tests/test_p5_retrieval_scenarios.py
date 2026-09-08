import unittest

from app.database import init_database
from app.services.rag_retrieval_service import RetrievalService
from app.services.legal_seed import seed_legal_sources


class P5RetrievalScenarioTests(unittest.TestCase):
    def setUp(self) -> None:
        init_database()
        seed_legal_sources()
        self.service = RetrievalService()

    def test_trade_contract_and_transport_are_country_module_isolated(self) -> None:
        contract = self.service.retrieve_legal("越南买卖合同的违约风险需要核验什么？")
        transport = self.service.retrieve_legal("越南出口设备的报关和运输资料需要核验什么？")
        self.assertTrue(contract)
        self.assertTrue(transport)
        self.assertTrue(all(item.source.country_code == "VN" and item.source.legal_module == "M2" for item in contract))
        self.assertTrue(all(item.source.country_code == "VN" and item.source.legal_module == "M3" for item in transport))

    def test_engineering_investment_modules_are_isolated(self) -> None:
        cases = {"M1": "泰国工业厂房项目的外商投资准入需要核验什么？", "M4": "泰国工程人员的工作许可和劳动用工需要核验什么？", "M6": "泰国项目发生仲裁争议时需要准备什么？"}
        for legal_module, question in cases.items():
            with self.subTest(legal_module=legal_module):
                rows = self.service.retrieve_legal(question)
                self.assertTrue(rows)
                self.assertTrue(all(item.source.country_code == "TH" and item.source.legal_module == legal_module for item in rows))

    def test_ip_and_safety_degradation(self) -> None:
        ip_rows = self.service.retrieve_legal("新加坡商标和技术保护应核验什么？")
        self.assertTrue(ip_rows)
        self.assertTrue(all(item.source.country_code == "SG" and item.source.legal_module == "M5" for item in ip_rows))
        self.assertEqual(self.service.retrieve_legal("向东盟出口设备如何处理？"), [])
        self.assertEqual(self.service.retrieve_legal("越南和泰国的贸易规则是否相同？"), [])


if __name__ == "__main__":
    unittest.main()

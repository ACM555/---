import unittest

from app.services.assistant_orchestrator import AssistantOrchestrator


class P2SafetyPolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assess = AssistantOrchestrator._safety_assessment

    def test_twelve_downgrade_rules(self) -> None:
        cases = {
            "未明确国家": "出口设备的报关需要注意什么？",
            "多国不可混用": "越南和泰国的合同规则是否相同？",
            "未明确模块": "新加坡出海要注意什么？",
            "保证结果": "越南商标一定能注册成功吗？",
            "确定性合法判断": "泰国投资这样做违法吗？",
            "来源冲突": "新加坡商标资料冲突时该信哪一个？",
            "版本核验": "越南劳动法最新版本是什么？",
            "适用前提": "菲律宾劳动用工不满足条件能豁免吗？",
            "高风险期限": "泰国投资许可需要几天？",
            "高风险比例": "马来西亚投资持股比例是多少？",
            "高风险处罚": "印尼进口违规罚款多少？",
            "高风险争议时效": "缅甸货款追偿时效多久？",
        }
        for name, question in cases.items():
            with self.subTest(name=name):
                outcome = self.assess(question)
                self.assertIsNotNone(outcome)
                self.assertIn(outcome[0], {"clarification_needed", "human_review_required"})

    def test_single_country_module_with_no_high_risk_request_can_continue(self) -> None:
        self.assertIsNone(self.assess("新加坡商标和技术保护应核验哪些事项？"))


if __name__ == "__main__":
    unittest.main()

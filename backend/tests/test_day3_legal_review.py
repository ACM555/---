import base64
import json
import unittest
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from app.services.audit_engine import run_audit


ROOT = Path(__file__).resolve().parent
SAMPLES_PATH = ROOT / "day3_samples.json"


def make_logo_base64(kind: str = "plain") -> str:
    image = np.full((160, 160, 3), 255, dtype=np.uint8)
    if kind == "visual":
        cv2.circle(image, (80, 80), 46, (0, 0, 0), thickness=6)
        cv2.line(image, (80, 34), (80, 126), (0, 0, 0), thickness=4)
        cv2.line(image, (34, 80), (126, 80), (0, 0, 0), thickness=4)
    else:
        cv2.rectangle(image, (48, 48), (112, 112), (40, 120, 220), thickness=-1)

    ok, buffer = cv2.imencode(".png", image)
    assert ok
    return base64.b64encode(buffer.tobytes()).decode("ascii")


def request_for_case(case_id: str) -> dict[str, str]:
    plain_logo = make_logo_base64()
    visual_logo = make_logo_base64("visual")
    cases = {
        "D3-001": {
            "brandName": "茉莉奶白",
            "englishName": "",
            "niceClass": "第43类-餐饮服务",
            "goodsServices": "新茶饮品牌，主营奶茶饮品，目标市场越南",
            "logo": plain_logo,
        },
        "D3-002": {
            "brandName": "Molan Tea",
            "englishName": "Molan Tea",
            "niceClass": "",
            "goodsServices": "新茶饮品牌，主营奶茶饮品，目标市场越南",
            "logo": plain_logo,
        },
        "D3-003": {
            "brandName": "星巴克",
            "englishName": "Starbucks",
            "niceClass": "第43类-餐饮服务",
            "goodsServices": "咖啡、茶饮、餐饮服务",
            "logo": plain_logo,
        },
        "D3-004": {
            "brandName": "Starbuk",
            "englishName": "Starbuk",
            "niceClass": "第43类-餐饮服务",
            "goodsServices": "含四叶花卉图形的新茶饮品牌，目标市场越南",
            "logo": visual_logo,
        },
        "D3-005": {
            "brandName": "Social Coffee Roasteri",
            "englishName": "Social Coffee Roasteri",
            "niceClass": "第43类-餐饮服务",
            "goodsServices": "咖啡、茶饮或餐饮服务",
            "logo": plain_logo,
        },
        "D3-006": {
            "brandName": "Louis Vuiton",
            "englishName": "Louis Vuiton",
            "niceClass": "第43类-餐饮服务",
            "goodsServices": "茶饮品牌，请判断是否享有全类别保护和注册成功率",
            "logo": plain_logo,
        },
        "D3-007": {
            "brandName": "Molan Garden",
            "englishName": "Molan Garden",
            "niceClass": "第35类-广告销售",
            "goodsServices": "面向越南市场的原创生活方式品牌零售服务",
            "logo": plain_logo,
        },
        "D3-008": {
            "brandName": "Molan",
            "englishName": "Molan",
            "niceClass": "第43类-餐饮服务",
            "goodsServices": "请告诉我这个商标的注册成功率",
            "logo": plain_logo,
        },
    }
    return cases[case_id]


def flatten_result_text(result: dict[str, Any]) -> str:
    parts: list[str] = [
        str(result.get("overallResult", "")),
        str(result.get("documentPreview", "")),
    ]
    for key in ("hitRules", "references", "suggestions"):
        for item in result.get(key, []):
            parts.extend(str(value) for value in item.values())
    return "\n".join(parts)


def actual_rule_ids(result: dict[str, Any]) -> set[str]:
    return {
        str(rule.get("ruleId"))
        for rule in result.get("hitRules", [])
        if rule.get("applicable") and rule.get("ruleId")
    }


class Day3LegalReviewTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.samples = json.loads(SAMPLES_PATH.read_text(encoding="utf-8"))["test_cases"]

    def test_day3_required_and_forbidden_wording(self):
        for sample in self.samples:
            with self.subTest(sample["case_id"]):
                result = run_audit(request_for_case(sample["case_id"]))
                full_text = flatten_result_text(result)

                self.assertIn(sample["required_wording"], full_text)
                self.assertNotIn(sample["forbidden_wording"], full_text)
                self.assertEqual(result["manualReviewRequired"], sample["manual_review_required"])

    def test_day3_expected_rule_ids(self):
        for sample in self.samples:
            expected = set(sample["expected_rule_ids"])
            if not expected:
                continue

            with self.subTest(sample["case_id"]):
                result = run_audit(request_for_case(sample["case_id"]))
                self.assertTrue(
                    expected.issubset(actual_rule_ids(result)),
                    f"expected {expected}, got {actual_rule_ids(result)}",
                )

    def test_day3_expected_risk_semantics(self):
        for sample in self.samples:
            with self.subTest(sample["case_id"]):
                result = run_audit(request_for_case(sample["case_id"]))
                expected_risk = sample["expected_overall_risk"]

                if expected_risk == "review":
                    self.assertTrue(result["manualReviewRequired"])
                    self.assertIn(result["riskLevel"], {"medium", "high"})
                else:
                    self.assertEqual(result["riskLevel"], expected_risk)


if __name__ == "__main__":
    unittest.main()

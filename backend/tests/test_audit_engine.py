import base64
import unittest

import cv2
import numpy as np

from app.services.audit_engine import run_audit


def make_plain_logo_base64() -> str:
    image = np.full((32, 32, 3), 255, dtype=np.uint8)
    cv2.rectangle(image, (8, 8), (24, 24), (40, 120, 220), thickness=-1)
    ok, buffer = cv2.imencode(".png", image)
    assert ok
    return base64.b64encode(buffer.tobytes()).decode("ascii")


class AuditEngineTest(unittest.TestCase):
    def test_pure_han_brand_requires_review(self):
        logo = make_plain_logo_base64()
        result = run_audit(
            {
                "brandName": "茉莉奶白",
                "englishName": "",
                "niceClass": "第43类-餐饮服务",
                "goodsServices": "新茶饮品牌，主营奶茶饮品，目标市场越南",
                "logo": logo,
            }
        )

        self.assertEqual(result["riskLevel"], "medium")
        self.assertTrue(result["manualReviewRequired"])
        self.assertIn("中文", result["hitRules"][0]["note"])
        self.assertNotIn("必然被驳回", result["overallResult"])

    def test_exact_trademark_candidate_is_high_risk_line(self):
        logo = make_plain_logo_base64()
        result = run_audit(
            {
                "brandName": "星巴克",
                "englishName": "Starbucks",
                "niceClass": "第43类-餐饮服务",
                "goodsServices": "咖啡、茶饮、餐饮服务",
                "logo": logo,
            }
        )

        self.assertEqual(result["riskLevel"], "high")
        self.assertGreaterEqual(result["riskScore"], 80)
        self.assertTrue(any("重要冲突线索" in rule["note"] for rule in result["hitRules"]))
        self.assertFalse(any("已经构成侵权" in rule["note"] for rule in result["hitRules"]))
        self.assertIn("# M5 商标与技术出海风险提示清单", result["documentPreview"])
        self.assertIn("风险线索等级**：high", result["documentPreview"])
        self.assertIn("## 使用边界", result["documentPreview"])
        self.assertNotIn("可以提交注册", result["documentPreview"])
        self.assertIn("# 商标注册申请书", result["applicationDocumentPreview"])
        self.assertIn("## Trademark Application Form", result["applicationDocumentPreview"])
        self.assertIn("### Đơn đăng ký nhãn hiệu", result["applicationDocumentPreview"])
        self.assertIn("星巴克", result["applicationDocumentPreview"])
        self.assertIn("# 商标代理委托书", result["powerOfAttorneyPreview"])
        self.assertIn("## Power of Attorney", result["powerOfAttorneyPreview"])
        self.assertIn("### Giấy ủy quyền", result["powerOfAttorneyPreview"])

    def test_complete_unknown_brand_is_low_risk(self):
        logo = make_plain_logo_base64()
        result = run_audit(
            {
                "brandName": "Molan Garden",
                "englishName": "Molan Garden",
                "niceClass": "第35类-广告销售",
                "goodsServices": "面向越南市场的原创生活方式品牌零售服务",
                "logo": logo,
            }
        )

        self.assertEqual(result["riskLevel"], "low")
        self.assertIn("当前有限范围内未命中明显风险", result["overallResult"])
        self.assertNotIn("放心使用", result["overallResult"])
        self.assertIn("风险线索等级**：low", result["documentPreview"])
        self.assertIn("不构成律师法律意见", result["documentPreview"])
        self.assertNotIn("可以提交注册", result["documentPreview"])

    def test_success_rate_request_is_rejected(self):
        logo = make_plain_logo_base64()
        result = run_audit(
            {
                "brandName": "Molan",
                "englishName": "Molan",
                "niceClass": "第43类-餐饮服务",
                "goodsServices": "请告诉我注册成功率",
                "logo": logo,
            }
        )

        self.assertEqual(result["riskLevel"], "medium")
        self.assertTrue(any("不能提供注册成功率" in rule["note"] for rule in result["hitRules"]))
        self.assertFalse(any("预计成功率" in rule["note"] for rule in result["hitRules"]))
        self.assertIn("风险线索等级**：medium", result["documentPreview"])
        self.assertIn("不能判断商标是否可注册", result["documentPreview"])


if __name__ == "__main__":
    unittest.main()

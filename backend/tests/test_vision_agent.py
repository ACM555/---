import base64
import unittest

import cv2
import numpy as np

from app.services.vision_agent import extract_visual_features, run_vision_agent


def make_png_base64(image: np.ndarray) -> str:
    ok, buffer = cv2.imencode(".png", image)
    assert ok
    return base64.b64encode(buffer.tobytes()).decode("ascii")


class VisionAgentTest(unittest.TestCase):
    def test_extract_visual_features_from_opencv_image(self):
        image = np.full((160, 160, 3), 255, dtype=np.uint8)
        cv2.circle(image, (80, 80), 45, (0, 0, 0), thickness=6)
        cv2.line(image, (80, 35), (80, 125), (0, 0, 0), thickness=4)
        cv2.line(image, (35, 80), (125, 80), (0, 0, 0), thickness=4)

        features = extract_visual_features(image)

        self.assertGreater(features.geometry_score, 0)
        self.assertGreater(features.edge_density_score, 0)
        self.assertGreater(features.symmetry_score, 50)
        self.assertGreater(features.center_score, 50)

    def test_run_vision_agent_returns_radar_data(self):
        image = np.full((120, 120, 3), 255, dtype=np.uint8)
        cv2.rectangle(image, (25, 25), (95, 95), (20, 80, 200), thickness=-1)

        result = run_vision_agent(
            {
                "brandName": "Molan",
                "englishName": "Molan",
                "goodsServices": "原创餐饮品牌",
                "logo": make_png_base64(image),
            }
        )

        self.assertEqual(len(result["radarData"]), 5)
        self.assertTrue(all("target" in item for item in result["radarData"]))

    def test_high_risk_visual_terms_raise_review_candidate(self):
        image = np.full((160, 160, 3), 255, dtype=np.uint8)
        cv2.ellipse(image, (80, 80), (35, 55), 0, 0, 360, (0, 0, 0), thickness=5)

        result = run_vision_agent(
            {
                "brandName": "Molan",
                "englishName": "Molan",
                "goodsServices": "含四叶花卉图形的新茶饮品牌",
                "logo": make_png_base64(image),
            }
        )

        self.assertEqual(len(result["hitRules"]), 1)
        self.assertIn("OpenCV", result["hitRules"][0]["note"])
        self.assertEqual(result["hitRules"][0]["similarityType"], "OpenCV视觉相似候选")

    def test_invalid_image_payload_requires_manual_review(self):
        result = run_vision_agent(
            {
                "brandName": "Molan",
                "englishName": "Molan",
                "goodsServices": "原创餐饮品牌",
                "logo": "not-a-valid-image",
            }
        )

        self.assertEqual(len(result["hitRules"]), 1)
        self.assertIn("无法被 OpenCV 解码", result["hitRules"][0]["note"])


if __name__ == "__main__":
    unittest.main()

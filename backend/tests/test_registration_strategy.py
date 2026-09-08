import unittest

from app.services.registration_strategy import build_registration_strategy


class RegistrationStrategyTest(unittest.TestCase):
    def test_single_country_for_two_or_fewer_markets(self):
        result = build_registration_strategy(
            {
                "targetMarkets": ["越南", "泰国"],
                "hasChinaBase": False,
                "niceClass": "第43类-餐饮服务",
                "goodsServices": "新茶饮品牌，主营奶茶饮品",
            }
        )

        self.assertEqual(result["recommendedPath"], "单国申请")
        self.assertIn("不超过 2 国", result["reason"])
        self.assertTrue(result["localizedGoodsServices"])

    def test_madrid_for_three_plus_without_core_markets(self):
        result = build_registration_strategy(
            {
                "targetMarkets": ["新加坡", "菲律宾", "马来西亚"],
                "hasChinaBase": True,
                "niceClass": "第35类-广告销售",
                "goodsServices": "生活方式品牌零售服务",
            }
        )

        self.assertEqual(result["recommendedPath"], "马德里体系")
        self.assertIn("40-60%", result["costSaving"])
        self.assertTrue(any("5年中央打击" in risk for risk in result["risks"]))

    def test_hybrid_for_three_plus_with_core_market(self):
        result = build_registration_strategy(
            {
                "targetMarkets": ["越南", "泰国", "印尼"],
                "hasChinaBase": False,
                "niceClass": "第43类-餐饮服务",
                "goodsServices": "餐饮",
            }
        )

        self.assertEqual(result["recommendedPath"], "单国 + 马德里混合路径")
        self.assertTrue(any("马德里体系" in risk and "中国基础" in risk for risk in result["risks"]))
        self.assertTrue(any(item["market"] == "越南" for item in result["localizedGoodsServices"]))
        self.assertTrue(any("细化" in item["localized"] for item in result["localizedGoodsServices"]))


if __name__ == "__main__":
    unittest.main()

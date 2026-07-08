import unittest

from brand_rules import assign_brands, extract_brand_decision


class BrandRuleTestCase(unittest.TestCase):
    def assert_brand(self, company, product, expected, source=None):
        decision = extract_brand_decision(company, product)
        self.assertEqual(decision.name, expected)
        if source:
            self.assertEqual(decision.source, source)

    def test_approved_positive_examples(self):
        cases = (
            ("友士股份有限公司", "森文無油紫蘇梅風味沙拉醬150ML", "森文"),
            ("友士股份有限公司", "森文秘藏豬排沾醬150ML", "森文"),
            ("加茂食品有限公司", "蛋小白雞蛋干120g-原味", "蛋小白"),
            ("遠東百貨股份有限公司", "MANTOVA葵花油", "MANTOVA"),
            ("遠東百貨股份有限公司", "加拿大Fazio芥花油", "Fazio"),
            ("永詮食品股份有限公司", "旺來興香草粉", "旺來興"),
        )
        for company, product, expected in cases:
            with self.subTest(product=product):
                self.assert_brand(company, product, expected)

    def test_company_fallback_is_explicitly_marked(self):
        self.assert_brand(
            "誠麗實業股份有限公司",
            "冷凍覆盆莓",
            "誠麗",
            "company_fallback",
        )
        self.assert_brand(
            "台東興業股份有限公司",
            "紐西蘭細精鹽(食品用)",
            "台東興業",
            "company_fallback",
        )

    def test_generic_words_are_not_inferred_as_brands(self):
        cases = (
            ("友士股份有限公司", "蜂蜜蛋糕"),
            ("友士股份有限公司", "酸梅汁"),
            ("友士股份有限公司", "冬瓜茶"),
            ("友士股份有限公司", "特級橄欖油"),
            ("友士股份有限公司", "冷凍草莓"),
            ("遠東百貨股份有限公司", "加拿大芥花油"),
        )
        for company, product in cases:
            with self.subTest(product=product):
                decision = extract_brand_decision(company, product)
                self.assertEqual(decision.name, "")
                self.assertEqual(decision.source, "unknown")

    def test_units_and_importers_are_not_brands(self):
        self.assert_brand("友士股份有限公司", "1000ML食用油", "")
        self.assert_brand("大北化工股份有限公司", "食品用香料", "")
        self.assert_brand("遠東百貨股份有限公司", "進口橄欖油", "")

    def test_bracket_and_alias_normalization(self):
        self.assert_brand("進口商股份有限公司", "【OREO】夾心餅乾", "OREO")
        self.assert_brand("遠東百貨股份有限公司", "Mantova橄欖油", "MANTOVA")

    def test_one_off_english_candidate_is_downgraded(self):
        products = [{
            "company_name": "遠東百貨股份有限公司",
            "product_name": "T550",
        }]
        assign_brands(products)
        self.assertEqual(products[0]["brand_name"], "")
        self.assertEqual(products[0]["brand_source"], "unknown")

    def test_product_codes_and_generic_english_are_not_formal_brands(self):
        samples = (
            "HL002 OLIMED 1L EVOO",
            "D003豬肉火鍋片",
            "PROPYLENE GLYCOL (FOOD ADDITIVE)",
            "OEM專用液糖(25KG)",
            "Sodium Carboxymethyl Cellulose",
            "MCT 油",
            "Premium大濾掛咖啡",
            "Peter Paul有機第一道冷壓椰子油",
            "Health Passion雞蛋乳酪米餅",
        )
        for product_name in samples:
            with self.subTest(product_name=product_name):
                decision = extract_brand_decision("測試食品有限公司", product_name)
                self.assertNotEqual(decision.source, "english_prefix")

    def test_english_aliases_are_canonicalized(self):
        self.assert_brand("測試食品有限公司", "bristot咖啡豆", "BRISTOT")
        self.assert_brand("測試食品有限公司", "Clemente橄欖油", "CLEMENTE")


if __name__ == "__main__":
    unittest.main()

import unittest

from app.services.scoring import LocationSignals, score_location


class ScoringTests(unittest.TestCase):
    def test_score_location_returns_expected_shape(self):
        result = score_location(
            LocationSignals(
                category="奶茶店",
                competitor_count_500m=3,
                competitor_count_1000m=8,
                residential_poi_count=12,
                office_poi_count=10,
                school_poi_count=2,
                transit_poi_count=4,
                commercial_poi_count=6,
                complementary_poi_count=8,
                rent_monthly=18000,
                budget_monthly=80000,
            )
        )

        self.assertGreaterEqual(result["total_score"], 0)
        self.assertLessEqual(result["total_score"], 100)
        self.assertIn(result["level"], {"推荐", "谨慎推荐", "高风险", "不建议"})
        self.assertEqual(len(result["dimensions"]), 6)
        self.assertEqual(result["model_insights"]["version"], "stage3_rules_v2_conservative")
        self.assertIn("IRS", result["model_insights"]["irs"]["name"])
        self.assertIn("哈夫", result["model_insights"]["huff"]["name"])
        self.assertIn("calibration", result["model_insights"])
        self.assertIn("data_confidence", result["model_insights"]["calibration"])
        self.assertTrue(result["next_actions"])

    def test_dense_competition_caps_total_score(self):
        result = score_location(
            LocationSignals(
                category="奶茶店",
                competitor_count_500m=12,
                competitor_count_1000m=25,
                residential_poi_count=20,
                office_poi_count=20,
                school_poi_count=5,
                transit_poi_count=8,
                commercial_poi_count=20,
                complementary_poi_count=15,
            )
        )

        self.assertEqual(result["total_score"], 55)
        self.assertEqual(result["level"], "高风险")
        self.assertTrue(result["model_insights"]["calibration"]["applied_caps"])


if __name__ == "__main__":
    unittest.main()

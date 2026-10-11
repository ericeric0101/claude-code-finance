import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / ".agents/skills/stock-analysis/scripts"))
import recommendation
import valuation


class RecommendationToolsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.input = json.loads((ROOT / "research/AAPL/recommendation-input.json").read_text())
        cls.summary = recommendation.build_summary(cls.input)

    def test_no_automatic_dcf_haircut_buy_range(self):
        self.assertNotIn("buy_range", self.summary)
        self.assertNotIn("entry_price", self.summary)
        self.assertEqual(self.summary["valuation_methods"]["reinvestment-aware DCF"]["base"], 194)

    def test_valuation_method_disagreement_is_exposed(self):
        spread = self.summary["valuation_map"]["base_method_spread_pct_of_low"]
        self.assertAlmostEqual(spread, (242 - 194) / 194 * 100, places=1)
        self.assertEqual(self.summary["valuation_map"]["scenario_bounds"]["base"],
                         {"low": 194.0, "high": 242.0})

    def test_reverse_dcf_output_compares_to_base_and_bull(self):
        reverse = self.summary["reverse_dcf"]
        self.assertEqual(reverse["market_expectation_vs_cases"], "above modeled bull growth")
        # Regression-check the existing valuation engine still computes reverse DCF.
        dcf_input = json.loads((ROOT / "research/AAPL/valuation-input.json").read_text())
        result = valuation.run(dcf_input)
        self.assertIsNotNone(result["reverse_dcf"]["implied_growth"])
        self.assertAlmostEqual(result["reverse_dcf"]["implied_growth"],
                               0.1537019938, places=6)

    def test_earnings_catch_up_scenario(self):
        rows = self.summary["earnings_catch_up"]
        row = next(r for r in rows if r["annual_eps_growth_pct"] == 15.0 and r["years"] == 2)
        self.assertEqual(row["future_eps"], 11.33)
        self.assertEqual(row["static_price_pe"], 29.7)
        self.assertEqual(row["price_held_flat"], 336.64)

    def test_watch_does_not_require_entry_price(self):
        rendered = recommendation.render_action("WATCH", "Current price requires growth above the modeled bull case.")
        self.assertIn("does not set a required entry price", rendered)
        self.assertNotIn("$", rendered)
        with self.assertRaises(ValueError):
            recommendation.render_action("HOLD EXISTING", "Thesis intact.")

    def test_valuation_map_places_quote_against_all_method_scenarios(self):
        vm = self.summary["valuation_map"]
        self.assertEqual(vm["current_position"], "above all modeled bull values")
        self.assertEqual(vm["scenario_bounds"]["bull"], {"low": 295.0, "high": 318.0})


if __name__ == "__main__":
    unittest.main()

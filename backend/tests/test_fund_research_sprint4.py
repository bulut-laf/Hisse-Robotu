import unittest
from backend.app.funds.portfolio import Allocation, validate_allocations, allocation_amounts, stress_test


class PortfolioValidationTests(unittest.TestCase):
    def test_valid_weights_sum_to_100(self):
        result = validate_allocations([Allocation("FUND-A", 60), Allocation("FUND-B", 40)])
        self.assertTrue(result["valid"])
        self.assertAlmostEqual(result["total_weight_pct"], 100)

    def test_rejects_weights_not_sum_to_100(self):
        self.assertFalse(validate_allocations([Allocation("FUND-A", 60), Allocation("FUND-B", 30)])["valid"])

    def test_rejects_duplicate_fund_ids(self):
        result = validate_allocations([Allocation("FUND-A", 50), Allocation("FUND-A", 50)])
        self.assertFalse(result["valid"])
        self.assertTrue(any(issue.startswith("duplicate_fund_isin") for issue in result["issues"]))

    def test_empty_portfolio_invalid(self):
        self.assertFalse(validate_allocations([])["valid"])

    def test_allocation_amounts(self):
        result = allocation_amounts(14_000_000, [Allocation("FUND-A", 60), Allocation("FUND-B", 40)])
        self.assertEqual(result["FUND-A"], 8_400_000)
        self.assertEqual(result["FUND-B"], 5_600_000)

    def test_invalid_allocation_amounts_raise(self):
        with self.assertRaises(ValueError):
            allocation_amounts(1000, [Allocation("FUND-A", 70)])

    def test_stress_test_weighted_return(self):
        result = stress_test(
            [Allocation("FUND-A", 60), Allocation("FUND-B", 40)],
            {"FUND-A": -10, "FUND-B": -5},
        )
        self.assertTrue(result["comparable"])
        self.assertAlmostEqual(result["portfolio_return_pct"], -8)

    def test_missing_scenario_return_is_not_imputed(self):
        result = stress_test([Allocation("FUND-A", 60), Allocation("FUND-B", 40)], {"FUND-A": -10})
        self.assertFalse(result["comparable"])
        self.assertIsNone(result["portfolio_return_pct"])
        self.assertEqual(result["missing_funds"], ["FUND-B"])

    def test_negative_investment_rejected(self):
        with self.assertRaises(ValueError):
            allocation_amounts(-1, [Allocation("FUND-A", 100)])

    def test_invalid_scenario_allocation_rejected(self):
        with self.assertRaises(ValueError):
            stress_test([Allocation("FUND-A", 80)], {"FUND-A": -10})


if __name__ == "__main__":
    unittest.main()

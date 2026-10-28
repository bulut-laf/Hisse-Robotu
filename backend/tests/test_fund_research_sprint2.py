import unittest
from datetime import date
from backend.app.funds.performance import NavObservation, calculate_performance
from backend.app.funds.costs import estimate_annual_cost, compare_annual_costs


class PerformanceTests(unittest.TestCase):
    def test_total_return_and_drawdown(self):
        result = calculate_performance([
            NavObservation(date(2024,1,1),100),
            NavObservation(date(2024,1,2),120),
            NavObservation(date(2024,1,3),90),
            NavObservation(date(2024,1,4),110),
        ])
        self.assertAlmostEqual(result.total_return_pct, 10.0)
        self.assertAlmostEqual(result.max_drawdown_pct, -25.0)

    def test_sorts_observations(self):
        result = calculate_performance([
            NavObservation(date(2024,1,3),110),
            NavObservation(date(2024,1,1),100),
        ])
        self.assertEqual(result.first_date, date(2024,1,1))

    def test_requires_two_observations(self):
        with self.assertRaises(ValueError):
            calculate_performance([NavObservation(date(2024,1,1),100)])

    def test_rejects_duplicate_dates(self):
        with self.assertRaises(ValueError):
            calculate_performance([
                NavObservation(date(2024,1,1),100),
                NavObservation(date(2024,1,1),101),
            ])

    def test_rejects_nonpositive_nav(self):
        with self.assertRaises(ValueError):
            NavObservation(date(2024,1,1),0)

    def test_annualized_volatility_unavailable_for_one_return(self):
        result = calculate_performance([
            NavObservation(date(2024,1,1),100),
            NavObservation(date(2024,1,2),101),
        ])
        self.assertIsNone(result.annualized_volatility_pct)


class CostTests(unittest.TestCase):
    def test_cost_in_huf(self):
        result = estimate_annual_cost(14_000_000, 0.2, 0.05)
        self.assertAlmostEqual(result.estimated_annual_cost, 35_000)
        self.assertTrue(result.evidence_complete)

    def test_missing_fee_is_not_zero(self):
        result = estimate_annual_cost(14_000_000, None, 0.0)
        self.assertIsNone(result.estimated_annual_cost)
        self.assertFalse(result.evidence_complete)

    def test_comparison(self):
        result = compare_annual_costs(1_000_000, 0.2, 0.5)
        self.assertTrue(result["comparable"])
        self.assertAlmostEqual(result["difference"], -3000)

    def test_missing_comparison_rate(self):
        result = compare_annual_costs(1_000_000, 0.2, None)
        self.assertFalse(result["comparable"])
        self.assertIsNone(result["difference"])

    def test_rejects_invalid_cost(self):
        with self.assertRaises(ValueError):
            estimate_annual_cost(1000, 120, 0)


if __name__ == "__main__":
    unittest.main()

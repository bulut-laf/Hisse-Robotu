import unittest

from backend.app.funds.report import (
    build_fund_research_report,
    report_is_comparable,
)


class FundResearchReportTests(unittest.TestCase):
    def test_empty_report_is_not_comparable(self):
        report = build_fund_research_report()
        self.assertEqual(report["fund_count"], 0)
        self.assertFalse(report_is_comparable(report))

    def test_fund_count_and_isin_are_preserved(self):
        report = build_fund_research_report(
            funds=[{"isin": "IE000TEST001", "name": "Example"}]
        )
        self.assertEqual(report["fund_count"], 1)
        self.assertEqual(report["funds"][0]["fund_isin"], "IE000TEST001")

    def test_source_url_without_date_is_incomplete(self):
        report = build_fund_research_report(
            funds=[{"isin": "IE000TEST001", "source_url": "https://example.com"}]
        )
        self.assertEqual(report["funds"][0]["evidence_status"], "incomplete")
        self.assertFalse(report_is_comparable(report))

    def test_complete_source_fields_are_marked_verified(self):
        report = build_fund_research_report(funds=[{
            "isin": "IE000TEST001",
            "source_url": "https://example.com/factsheet",
            "source_date": "2026-10-01",
        }])
        self.assertEqual(report["funds"][0]["evidence_status"], "verified")
        self.assertTrue(report_is_comparable(report))

    def test_missing_values_are_not_imputed(self):
        report = build_fund_research_report(funds=[{"isin": "IE000TEST001"}])
        unknown = report["funds"][0]["unknown_fields"]
        self.assertIn("currency", unknown)
        self.assertIn("ongoing_charges_pct", unknown)

    def test_input_is_not_mutated(self):
        source = {"isin": "IE000TEST001"}
        build_fund_research_report(funds=[source])
        self.assertNotIn("fund_isin", source)

    def test_analysis_sections_are_preserved(self):
        report = build_fund_research_report(
            performance={"return_1y_pct": 7.5},
            costs={"ongoing_charges_pct": 0.2},
            overlap={"comparable": False},
            exposure={"country": None},
            stress={"portfolio_return_pct": None},
        )
        self.assertEqual(report["performance"]["return_1y_pct"], 7.5)
        self.assertFalse(report["overlap"]["comparable"])
        self.assertIsNone(report["stress"]["portfolio_return_pct"])

    def test_report_states_limitations(self):
        report = build_fund_research_report()
        self.assertTrue(any("not imputed" in x for x in report["limitations"]))


if __name__ == "__main__":
    unittest.main()

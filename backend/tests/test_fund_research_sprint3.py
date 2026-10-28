import csv
import tempfile
import unittest
from pathlib import Path
from backend.app.funds.overlap import Holding, pairwise_overlap, exposure_breakdown
from backend.app.funds.holdings_io import load_holdings_csv


class OverlapTests(unittest.TestCase):
    def test_pairwise_overlap_uses_minimum_shared_weights(self):
        a = [Holding("IE00BK5BQT80", "AAA", 8), Holding("IE00BK5BQT80", "BBB", 5)]
        b = [Holding("IE00B4L5Y983", "AAA", 4), Holding("IE00B4L5Y983", "CCC", 9)]
        result = pairwise_overlap(a, b)
        self.assertTrue(result["comparable"])
        self.assertAlmostEqual(result["overlap_pct"], 4)
        self.assertEqual(result["shared_assets"], ["AAA"])

    def test_empty_holdings_not_reported_as_zero_overlap(self):
        result = pairwise_overlap([], [Holding("IE00B4L5Y983", "AAA", 5)])
        self.assertFalse(result["comparable"])
        self.assertIsNone(result["overlap_pct"])

    def test_exposure_breakdown_and_unclassified_weight(self):
        rows = [
            Holding("IE00BK5BQT80", "AAA", 40, sector="Technology", country="US", currency="USD"),
            Holding("IE00BK5BQT80", "BBB", 35, sector="Financials", country="GB", currency="GBP"),
            Holding("IE00BK5BQT80", "CCC", 25),
        ]
        result = exposure_breakdown(rows, "sector")
        self.assertEqual(result["exposures"]["Technology"], 40)
        self.assertEqual(result["unclassified_weight_pct"], 25)

    def test_invalid_dimension_fails(self):
        with self.assertRaises(ValueError):
            exposure_breakdown([], "region")

    def test_weight_range_validation(self):
        with self.assertRaises(ValueError):
            Holding("IE00BK5BQT80", "AAA", 101)

    def test_rejects_non_http_source(self):
        with self.assertRaises(ValueError):
            Holding("IE00BK5BQT80", "AAA", 1, source_url="file:///private/data")

    def test_csv_import(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "holdings.csv"
            path.write_text(
                "fund_isin,asset_id,weight_pct,sector,country,currency,source_url\n"
                "IE00BK5BQT80,AAA,12.5,Technology,US,USD,https://example.com/holdings\n",
                encoding="utf-8",
            )
            rows = load_holdings_csv(path)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0].sector, "Technology")

    def test_csv_missing_required_column_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.csv"
            path.write_text("fund_isin,asset_id\nIE00BK5BQT80,AAA\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_holdings_csv(path)

    def test_csv_bad_row_has_line_number(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.csv"
            path.write_text("fund_isin,asset_id,weight_pct\nIE00BK5BQT80,AAA,not-a-number\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "line 2"):
                load_holdings_csv(path)


if __name__ == "__main__":
    unittest.main()

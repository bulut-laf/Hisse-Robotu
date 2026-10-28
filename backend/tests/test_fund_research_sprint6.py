import unittest

from backend.app.funds.evidence import (
    evidence_ledger,
    import_evidence_csv,
    validate_evidence_record,
    validate_fund_snapshot,
)


class FundEvidenceSprint6Tests(unittest.TestCase):
    def valid_record(self):
        return {
            "isin": "ie000test001",
            "field_name": "currency",
            "field_value": "EUR",
            "source_name": "Official factsheet",
            "source_url": "https://example.com/factsheet.pdf",
            "source_date": "2026-10-20",
            "captured_at": "2026-10-27T10:00:00+00:00",
        }

    def test_valid_evidence_record_normalizes_isin(self):
        result = validate_evidence_record(self.valid_record())
        self.assertTrue(result["valid"])
        self.assertEqual(result["isin"], "IE000TEST001")

    def test_missing_source_metadata_is_rejected(self):
        record = self.valid_record()
        record["source_url"] = ""
        result = validate_evidence_record(record)
        self.assertFalse(result["valid"])
        self.assertIn("missing_source_url", result["issues"])

    def test_invalid_source_url_is_rejected(self):
        record = self.valid_record()
        record["source_url"] = "file:///factsheet.pdf"
        result = validate_evidence_record(record)
        self.assertFalse(result["valid"])
        self.assertIn("invalid_source_url", result["issues"])

    def test_invalid_source_date_is_rejected(self):
        record = self.valid_record()
        record["source_date"] = "20-10-2026"
        self.assertIn("invalid_source_date", validate_evidence_record(record)["issues"])

    def test_snapshot_keeps_missing_values_unknown(self):
        result = validate_fund_snapshot({
            "isin": "IE000TEST001",
            "source_name": "Official",
            "source_url": "https://example.com",
            "source_date": "2026-10-20",
        })
        self.assertEqual(result["evidence_status"], "source_documented")
        self.assertIn("currency", result["unknown_fields"])
        self.assertIn("nav", result["unknown_fields"])

    def test_snapshot_rejects_risk_outside_one_to_seven(self):
        result = validate_fund_snapshot({
            "isin": "IE000TEST001",
            "source_name": "Official",
            "source_url": "https://example.com",
            "source_date": "2026-10-20",
            "risk_indicator": 9,
        })
        self.assertIn("invalid_risk_indicator", result["issues"])

    def test_csv_import_strips_utf8_bom_and_parses_row(self):
        csv_text = "\ufeffisin,field_name,field_value,source_name,source_url,source_date\nIE000TEST001,currency,EUR,Official,https://example.com,2026-10-20\n"
        result = import_evidence_csv(csv_text)
        self.assertTrue(result["valid"])
        self.assertEqual(result["row_count"], 1)

    def test_csv_import_reports_missing_columns(self):
        result = import_evidence_csv("isin,field_name\nIE000TEST001,currency\n")
        self.assertFalse(result["valid"])
        self.assertIn("source_url", result["missing_columns"])

    def test_csv_import_flags_invalid_row(self):
        csv_text = "isin,field_name,field_value,source_name,source_url,source_date\nIE000TEST001,currency,EUR,Official,ftp://bad,2026-10-20\n"
        result = import_evidence_csv(csv_text)
        self.assertFalse(result["valid"])
        self.assertEqual(result["invalid_rows"][0]["line"], 2)

    def test_ledger_preserves_multiple_observations(self):
        first = self.valid_record()
        second = dict(first, field_value="HUF", source_date="2026-10-21")
        ledger = evidence_ledger([first, second])
        self.assertEqual(ledger["fund_count"], 1)
        self.assertEqual(ledger["observation_count"], 2)
        self.assertEqual(len(ledger["funds"]["IE000TEST001"]["currency"]), 2)


if __name__ == "__main__":
    unittest.main()
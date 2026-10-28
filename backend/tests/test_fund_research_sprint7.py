import unittest
from datetime import datetime, timezone
from io import BytesIO

from backend.app.funds.erste_market import (
    build_comparison_url,
    evidence_record_from_fetch,
    fetch_erste_market_page,
    parse_visible_page,
)


class FakeResponse:
    def __init__(self, body, status=200, content_type="text/html; charset=utf-8"):
        self._body = body
        self.status = status
        self.headers = {"Content-Type": content_type}
        self.closed = False

    def read(self):
        return self._body

    def getcode(self):
        return self.status

    def close(self):
        self.closed = True


class ErsteMarketSprint7Tests(unittest.TestCase):
    def test_builds_official_url_with_isin(self):
        url = build_comparison_url("HU0000702006")
        self.assertTrue(url.startswith("https://www.erstemarket.hu/"))
        self.assertIn("funds=HU0000702006", url)
        self.assertIn("intervallum=365", url)

    def test_invalid_isin_rejected(self):
        with self.assertRaises(ValueError):
            build_comparison_url("BAD")

    def test_invalid_interval_rejected(self):
        with self.assertRaises(ValueError):
            build_comparison_url("HU0000702006", interval_days=0)

    def test_parser_extracts_title_and_visible_text(self):
        result = parse_visible_page(
            "<html><head><title>Fund page</title><script>secret()</script></head>"
            "<body><h1>ISIN</h1><p>HU0000702006</p></body></html>"
        )
        self.assertEqual(result["title"], "Fund page")
        self.assertIn("HU0000702006", result["text"])
        self.assertNotIn("secret", result["text"])

    def test_parser_handles_utf8_bom(self):
        result = parse_visible_page("\ufeff<html><body><p>ГЃrfolyam</p></body></html>")
        self.assertIn("ГЃrfolyam", result["text"])

    def test_successful_fetch_records_source_and_time(self):
        response = FakeResponse(b"<html><title>Erste</title><body>Fund value</body></html>")
        fixed_time = lambda: datetime(2026, 10, 28, tzinfo=timezone.utc)
        result = fetch_erste_market_page(
            "HU0000702006",
            opener=lambda request, timeout: response,
            now=fixed_time,
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["source_name"], "Erste Market")
        self.assertEqual(result["retrieved_at"], "2026-10-28T00:00:00+00:00")
        self.assertTrue(response.closed)

    def test_http_error_is_not_marked_verified(self):
        from urllib.error import HTTPError
        result = fetch_erste_market_page(
            "HU0000702006",
            opener=lambda request, timeout: (_ for _ in ()).throw(
                HTTPError(request.full_url, 503, "unavailable", {}, None)
            ),
        )
        self.assertFalse(result["ok"])
        self.assertEqual(result["data_status"], "not_verified")
        self.assertEqual(result["http_status"], 503)

    def test_empty_page_is_not_marked_verified(self):
        result = fetch_erste_market_page(
            "HU0000702006",
            opener=lambda request, timeout: FakeResponse(b"<html><body></body></html>"),
        )
        self.assertFalse(result["ok"])
        self.assertEqual(result["data_status"], "not_verified")

    def test_evidence_requires_explicit_source_date(self):
        result = {
            "ok": True, "source_name": "Erste Market",
            "requested_url": "https://www.erstemarket.hu/fund",
            "retrieved_at": "2026-10-28T00:00:00+00:00",
        }
        with self.assertRaises(ValueError):
            evidence_record_from_fetch(
                result, isin="HU0000702006", field_name="currency",
                field_value="HUF",
            )

    def test_evidence_record_keeps_source_fields(self):
        result = {
            "ok": True, "source_name": "Erste Market",
            "requested_url": "https://www.erstemarket.hu/fund",
            "retrieved_at": "2026-10-28T00:00:00+00:00",
        }
        record = evidence_record_from_fetch(
            result, isin="hu0000702006", field_name="currency",
            field_value="HUF", source_date="2026-10-27",
        )
        self.assertEqual(record["isin"], "HU0000702006")
        self.assertEqual(record["source_date"], "2026-10-27")
        self.assertEqual(record["captured_at"], result["retrieved_at"])


if __name__ == "__main__":
    unittest.main()
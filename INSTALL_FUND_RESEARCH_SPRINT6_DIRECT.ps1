$ErrorActionPreference = "Stop"
$ProjectRoot = "D:\Projects\Hisse-Robotu"
Set-Location $ProjectRoot

$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupRoot = Join-Path $ProjectRoot "_backups\fund_research_sprint6_$stamp"
New-Item -ItemType Directory -Force -Path $backupRoot | Out-Null

$moduleRelative = "backend\app\funds\evidence.py"
$testRelative = "backend\tests\test_fund_research_sprint6.py"
$notesRelative = "PROJECT_NOTES_FUND_RESEARCH_SPRINT6.md"

$module = @'
"""Source-aware fund evidence ingestion and validation.

No network requests are performed. Source data must be supplied by an operator
through structured records or CSV; unknown values are not inferred.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, asdict
from datetime import date, datetime, timezone
from io import StringIO
from typing import Any, Iterable, Mapping


REQUIRED_SOURCE_FIELDS = ("source_name", "source_url", "source_date")
FUND_FIELDS = (
    "isin", "name", "provider", "fund_type", "currency",
    "ongoing_charges_pct", "risk_indicator", "nav", "nav_date",
)


@dataclass(frozen=True)
class EvidenceRecord:
    isin: str
    field_name: str
    field_value: Any
    source_name: str
    source_url: str
    source_date: str
    captured_at: str | None = None


def _valid_iso_date(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        date.fromisoformat(value.strip()[:10])
        return True
    except ValueError:
        return False


def validate_evidence_record(record: Mapping[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    isin = str(record.get("isin") or "").strip().upper()
    field_name = str(record.get("field_name") or "").strip()
    if not isin:
        issues.append("missing_isin")
    if not field_name:
        issues.append("missing_field_name")
    if record.get("field_value") is None or record.get("field_value") == "":
        issues.append("missing_field_value")
    for field in REQUIRED_SOURCE_FIELDS:
        if not str(record.get(field) or "").strip():
            issues.append(f"missing_{field}")
    if record.get("source_date") and not _valid_iso_date(record.get("source_date")):
        issues.append("invalid_source_date")
    url = str(record.get("source_url") or "").strip().lower()
    if url and not (url.startswith("https://") or url.startswith("http://")):
        issues.append("invalid_source_url")
    if record.get("captured_at"):
        captured = str(record["captured_at"])
        try:
            datetime.fromisoformat(captured.replace("Z", "+00:00"))
        except ValueError:
            issues.append("invalid_captured_at")
    return {
        "valid": not issues,
        "issues": issues,
        "isin": isin or None,
        "field_name": field_name or None,
    }


def validate_fund_snapshot(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a snapshot and report gaps without guessing missing values."""
    isin = str(snapshot.get("isin") or "").strip().upper()
    issues: list[str] = []
    if not isin:
        issues.append("missing_isin")

    source_url = snapshot.get("source_url")
    source_date = snapshot.get("source_date")
    source_name = snapshot.get("source_name")
    source_complete = bool(
        str(source_name or "").strip()
        and str(source_url or "").strip()
        and str(source_url or "").strip().lower().startswith(("https://", "http://"))
        and _valid_iso_date(source_date)
    )
    if not source_name:
        issues.append("missing_source_name")
    if not source_url:
        issues.append("missing_source_url")
    elif not str(source_url).strip().lower().startswith(("https://", "http://")):
        issues.append("invalid_source_url")
    if not source_date:
        issues.append("missing_source_date")
    elif not _valid_iso_date(source_date):
        issues.append("invalid_source_date")

    unknown_fields = [field for field in FUND_FIELDS if snapshot.get(field) in (None, "")]
    if snapshot.get("ongoing_charges_pct") not in (None, ""):
        try:
            charges = float(snapshot["ongoing_charges_pct"])
            if charges < 0 or charges > 100:
                issues.append("invalid_ongoing_charges_pct")
        except (TypeError, ValueError):
            issues.append("invalid_ongoing_charges_pct")
    if snapshot.get("risk_indicator") not in (None, ""):
        try:
            risk = int(snapshot["risk_indicator"])
            if risk < 1 or risk > 7:
                issues.append("invalid_risk_indicator")
        except (TypeError, ValueError):
            issues.append("invalid_risk_indicator")
    if snapshot.get("nav_date") and not _valid_iso_date(snapshot.get("nav_date")):
        issues.append("invalid_nav_date")

    return {
        "valid": not issues,
        "evidence_status": "source_documented" if source_complete else "incomplete",
        "issues": issues,
        "isin": isin or None,
        "unknown_fields": unknown_fields,
        "source_complete": source_complete,
    }


def import_evidence_csv(text: str) -> dict[str, Any]:
    """Parse UTF-8/CSV text into normalized evidence records; no values are inferred."""
    reader = csv.DictReader(StringIO(text.lstrip("\ufeff")))
    required = {"isin", "field_name", "field_value", "source_name", "source_url", "source_date"}
    headers = set(reader.fieldnames or [])
    missing_columns = sorted(required - headers)
    if missing_columns:
        return {
            "valid": False,
            "issues": ["missing_columns"],
            "missing_columns": missing_columns,
            "records": [],
        }

    records: list[dict[str, Any]] = []
    invalid_rows: list[dict[str, Any]] = []
    for line_number, row in enumerate(reader, start=2):
        normalized = {
            key: (value.strip() if isinstance(value, str) else value)
            for key, value in row.items()
        }
        result = validate_evidence_record(normalized)
        normalized["validation"] = result
        records.append(normalized)
        if not result["valid"]:
            invalid_rows.append({"line": line_number, "issues": result["issues"]})
    return {
        "valid": not invalid_rows,
        "issues": [],
        "missing_columns": [],
        "row_count": len(records),
        "invalid_rows": invalid_rows,
        "records": records,
    }


def evidence_ledger(records: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Build a stable audit ledger grouped by ISIN and field, retaining every observation."""
    ledger: dict[str, dict[str, list[dict[str, Any]]]] = {}
    invalid_count = 0
    for record in records:
        check = validate_evidence_record(record)
        if not check["valid"]:
            invalid_count += 1
        isin = check["isin"] or "_MISSING_ISIN_"
        field = check["field_name"] or "_MISSING_FIELD_"
        ledger.setdefault(isin, {}).setdefault(field, []).append(dict(record))
    return {
        "fund_count": len(ledger),
        "observation_count": sum(
            len(observations)
            for fields in ledger.values()
            for observations in fields.values()
        ),
        "invalid_observation_count": invalid_count,
        "funds": ledger,
    }
'@

$tests = @'
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
'@

$notes = @'
# Fund Research Sprint 6 — Source-aware evidence ingestion

## Scope
- Adds field-level evidence validation, fund snapshot validation, CSV ingestion and an audit ledger.
- Does not perform network requests or fabricate real fund data.
- Every observation retains its source name, URL, source date and optional capture timestamp.
- Missing fields stay unknown; repeated observations are preserved rather than silently overwritten.
- A source-documentation status confirms required source metadata is present, not that the underlying source was independently audited.

## CSV format
Required columns: `isin,field_name,field_value,source_name,source_url,source_date`
Optional column: `captured_at`

## Target tests
`.\.venv\Scripts\python.exe -m pytest backend\tests\test_fund_research_sprint6.py -q`

## Full regression
`.\.venv\Scripts\python.exe -m pytest`
'@

$payloads = @{
    $moduleRelative = $module
    $testRelative = $tests
    $notesRelative = $notes
}

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
foreach ($relative in $payloads.Keys) {
    $destination = Join-Path $ProjectRoot $relative
    if (Test-Path $destination) {
        $backupDestination = Join-Path $backupRoot $relative
        New-Item -ItemType Directory -Force -Path (Split-Path $backupDestination -Parent) | Out-Null
        Copy-Item $destination $backupDestination -Force
    }
    New-Item -ItemType Directory -Force -Path (Split-Path $destination -Parent) | Out-Null
    [System.IO.File]::WriteAllText($destination, $payloads[$relative], $utf8NoBom)
}

Write-Host "`nSprint 6 dosyalari olusturuldu. Yedek: $backupRoot"
Write-Host "`n--- HEDEF TESTLER ---"
& .\.venv\Scripts\python.exe -m pytest $testRelative -q
if ($LASTEXITCODE -ne 0) {
    throw "Sprint 6 hedef testleri basarisiz. Tam regresyona gecmeyin."
}
Write-Host "`nHedef testler gecti. Simdi tam regresyonu calistirin:"
Write-Host ".\.venv\Scripts\python.exe -m pytest"

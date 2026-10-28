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
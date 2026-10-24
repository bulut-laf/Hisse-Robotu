
from datetime import date
from decimal import Decimal

from backend.app.analysis.fin_prod_v5_short_term_context_adapter import (
    _decimal_or_none,
    _date_or_none,
    _extract_exact_metric,
)

def test_missing_values_are_not_zero():
    assert _decimal_or_none(None) is None
    assert _decimal_or_none("") is None

def test_exact_metric_requires_explicit_key():
    docs = [("x.json", {"technical_trend": "72.5"})]
    value, evidence = _extract_exact_metric(
        docs,
        ("technical_trend", "technical_trend_score", "trend_score"),
    )
    assert value == Decimal("72.5")
    assert evidence["status"] == "EXACT"

def test_conflicting_explicit_metric_fails_closed():
    docs = [
        ("a.json", {"technical_trend": "70"}),
        ("b.json", {"technical_trend_score": "71"}),
    ]
    value, evidence = _extract_exact_metric(
        docs,
        ("technical_trend", "technical_trend_score", "trend_score"),
    )
    assert value is None
    assert evidence["status"] == "CONFLICT"

def test_date_parser_supports_iso():
    assert _date_or_none("2026-08-04") == date(2026, 8, 4)

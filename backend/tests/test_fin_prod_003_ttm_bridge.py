from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
import pytest

from app.analysis.ttm_financial_bridge import build_ttm_basis_from_reports, TTMBridgeError


@dataclass
class Identity:
    symbol: str
    published_at: datetime


@dataclass
class Report:
    identity: Identity


def test_future_report_leakage_guard(monkeypatch):
    class DummySeries:
        points = ()
    monkeypatch.setattr(
        "app.analysis.ttm_financial_bridge.build_historical_financial_series",
        lambda reports: DummySeries(),
    )
    r = Report(Identity("TUPRS", datetime(2026, 8, 4, 18, 0)))
    with pytest.raises(TTMBridgeError):
        build_ttm_basis_from_reports([r], as_of=datetime(2026, 8, 4, 17, 0))


def test_no_ebitda_is_synthesized_without_verified_basis(monkeypatch):
    class DummySeries:
        points = ()
    monkeypatch.setattr(
        "app.analysis.ttm_financial_bridge.build_historical_financial_series",
        lambda reports: DummySeries(),
    )
    r = Report(Identity("TUPRS", datetime(2026, 8, 4, 18, 0)))
    result = build_ttm_basis_from_reports([r])
    assert result.ebitda_ttm is None
    assert "TTM_EBITDA_REQUIRES_CANONICAL_OR_EXPLICIT_OVERRIDE" in result.data_flags


def test_explicit_ebitda_override_is_preserved(monkeypatch):
    class DummySeries:
        points = ()
    monkeypatch.setattr(
        "app.analysis.ttm_financial_bridge.build_historical_financial_series",
        lambda reports: DummySeries(),
    )
    r = Report(Identity("TUPRS", datetime(2026, 8, 4, 18, 0)))
    result = build_ttm_basis_from_reports([r], ebitda_ttm_override=Decimal("123"))
    assert result.ebitda_ttm == Decimal("123")

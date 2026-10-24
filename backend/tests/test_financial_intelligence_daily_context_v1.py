from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace

import app.analysis.financial_intelligence_daily_context as daily


def _panel():
    return {
        "status": "PASS",
        "sections": {
            "financial_health": {
                "score": 80,
            }
        },
    }


def _bank_record(symbol="GARAN"):
    return {
        "symbol": symbol,
        "source_type": "OFFICIAL_SOURCE_BUNDLE",
    }


def _bank_context(symbol="GARAN"):
    return SimpleNamespace(
        symbol=symbol,
        as_of="2026-07-30",
        publication_date="2026-07-30",
        source_type="OFFICIAL_SOURCE_BUNDLE",
        source_uri="file:///bundle.json",
        canonical_input_ready=True,
        scoring_ready=True,
        production_evidence=True,
        activation_ready=True,
    )


def test_existing_panel_is_preserved_without_bank_record(
    monkeypatch,
):
    calls = []

    def fake_panel(root, symbol):
        calls.append((root, symbol))
        return _panel()

    monkeypatch.setattr(
        daily,
        "build_financial_intelligence_panel",
        fake_panel,
    )

    result = daily.build_financial_intelligence_daily_context(
        "ROOT",
        "garan",
    )

    assert result.symbol == "GARAN"
    assert result.panel == _panel()
    assert result.bank is None
    assert calls == [("ROOT", "GARAN")]


def test_period_key_is_forwarded_to_existing_panel(
    monkeypatch,
):
    calls = []

    def fake_panel(root, symbol, period_key=None):
        calls.append((root, symbol, period_key))
        return _panel()

    monkeypatch.setattr(
        daily,
        "build_financial_intelligence_panel",
        fake_panel,
    )

    result = daily.build_financial_intelligence_daily_context(
        "ROOT",
        "GARAN",
        period_key="2026_2",
    )

    assert result.panel == _panel()
    assert calls == [
        ("ROOT", "GARAN", "2026_2")
    ]


def test_matching_bank_record_is_attached(
    monkeypatch,
):
    monkeypatch.setattr(
        daily,
        "build_financial_intelligence_panel",
        lambda root, symbol: _panel(),
    )

    monkeypatch.setattr(
        daily,
        "build_bank_daily_production_context",
        lambda record: _bank_context("GARAN"),
    )

    result = daily.build_financial_intelligence_daily_context(
        "ROOT",
        "garan",
        bank_record=_bank_record("GARAN"),
    )

    assert result.bank is not None
    assert result.bank.symbol == "GARAN"
    assert result.bank.activation_ready is True


def test_failed_bank_bridge_remains_absent(
    monkeypatch,
):
    monkeypatch.setattr(
        daily,
        "build_financial_intelligence_panel",
        lambda root, symbol: _panel(),
    )

    monkeypatch.setattr(
        daily,
        "build_bank_daily_production_context",
        lambda record: None,
    )

    result = daily.build_financial_intelligence_daily_context(
        "ROOT",
        "GARAN",
        bank_record=_bank_record(),
    )

    assert result.panel == _panel()
    assert result.bank is None


def test_symbol_mismatch_does_not_call_bank_bridge(
    monkeypatch,
):
    calls = []

    monkeypatch.setattr(
        daily,
        "build_financial_intelligence_panel",
        lambda root, symbol: _panel(),
    )

    def fake_bank(record):
        calls.append(record)
        return _bank_context()

    monkeypatch.setattr(
        daily,
        "build_bank_daily_production_context",
        fake_bank,
    )

    result = daily.build_financial_intelligence_daily_context(
        "ROOT",
        "AKBNK",
        bank_record=_bank_record("GARAN"),
    )

    assert result.bank is None
    assert calls == []


def test_input_bank_record_is_not_mutated(
    monkeypatch,
):
    record = _bank_record()
    before = deepcopy(record)

    monkeypatch.setattr(
        daily,
        "build_financial_intelligence_panel",
        lambda root, symbol: _panel(),
    )

    monkeypatch.setattr(
        daily,
        "build_bank_daily_production_context",
        lambda record: _bank_context(),
    )

    daily.build_financial_intelligence_daily_context(
        "ROOT",
        "GARAN",
        bank_record=record,
    )

    assert record == before


def test_daily_context_is_frozen(
    monkeypatch,
):
    monkeypatch.setattr(
        daily,
        "build_financial_intelligence_panel",
        lambda root, symbol: _panel(),
    )

    result = daily.build_financial_intelligence_daily_context(
        "ROOT",
        "GARAN",
    )

    try:
        result.symbol = "AKBNK"
        raised = False
    except AttributeError:
        raised = True

    assert raised is True
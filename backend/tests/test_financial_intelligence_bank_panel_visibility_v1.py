from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace

import app.analysis.financial_intelligence_daily_context as daily


def _base_panel():
    return {
        "status": "PASS",
        "read_only": True,
        "sections": {
            "financial_health": {
                "score": 80,
            },
            "valuation": {
                "base": 100,
            },
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


def test_active_bank_context_is_visible_in_panel(
    monkeypatch,
):
    monkeypatch.setattr(
        daily,
        "build_financial_intelligence_panel",
        lambda root, symbol: _base_panel(),
    )

    monkeypatch.setattr(
        daily,
        "build_bank_daily_production_context",
        lambda record: _bank_context(),
    )

    result = daily.build_financial_intelligence_daily_context(
        "ROOT",
        "GARAN",
        bank_record=_bank_record(),
    )

    bank_section = result.panel["sections"]["bank_production"]

    assert bank_section == {
        "status": "ACTIVE",
        "symbol": "GARAN",
        "as_of": "2026-07-30",
        "publication_date": "2026-07-30",
        "source_type": "OFFICIAL_SOURCE_BUNDLE",
        "canonical_input_ready": True,
        "scoring_ready": True,
        "production_evidence": True,
        "activation_ready": True,
        "read_only": True,
    }


def test_existing_panel_sections_are_preserved(
    monkeypatch,
):
    panel = _base_panel()

    monkeypatch.setattr(
        daily,
        "build_financial_intelligence_panel",
        lambda root, symbol: panel,
    )

    monkeypatch.setattr(
        daily,
        "build_bank_daily_production_context",
        lambda record: _bank_context(),
    )

    result = daily.build_financial_intelligence_daily_context(
        "ROOT",
        "GARAN",
        bank_record=_bank_record(),
    )

    assert (
        result.panel["sections"]["financial_health"]["score"]
        == 80
    )
    assert (
        result.panel["sections"]["valuation"]["base"]
        == 100
    )
    assert result.panel["status"] == "PASS"
    assert result.panel["read_only"] is True


def test_original_panel_is_not_mutated(
    monkeypatch,
):
    panel = _base_panel()
    before = deepcopy(panel)

    monkeypatch.setattr(
        daily,
        "build_financial_intelligence_panel",
        lambda root, symbol: panel,
    )

    monkeypatch.setattr(
        daily,
        "build_bank_daily_production_context",
        lambda record: _bank_context(),
    )

    daily.build_financial_intelligence_daily_context(
        "ROOT",
        "GARAN",
        bank_record=_bank_record(),
    )

    assert panel == before
    assert "bank_production" not in panel["sections"]


def test_no_bank_context_does_not_add_bank_section(
    monkeypatch,
):
    monkeypatch.setattr(
        daily,
        "build_financial_intelligence_panel",
        lambda root, symbol: _base_panel(),
    )

    result = daily.build_financial_intelligence_daily_context(
        "ROOT",
        "TUPRS",
    )

    assert "bank_production" not in result.panel["sections"]


def test_failed_bank_gate_is_not_visible(
    monkeypatch,
):
    monkeypatch.setattr(
        daily,
        "build_financial_intelligence_panel",
        lambda root, symbol: _base_panel(),
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

    assert result.bank is None
    assert "bank_production" not in result.panel["sections"]


def test_wrong_symbol_bank_record_is_not_visible(
    monkeypatch,
):
    calls = []

    monkeypatch.setattr(
        daily,
        "build_financial_intelligence_panel",
        lambda root, symbol: _base_panel(),
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
    assert "bank_production" not in result.panel["sections"]
    assert calls == []
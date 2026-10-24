from __future__ import annotations

import app.ui.financial_intelligence_presentation_contract as presentation
import app.ui.financial_intelligence_ui_boundary as boundary


def _bank():
    return {
        "status": "ACTIVE",
        "symbol": "GARAN",
        "as_of": "2026-07-30",
        "publication_date": "2026-07-30",
        "production_evidence": True,
        "activation_ready": True,
        "read_only": True,
    }


def _renderer_payload(bank=None):
    return {
        "status": "PASS",
        "symbol": "GARAN",
        "eligible_symbols": ["GARAN"],
        "panel_status": "PASS",
        "financial_health": 80,
        "cash_quality": 70,
        "capital_efficiency": 60,
        "risk": "LOW",
        "current_price": 100,
        "attractive_entry_price": 90,
        "valuation_status": "FAIR",
        "bank_production": bank,
        "panel_artifact": "panel.json",
    }


def test_presentation_contract_passes_bank_production_read_only(
    monkeypatch,
):
    monkeypatch.setattr(
        presentation,
        "build_financial_intelligence_renderer_payload",
        lambda root, symbol=None: _renderer_payload(_bank()),
    )

    result = (
        presentation.build_financial_intelligence_presentation_contract(
            "ROOT",
            symbol="GARAN",
        )
    )

    assert result["status"] == "PASS"
    assert result["bank_production"] == _bank()


def test_presentation_without_bank_remains_none(
    monkeypatch,
):
    monkeypatch.setattr(
        presentation,
        "build_financial_intelligence_renderer_payload",
        lambda root, symbol=None: _renderer_payload(None),
    )

    result = (
        presentation.build_financial_intelligence_presentation_contract(
            "ROOT",
            symbol="GARAN",
        )
    )

    assert result["bank_production"] is None


def test_ui_boundary_exposes_bank_production(
    monkeypatch,
):
    bank = _bank()

    monkeypatch.setattr(
        boundary,
        "build_financial_intelligence_presentation_contract",
        lambda root, symbol=None: {
            "status": "PASS",
            "symbol": "GARAN",
            "eligible_symbols": ["GARAN"],
            "panel_status": "PASS",
            "cards": [],
            "valuation": {},
            "bank_production": bank,
            "panel_artifact": "panel.json",
        },
    )

    result = boundary.build_financial_intelligence_ui_boundary(
        "ROOT",
        symbol="GARAN",
    )

    assert result["status"] == "PASS"
    assert result["bank_production"] == bank
    assert result["bank_production"]["read_only"] is True


def test_ui_boundary_without_bank_remains_none(
    monkeypatch,
):
    monkeypatch.setattr(
        boundary,
        "build_financial_intelligence_presentation_contract",
        lambda root, symbol=None: {
            "status": "PASS",
            "symbol": "TUPRS",
            "eligible_symbols": ["TUPRS"],
            "panel_status": "PASS",
            "cards": [],
            "valuation": {},
            "bank_production": None,
            "panel_artifact": "panel.json",
        },
    )

    result = boundary.build_financial_intelligence_ui_boundary(
        "ROOT",
        symbol="TUPRS",
    )

    assert result["bank_production"] is None


def test_bank_ui_payload_has_no_trade_authority(
    monkeypatch,
):
    bank = _bank()

    monkeypatch.setattr(
        boundary,
        "build_financial_intelligence_presentation_contract",
        lambda root, symbol=None: {
            "status": "PASS",
            "symbol": "GARAN",
            "eligible_symbols": ["GARAN"],
            "panel_status": "PASS",
            "cards": [],
            "valuation": {},
            "bank_production": bank,
            "panel_artifact": "panel.json",
        },
    )

    result = boundary.build_financial_intelligence_ui_boundary(
        "ROOT",
        symbol="GARAN",
    )

    keys = set(result["bank_production"])

    forbidden = {
        "buy",
        "sell",
        "trade",
        "recommendation",
        "ranking",
        "target_price",
        "entry_price",
        "position_size",
    }

    assert forbidden.isdisjoint(keys)


def test_existing_ui_boundary_contract_is_preserved(
    monkeypatch,
):
    monkeypatch.setattr(
        boundary,
        "build_financial_intelligence_presentation_contract",
        lambda root, symbol=None: {
            "status": "PASS",
            "symbol": "GARAN",
            "eligible_symbols": ["GARAN"],
            "panel_status": "PASS",
            "cards": [],
            "valuation": {},
            "bank_production": _bank(),
            "panel_artifact": "panel.json",
        },
    )

    result = boundary.build_financial_intelligence_ui_boundary(
        "ROOT",
        symbol="GARAN",
    )

    assert result["status"] == "PASS"
    assert result["symbol"] == "GARAN"
    assert result["metric_cards"] == []
    assert result["valuation_rows"] == []
    assert result["mode"] == "READ_ONLY_UI_CONSUMPTION_BOUNDARY"
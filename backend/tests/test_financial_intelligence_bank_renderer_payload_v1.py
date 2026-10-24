from __future__ import annotations

from pathlib import Path

import app.ui.financial_intelligence_renderer_payload as renderer


def _contract(panel):
    return {
        "status": "PASS",
        "symbol": "GARAN",
        "eligible_symbols": ["GARAN"],
        "panel": panel,
        "panel_artifact": str(
            Path("GARAN_financial_intelligence_panel.json")
        ),
    }


def _panel(bank=None):
    sections = {
        "financial_health": {
            "score": 80,
        }
    }

    if bank is not None:
        sections["bank_production"] = bank

    return {
        "status": "PASS",
        "sections": sections,
    }


def _bank(**overrides):
    data = {
        "status": "ACTIVE",
        "symbol": "GARAN",
        "as_of": "2026-07-30",
        "publication_date": "2026-07-30",
        "production_evidence": True,
        "activation_ready": True,
        "read_only": True,
    }
    data.update(overrides)
    return data


def _patch_dependencies(monkeypatch, panel):
    monkeypatch.setattr(
        renderer,
        "build_financial_intelligence_renderer_contract",
        lambda root, symbol=None: _contract(panel),
    )

    monkeypatch.setattr(
        renderer,
        "_acceptance_file",
        lambda data_dir, symbol: None,
    )

    monkeypatch.setattr(
        renderer,
        "_candidate_jsons",
        lambda fi_dir, symbol: [],
    )


def test_active_bank_section_is_exposed_read_only(
    monkeypatch,
):
    _patch_dependencies(
        monkeypatch,
        _panel(_bank()),
    )

    result = renderer.build_financial_intelligence_renderer_payload(
        "ROOT",
        symbol="GARAN",
    )

    assert result["status"] == "PASS"

    assert result["bank_production"] == {
        "status": "ACTIVE",
        "symbol": "GARAN",
        "as_of": "2026-07-30",
        "publication_date": "2026-07-30",
        "production_evidence": True,
        "activation_ready": True,
        "read_only": True,
    }


def test_missing_bank_section_stays_none(
    monkeypatch,
):
    _patch_dependencies(
        monkeypatch,
        _panel(),
    )

    result = renderer.build_financial_intelligence_renderer_payload(
        "ROOT",
        symbol="GARAN",
    )

    assert result["bank_production"] is None


def test_non_activation_ready_bank_is_hidden(
    monkeypatch,
):
    _patch_dependencies(
        monkeypatch,
        _panel(
            _bank(
                activation_ready=False,
            )
        ),
    )

    result = renderer.build_financial_intelligence_renderer_payload(
        "ROOT",
        symbol="GARAN",
    )

    assert result["bank_production"] is None


def test_missing_production_evidence_is_hidden(
    monkeypatch,
):
    _patch_dependencies(
        monkeypatch,
        _panel(
            _bank(
                production_evidence=False,
            )
        ),
    )

    result = renderer.build_financial_intelligence_renderer_payload(
        "ROOT",
        symbol="GARAN",
    )

    assert result["bank_production"] is None


def test_bank_payload_contains_no_trade_fields(
    monkeypatch,
):
    _patch_dependencies(
        monkeypatch,
        _panel(_bank()),
    )

    result = renderer.build_financial_intelligence_renderer_payload(
        "ROOT",
        symbol="GARAN",
    )

    bank = result["bank_production"]

    assert bank is not None

    forbidden = {
        "buy",
        "sell",
        "trade",
        "recommendation",
        "ranking",
        "target_price",
        "entry_price",
    }

    assert forbidden.isdisjoint(bank.keys())


def test_existing_renderer_values_are_preserved(
    monkeypatch,
):
    panel = _panel(_bank())

    _patch_dependencies(
        monkeypatch,
        panel,
    )

    result = renderer.build_financial_intelligence_renderer_payload(
        "ROOT",
        symbol="GARAN",
    )

    assert result["status"] == "PASS"
    assert result["symbol"] == "GARAN"
    assert result["panel_status"] == "PASS"
    assert result["mode"] == "READ_ONLY_RENDERER_PAYLOAD"
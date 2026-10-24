from __future__ import annotations

from pathlib import Path

import pytest

from app.ui.financial_intelligence_dashboard import (
    _load_dashboard_panel,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    "symbol",
    (
        "AKBNK",
        "GARAN",
    ),
)
def test_real_bank_bundle_loads_into_dashboard(
    symbol,
):
    panel, source_path = _load_dashboard_panel(
        PROJECT_ROOT,
        symbol,
    )

    assert panel is not None
    assert source_path.exists()

    sections = panel.get("sections") or {}

    assert "bank_production" in sections

    bank = sections["bank_production"]

    assert bank["status"] == "ACTIVE"
    assert bank["symbol"] == symbol
    assert bank["canonical_input_ready"] is True
    assert bank["scoring_ready"] is True
    assert bank["production_evidence"] is True
    assert bank["activation_ready"] is True
    assert bank["read_only"] is True


@pytest.mark.parametrize(
    "symbol",
    (
        "AKBNK",
        "GARAN",
    ),
)
def test_bank_dashboard_section_has_no_trade_authority(
    symbol,
):
    panel, _ = _load_dashboard_panel(
        PROJECT_ROOT,
        symbol,
    )

    bank = panel["sections"]["bank_production"]

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

    assert forbidden.isdisjoint(bank.keys())


def test_unknown_symbol_remains_fail_closed():
    panel, path = _load_dashboard_panel(
        PROJECT_ROOT,
        "ZZZZZ",
    )

    assert panel is None
    assert path.name == (
        "ZZZZZ_financial_intelligence_panel.json"
    )
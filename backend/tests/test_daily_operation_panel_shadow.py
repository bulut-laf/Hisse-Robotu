from __future__ import annotations

from datetime import date

from backend.app.analysis.daily_operation_panel import (
    build_daily_operation_summary,
)
from backend.app.analysis.shadow_portfolio import ShadowPosition


def test_golge_portfoy_pozisyonlari_operasyon_paneline_dahil_edilir():
    shadow = ShadowPosition(
        symbol="THYAO",
        entry_date=date(2026, 7, 31),
        entry_price=100.0,
        quantity=10,
        capital_at_entry=10000.0,
    )

    summary = build_daily_operation_summary(
        pilot_records=(),
        signal_outcomes=(),
        trade_records=(),
        shadow_positions=(shadow,),
    )

    assert summary.shadow_trade_count == 1

from __future__ import annotations

from datetime import date

from backend.app.analysis.kap_fundamental_service import (
    KapFundamentalService,
)
from backend.app.data.fundamental_store import FundamentalJsonStore
from backend.app.data.kap_fundamental_source import KapFundamentalClient


def record(period_end="2026-06-30", year=2026, quarter=2):
    return {
        "symbol": "THYAO",
        "period_end": period_end,
        "fiscal_year": year,
        "fiscal_quarter": quarter,
        "currency": "TRY",
        "revenue": 1000,
        "gross_profit": 300,
        "operating_profit": 180,
        "ebitda": 220,
        "net_income": 120,
        "total_assets": 2500,
        "total_equity": 1000,
        "total_debt": 700,
        "cash_and_equivalents": 200,
        "current_assets": 900,
        "current_liabilities": 600,
        "operating_cash_flow": 160,
        "capital_expenditure": 40,
        "shares_outstanding": 100,
        "source": "KAP",
        "published_at": "2026-07-20",
    }


def test_guncel_kap_verisi_analiz_ve_kayit_uretir(tmp_path):
    client = KapFundamentalClient(
        fetcher=lambda symbol, start, end: [record()]
    )
    service = KapFundamentalService(
        client=client,
        store=FundamentalJsonStore(
            tmp_path / "fundamentals.json"
        ),
    )

    result = service.analyze(
        "THYAO",
        today=date(2026, 7, 30),
    )

    assert result.locked is False
    assert result.snapshot is not None
    assert result.snapshot.latest.period_key == "2026Q2"
    assert result.store_result is not None
    assert result.store_result.inserted == 1


def test_eski_kap_verisi_analizi_kilitler(tmp_path):
    client = KapFundamentalClient(
        fetcher=lambda symbol, start, end: [
            record(
                period_end="2025-06-30",
                year=2025,
                quarter=2,
            )
        ]
    )
    service = KapFundamentalService(
        client=client,
        store=FundamentalJsonStore(
            tmp_path / "fundamentals.json"
        ),
    )

    result = service.analyze(
        "THYAO",
        today=date(2026, 7, 30),
    )

    assert result.locked is True
    assert result.snapshot is None
    assert result.store_result is None

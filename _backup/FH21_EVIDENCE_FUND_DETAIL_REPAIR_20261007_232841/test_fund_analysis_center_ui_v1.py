from datetime import date, datetime, timezone
from decimal import Decimal

from backend.app.funds.analysis_engine import FundAnalysisClass, FundAnalysisResult
from backend.app.funds.contracts import DataQualityState
from backend.app.funds.portfolio_tracking import (
    FundPortfolioPosition,
    FundPortfolioSnapshot,
    FundPortfolioSnapshotJsonStore,
)
from backend.app.funds.pressure_risk import (
    FundExitLiquidity,
    FundOwnershipConcentration,
    PressureScoreStatus,
    PressureSubScore,
    StockFundPressureInput,
    StockFundPressureProfile,
)
from backend.app.ui.fund_analysis_center import (
    fund_analysis_rows,
    fund_pressure_rows,
    render_fund_analysis_center,
)


def item():
    return FundAnalysisResult("fund:tefas:AAA", "equity", FundAnalysisClass.A, "GL / NCELKL",
        ("F1", "F2", "F3", "F4"), ("F5",), (), (), "BROAD_STRENGTH", "kanıt")


class Column:
    def __init__(self): self.metrics = []
    def metric(self, *args, **kwargs): self.metrics.append((args, kwargs))


class Stub:
    def __init__(self): self.info_messages = []; self.frames = []; self.markdowns = []
    def subheader(self, *_args): pass
    def caption(self, *_args): pass
    def divider(self): pass
    def markdown(self, value): self.markdowns.append(value)
    def columns(self, count): return [Column() for _ in range(count)]
    def multiselect(self, _label, options, default, key): return default
    def selectbox(self, _label, options, index, key): return options[index]
    def dataframe(self, rows, **_kwargs): self.frames.append(rows)
    def info(self, message): self.info_messages.append(message)
    def error(self, message): self.info_messages.append(message)


def test_rows_are_research_only():
    row = fund_analysis_rows((item(),))[0]
    assert row["Sınıf"] == "A" and "AL" not in row and "SAT" not in row


def test_empty_and_populated_states():
    empty = Stub(); render_fund_analysis_center(empty, ())
    full = Stub(); render_fund_analysis_center(full, (item(),))
    assert empty.info_messages and full.frames


def _snapshot(fund: str, day: date, positions: tuple[FundPortfolioPosition, ...]):
    return FundPortfolioSnapshot(
        canonical_fund_id=fund,
        portfolio_date=day,
        publication_date=day,
        ingested_at=datetime(day.year, day.month, day.day, 12, tzinfo=timezone.utc),
        provider="TEFAS",
        positions=positions,
        data_quality_state=DataQualityState.VALID,
    )


def _position(fund: str, day: date, symbol: str, shares: str, weight: str):
    return FundPortfolioPosition(
        canonical_fund_id=fund,
        portfolio_date=day,
        symbol=symbol,
        asset_type="EQUITY",
        shares_held=Decimal(shares),
        market_value=Decimal(shares) * Decimal("100"),
        portfolio_weight=Decimal(weight),
    )


def test_portfolio_tracking_bridge_shows_current_changes_and_stock_breadth(tmp_path):
    fund = "fund:tefas:AAA"
    first = date(2026, 7, 31)
    second = date(2026, 8, 31)
    store = FundPortfolioSnapshotJsonStore(tmp_path / "portfolio_snapshots.json")
    store.append((
        _snapshot(fund, first, (_position(fund, first, "THYAO", "100", "0.10"),)),
        _snapshot(fund, second, (
            _position(fund, second, "THYAO", "130", "0.12"),
            _position(fund, second, "ASELS", "50", "0.05"),
        )),
    ))

    st = Stub()
    render_fund_analysis_center(st, (item(),), portfolio_store=store)

    assert any(rows and "Portföy %" in rows[0] for rows in st.frames)
    assert any(any(row.get("Durum") == "Yeni giriş" for row in rows) for rows in st.frames)
    assert any(rows and "Birikim Breadth %" in rows[0] for rows in st.frames)
    assert any("Güncel Portföy" in title for title in st.markdowns)


def test_pressure_rows_expose_raw_fdo_liquidation_and_keep_trade_authority_none():
    symbol = "THYAO"
    ownership = FundOwnershipConcentration(
        fund_owned_shares=Decimal("25"),
        free_float_shares=Decimal("100"),
        fund_free_float_ratio=Decimal("0.25"),
        largest_fund_share=Decimal("0.5"),
        top3_fund_share=Decimal("0.8"),
        top5_fund_share=Decimal("1"),
        hhi=Decimal("0.4"),
    )
    liquidity = FundExitLiquidity(
        total_fund_position_value=Decimal("1000"),
        adv20_value=Decimal("500"),
        median_daily_value_20=Decimal("450"),
        stressed_liquidity_capacity=Decimal("25"),
        liquidation_days_normal=Decimal("20"),
        liquidation_days_aggressive=Decimal("10"),
        liquidation_days_stress=Decimal("40"),
    )
    raw = StockFundPressureInput(
        symbol=symbol,
        observation_date=date(2026, 9, 1),
        ownership=ownership,
        liquidity=liquidity,
        ownership_change_20d=Decimal("-0.02"),
        distribution_breadth_20d=Decimal("0.6"),
        down_volume_ratio_20d=Decimal("0.7"),
        return_20d=Decimal("-0.05"),
        data_quality_state=DataQualityState.VALID,
    )
    ready = PressureSubScore(Decimal("80"), PressureScoreStatus.READY, ())
    profile = StockFundPressureProfile(
        symbol=symbol,
        observation_date=date(2026, 9, 1),
        fund_concentration_risk=ready,
        exit_difficulty_risk=ready,
        active_selling_pressure=ready,
        data_quality_state=DataQualityState.VALID,
    )

    row = fund_pressure_rows({symbol: profile}, {symbol: raw})[0]
    assert row["Fon/FDO %"] == 25.0
    assert row["Likidasyon Normal (gün)"] == 20.0
    assert row["Aktif Satış Baskısı"] == 80.0
    assert row["Trade Authority"] == "NONE"


def test_full_production_refresh_ui_contract_is_explicit_and_non_trading():
    from pathlib import Path
    source = (Path(__file__).resolve().parents[1] / "app" / "ui" / "fund_analysis_center.py").read_text(encoding="utf-8")
    assert "KAP FDO + Baskı Riskini Tam Güncelle" in source
    assert "network_enabled=True" in source
    assert "KAP/MKK dışı FDO tahmin edilmez" in source


def test_profile_live_ux_completion_contract_present():
    from pathlib import Path
    source = (Path(__file__).resolve().parents[1] / "app" / "ui" / "fund_analysis_center.py").read_text(encoding="utf-8")
    assert "Fiyat & Büyüklük Geçmişi" in source
    assert "Son Portföy Değişimi" in source
    assert "Veri Tazeliği" in source
    assert "Otomatik yenileme" in source


def test_erste_hungary_evidence_ui_exposes_read_only_artifact_provenance():
    from pathlib import Path

    source = Path(
        "backend/app/ui/fund_analysis_center.py"
    ).read_text(encoding="utf-8")

    assert "erste_hungary_evidence_as_of" in source
    assert "Evidence artifact as_of:" in source
    assert "provenance: read-only" in source


def test_erste_hungary_evidence_ui_exposes_fund_detail_selector():
    from pathlib import Path

    source = Path(
        "backend/app/ui/fund_analysis_center.py"
    ).read_text(encoding="utf-8")

    assert 'key="erste_hungary_evidence_fund_detail"' in source
    assert '"Evidence fonu"' in source
    assert "row.canonical_fund_id" in source
    assert "erste_hungary_evidence_rows(detail)" in source
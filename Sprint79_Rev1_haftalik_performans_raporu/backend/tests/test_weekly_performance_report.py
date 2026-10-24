from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path

from backend.app.analysis.shadow_portfolio import (
    CLOSED_STATUS,
    OPEN_STATUS,
    ShadowPosition,
)
from backend.app.analysis.weekly_performance_report import (
    WeeklyPerformanceArchive,
    build_weekly_performance_report,
    weekly_report_csv_bytes,
    weekly_report_pdf_bytes,
)


def closed(symbol: str, ret_price: float, score: int = 75) -> ShadowPosition:
    return ShadowPosition(
        symbol=symbol,
        entry_date=date(2026, 7, 25),
        entry_price=100.0,
        quantity=10,
        capital_at_entry=10000.0,
        status=CLOSED_STATUS,
        exit_date=date(2026, 7, 30),
        exit_price=ret_price,
        signal_class="İzlemeye Değer",
        quality_score=score,
        market_regime="Pozitif",
        sector="Ulaştırma",
        mfe_percent=8.0,
        mae_percent=-3.0,
        target_1=105.0,
        target_1_hit=ret_price >= 105.0,
        stop_loss=95.0,
        stop_hit=ret_price <= 95.0,
    )


def opened() -> ShadowPosition:
    return ShadowPosition(
        symbol="EREGL",
        entry_date=date(2026, 7, 29),
        entry_price=50.0,
        quantity=100,
        capital_at_entry=10000.0,
        status=OPEN_STATUS,
        last_price=52.0,
        last_price_date=date(2026, 7, 31),
        signal_class="Temkinli İzle",
        quality_score=65,
        market_regime="Nötr",
        sector="Metal",
        mfe_percent=6.0,
        mae_percent=-2.0,
    )


def test_haftalik_ozet_kazanani_kaybedeni_ve_kar_zarari_hesaplar():
    report = build_weekly_performance_report(
        (closed("THYAO", 108.0), closed("ASELS", 96.0), opened()),
        period_end=date(2026, 7, 31),
        generated_at=datetime(2026, 7, 31, tzinfo=timezone.utc),
    )

    assert report.closed_count == 2
    assert report.open_count == 1
    assert report.winning_count == 2
    assert report.losing_count == 1
    assert report.realized_pnl == 40.0
    assert report.unrealized_pnl == 200.0
    assert report.best_symbol == "THYAO.IS"
    assert report.worst_symbol == "ASELS.IS"


def test_ortalama_medyan_mfe_mae_ve_hedef_oranlari_uretilir():
    report = build_weekly_performance_report(
        (closed("THYAO", 108.0), closed("ASELS", 96.0)),
        period_end=date(2026, 7, 31),
    )

    assert report.average_return_percent == 2.0
    assert report.median_return_percent == 2.0
    assert report.average_mfe_percent == 8.0
    assert report.average_mae_percent == -3.0
    assert report.target_1_hit_rate == 50.0
    assert report.stop_hit_rate == 0.0


def test_sinyal_kalite_rejim_ve_sektor_gruplari_korunur():
    report = build_weekly_performance_report(
        (closed("THYAO", 108.0, 85), closed("ASELS", 96.0, 55)),
        period_end=date(2026, 7, 31),
    )

    assert any(row[0] == "İzlemeye Değer" for row in report.signal_class_rows)
    assert any(row[0] == "80-100" for row in report.quality_band_rows)
    assert any(row[0] == "Pozitif" for row in report.regime_rows)
    assert any(row[0] == "Ulaştırma" for row in report.sector_rows)


def test_csv_ve_pdf_uretilir():
    report = build_weekly_performance_report(
        (closed("THYAO", 108.0),),
        period_end=date(2026, 7, 31),
    )

    csv_bytes = weekly_report_csv_bytes(report)
    pdf_bytes = weekly_report_pdf_bytes(report)

    assert csv_bytes.startswith(b"\xef\xbb\xbf")
    assert b"%PDF" in pdf_bytes[:10]


def test_rapor_arsivi_csv_pdf_json_kaydeder(tmp_path: Path):
    report = build_weekly_performance_report(
        (closed("THYAO", 108.0),),
        period_end=date(2026, 7, 31),
    )
    archive = WeeklyPerformanceArchive(tmp_path)

    paths = archive.save(
        report,
        csv_bytes=weekly_report_csv_bytes(report),
        pdf_bytes=weekly_report_pdf_bytes(report),
    )

    assert all(path.exists() for path in paths)
    assert len(archive.list()) == 1

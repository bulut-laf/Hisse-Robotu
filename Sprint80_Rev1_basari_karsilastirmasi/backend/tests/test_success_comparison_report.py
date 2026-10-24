from __future__ import annotations

from datetime import date
from pathlib import Path

from backend.app.analysis.signal_outcome_tracking import (
    HorizonOutcome,
    SignalOutcome,
    SignalSnapshot,
)
from backend.app.analysis.success_comparison_report import (
    build_success_comparison_report,
    comparison_csv_bytes,
    comparison_pdf_bytes,
)


def outcome(
    *,
    symbol: str,
    regime: str,
    sector: str,
    momentum: str,
    divergence: str,
    volume: bool,
    quality: int,
    daily: str,
    weekly: str,
    return_percent: float,
) -> SignalOutcome:
    snapshot = SignalSnapshot(
        symbol=symbol,
        signal_date=date(2026, 7, 1),
        reference_price=100.0,
        decision_class="İzlemeye Değer",
        quality_score=quality,
        daily_direction=daily,
        weekly_direction=weekly,
        divergence_type=divergence,
        market_regime=regime,
        sector=sector,
        momentum_state=momentum,
        volume_confirmation=volume,
    )
    horizons = tuple(
        HorizonOutcome(
            horizon=horizon,
            available=True,
            end_date=date(2026, 7, horizon),
            close_return_percent=return_percent,
            maximum_favorable_excursion_percent=return_percent + 2,
            maximum_adverse_excursion_percent=-1.0,
            target_1_hit=return_percent > 2,
            target_2_hit=return_percent > 5,
            stop_hit=return_percent < -3,
        )
        for horizon in (5, 10, 20)
    )
    return SignalOutcome(
        snapshot=snapshot,
        horizons=horizons,
        evaluated_at="2026-07-31T12:00:00+00:00",
    )


def records():
    return (
        outcome(
            symbol="AAA",
            regime="Pozitif",
            sector="Banka",
            momentum="Pozitif MACD",
            divergence="Pozitif uyumsuzluk",
            volume=True,
            quality=85,
            daily="Pozitif",
            weekly="Pozitif",
            return_percent=6.0,
        ),
        outcome(
            symbol="BBB",
            regime="Pozitif",
            sector="Banka",
            momentum="Pozitif MACD",
            divergence="",
            volume=True,
            quality=75,
            daily="Pozitif",
            weekly="Pozitif",
            return_percent=3.0,
        ),
        outcome(
            symbol="CCC",
            regime="Negatif",
            sector="Sanayi",
            momentum="Negatif MACD",
            divergence="Negatif uyumsuzluk",
            volume=False,
            quality=45,
            daily="Negatif",
            weekly="Pozitif",
            return_percent=-4.0,
        ),
    )


def test_rejim_sektor_gosterge_hacim_kalite_ve_yon_gruplari_uretilir():
    report = build_success_comparison_report(
        records(),
        minimum_sample_size=1,
    )

    dimensions = {item.dimension for item in report.rows}

    assert dimensions == {
        "Piyasa rejimi",
        "Sektör",
        "Gösterge",
        "Günlük/haftalık yön",
        "Hacim onayı",
        "Kalite bandı",
    }


def test_5_10_20_gunluk_sonuclar_ayri_karsilastirilir():
    report = build_success_comparison_report(
        records(),
        minimum_sample_size=1,
    )

    assert {item.horizon for item in report.rows} == {5, 10, 20}


def test_basari_orani_getiri_mfe_mae_hedef_ve_stop_hesaplanir():
    report = build_success_comparison_report(
        records(),
        minimum_sample_size=1,
    )
    positive = next(
        item
        for item in report.rows
        if item.dimension == "Piyasa rejimi"
        and item.group == "Pozitif"
        and item.horizon == 5
    )

    assert positive.sample_count == 2
    assert positive.success_rate_percent == 100.0
    assert positive.average_return_percent == 4.5
    assert positive.average_mfe_percent == 6.5
    assert positive.average_mae_percent == -1.0
    assert positive.target_1_rate_percent == 100.0
    assert positive.stop_rate_percent == 0.0


def test_yetersiz_orneklem_uyarisi_uretilir():
    report = build_success_comparison_report(
        records(),
        minimum_sample_size=5,
    )

    assert all(
        item.sample_status.startswith("Yetersiz örneklem")
        for item in report.rows
    )
    assert report.strongest == ()
    assert report.weakest == ()


def test_csv_utf8_bom_ile_uretilir():
    report = build_success_comparison_report(
        records(),
        minimum_sample_size=1,
    )

    data = comparison_csv_bytes(report)

    assert data.startswith(b"\xef\xbb\xbf")
    assert "Piyasa rejimi" in data.decode("utf-8-sig")


def test_pdf_uretilir():
    report = build_success_comparison_report(
        records(),
        minimum_sample_size=1,
    )

    data = comparison_pdf_bytes(report)

    assert data.startswith(b"%PDF")

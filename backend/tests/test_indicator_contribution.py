from __future__ import annotations

from datetime import date

from backend.app.analysis.indicator_contribution import (
    analyze_indicator_contributions,
    analyze_redundancy,
    contribution_rows,
    contribution_to_csv,
)
from backend.app.analysis.signal_outcome_tracking import (
    HorizonOutcome,
    SignalOutcome,
    SignalSnapshot,
)


def outcome(
    index: int,
    *,
    result: float,
    daily: str,
    weekly: str,
    momentum: str,
    volume: bool,
    divergence: str,
    regime: str,
    atr: float,
    rr: float,
) -> SignalOutcome:
    snapshot = SignalSnapshot(
        symbol=f"TST{index}",
        signal_date=date(2026, 1, 2),
        reference_price=100.0,
        decision_class="İzlemeye Değer",
        quality_score=75 if result > 0 else 55,
        daily_direction=daily,
        weekly_direction=weekly,
        divergence_type=divergence,
        market_regime=regime,
        momentum_state=momentum,
        volume_confirmation=volume,
        atr_percent=atr,
        risk_reward_ratio=rr,
    )
    horizons = tuple(
        HorizonOutcome(
            horizon=horizon,
            available=True,
            end_date=date(2026, 2, 1),
            close_return_percent=result,
            maximum_favorable_excursion_percent=max(result, 1.0),
            maximum_adverse_excursion_percent=min(result, -1.0),
            target_1_hit=result >= 5,
            target_2_hit=result >= 10,
            stop_hit=result <= -5,
        )
        for horizon in (5, 10, 20)
    )
    return SignalOutcome(
        snapshot=snapshot,
        horizons=horizons,
        evaluated_at="2026-02-01T00:00:00+00:00",
    )


def dataset():
    records = []
    for index in range(6):
        records.append(
            outcome(
                index,
                result=6.0 + index,
                daily="Pozitif",
                weekly="Pozitif",
                momentum="Pozitif",
                volume=True,
                divergence="Normal Pozitif",
                regime="Olumlu",
                atr=2.5,
                rr=2.2,
            )
        )
    for index in range(6, 12):
        records.append(
            outcome(
                index,
                result=-4.0 - (index - 6),
                daily="Negatif",
                weekly="Negatif",
                momentum="Negatif",
                volume=False,
                divergence="Normal Negatif",
                regime="Olumsuz",
                atr=7.0,
                rr=1.2,
            )
        )
    return tuple(records)


def test_gosterge_mevcut_ve_yok_gruplari_karsilastirilir():
    results = analyze_indicator_contributions(
        dataset(),
        horizon=10,
        minimum_group_size=5,
    )

    daily = next(
        item
        for item in results
        if item.indicator == "Günlük trend pozitif"
    )

    assert daily.present_count == 6
    assert daily.absent_count == 6
    assert daily.success_rate_difference == 100.0
    assert daily.average_return_difference > 0
    assert daily.confidence == "Destekleyici"


def test_kucuk_orneklemde_kesin_sonuc_uretilmez():
    results = analyze_indicator_contributions(
        dataset()[:4],
        horizon=10,
        minimum_group_size=5,
    )

    assert all(item.confidence == "Yetersiz örnek" for item in results)
    assert all(
        item.success_rate_difference is None
        for item in results
    )


def test_eksik_gosterge_degeri_gruplara_dahil_edilmez():
    record = outcome(
        20,
        result=3.0,
        daily="Pozitif",
        weekly="Pozitif",
        momentum="",
        volume=True,
        divergence="",
        regime="",
        atr=2.0,
        rr=2.0,
    )
    results = analyze_indicator_contributions(
        (record,),
        horizon=5,
        minimum_group_size=2,
    )

    momentum = next(
        item for item in results if item.indicator == "Momentum pozitif"
    )
    assert momentum.present_count == 0
    assert momentum.absent_count == 0


def test_tekrarlayan_gostergeler_benzerlik_raporuna_girer():
    findings = analyze_redundancy(
        dataset(),
        minimum_sample_size=10,
        agreement_threshold=0.90,
    )

    assert findings
    assert findings[0].agreement_rate == 100.0


def test_tablo_ve_csv_raporu_uretilir():
    contributions = analyze_indicator_contributions(
        dataset(),
        horizon=20,
        minimum_group_size=5,
    )

    rows = contribution_rows(contributions)
    csv_content = contribution_to_csv(contributions)

    assert rows
    assert "Gösterge" in rows[0]
    assert csv_content.startswith(b"\xef\xbb\xbf")


def test_farkli_ufuklar_ayri_hesaplanabilir():
    five = analyze_indicator_contributions(
        dataset(),
        horizon=5,
        minimum_group_size=5,
    )
    twenty = analyze_indicator_contributions(
        dataset(),
        horizon=20,
        minimum_group_size=5,
    )

    assert all(item.horizon == 5 for item in five)
    assert all(item.horizon == 20 for item in twenty)

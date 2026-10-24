from datetime import date

from backend.app.prebreakout.prebreakout_backtest import (
    PreBreakoutForwardPerformance,
    PreBreakoutPerformanceLabel,
    PreBreakoutReplayResult,
    performans_etiketi_belirle,
)
from backend.app.prebreakout.prebreakout_models import (
    PreBreakoutResult,
    PreBreakoutStage,
)


def analysis(
    *,
    accepted: bool = True,
    late_entry: bool = False,
) -> PreBreakoutResult:
    return PreBreakoutResult(
        symbol="TEST.IS",
        score=65,
        stage=PreBreakoutStage.E2,
        stage_label="Dirence yaklaşıyor",
        features=None,
        component_scores=None,
        late_entry=late_entry,
        accepted=accepted,
        reasons=(),
        risks=(),
    )


def replay(
    forward: tuple[PreBreakoutForwardPerformance, ...],
    *,
    accepted: bool = True,
    late_entry: bool = False,
) -> PreBreakoutReplayResult:
    return PreBreakoutReplayResult(
        symbol="TEST.IS",
        cutoff_date=date(2026, 7, 1),
        analysis=analysis(accepted=accepted, late_entry=late_entry),
        entry_close=100.0,
        forward=forward,
    )


def metric(
    horizon: int,
    close: float,
    maximum: float,
    minimum: float,
) -> PreBreakoutForwardPerformance:
    return PreBreakoutForwardPerformance(
        horizon=horizon,
        close_return_pct=close,
        max_return_pct=maximum,
        min_return_pct=minimum,
        available=True,
    )


def test_tuprs_benzeri_guclu_hareket_basarili_etiketi_alir() -> None:
    result = replay(
        (
            metric(5, 8.55, 9.50, -0.55),
            metric(10, 21.14, 23.00, -0.55),
            metric(20, 21.88, 35.53, -0.55),
        )
    )
    assert performans_etiketi_belirle(result) == PreBreakoutPerformanceLabel.BASARILI


def test_thyao_benzeri_kisa_hareket_sinirli_etiketi_alir() -> None:
    result = replay(
        (
            metric(5, 1.07, 8.22, -2.00),
            metric(10, 0.46, 8.22, -3.00),
            metric(20, -6.16, 8.22, -7.00),
        )
    )
    assert performans_etiketi_belirle(result) == PreBreakoutPerformanceLabel.SINIRLI_HAREKET


def test_sahol_benzeri_aday_yanlis_pozitif_etiketi_alir() -> None:
    result = replay(
        (
            metric(5, -8.26, 1.02, -8.77),
            metric(10, -7.95, 1.02, -9.63),
            metric(20, -16.11, 1.02, -16.31),
        )
    )
    assert performans_etiketi_belirle(result) == PreBreakoutPerformanceLabel.YANLIS_POZITIF


def test_gec_giris_ayri_etiketlenir() -> None:
    result = replay(
        (metric(5, 4.0, 7.0, -1.0),),
        late_entry=True,
    )
    assert performans_etiketi_belirle(result) == PreBreakoutPerformanceLabel.GEC_GIRIS

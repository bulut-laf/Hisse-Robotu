from backend.app.prebreakout.prebreakout_calibration import (
    PreBreakoutCalibrationRow,
    guvenilir_asama_satirlarini_sec,
    kalibrasyon_ozetini_hesapla,
)


def row(
    stage: str,
    *,
    candidates: int,
    measured: int,
    success_rate: float,
) -> PreBreakoutCalibrationRow:
    return PreBreakoutCalibrationRow(
        stage=stage,
        candidate_count=candidates,
        measured_count=measured,
        successful_count=round(measured * success_rate / 100),
        limited_count=0,
        false_positive_count=0,
        success_rate_pct=success_rate,
        average_close_return_5d_pct=None,
        average_close_return_10d_pct=None,
        average_close_return_20d_pct=None,
        average_max_return_5d_pct=None,
        average_max_return_10d_pct=None,
        average_max_return_20d_pct=None,
        average_min_return_5d_pct=None,
        average_min_return_10d_pct=None,
        average_min_return_20d_pct=None,
    )


def test_olcum_kapsami_toplam_aday_uzerinden_hesaplanir() -> None:
    summary = kalibrasyon_ozetini_hesapla(
        (
            row("E2", candidates=4, measured=3, success_rate=50.0),
            row("E3", candidates=6, measured=5, success_rate=60.0),
        ),
        minimum_sample_size=3,
    )

    assert summary.candidate_count == 10
    assert summary.measured_count == 8
    assert summary.measurement_coverage_pct == 80.0


def test_en_iyi_asama_yalnizca_yeterli_orneklemden_secilir() -> None:
    summary = kalibrasyon_ozetini_hesapla(
        (
            row("E2", candidates=2, measured=2, success_rate=100.0),
            row("E3", candidates=5, measured=5, success_rate=60.0),
        ),
        minimum_sample_size=3,
    )

    assert summary.best_stage == "E3"
    assert summary.best_stage_success_rate_pct == 60.0
    assert summary.reliable_stage_count == 1


def test_esit_basarida_daha_fazla_olculen_asama_onceliklidir() -> None:
    summary = kalibrasyon_ozetini_hesapla(
        (
            row("E2", candidates=3, measured=3, success_rate=50.0),
            row("E3", candidates=6, measured=6, success_rate=50.0),
        ),
        minimum_sample_size=3,
    )

    assert summary.best_stage == "E3"


def test_yetersiz_orneklemde_en_iyi_asama_uretilmez() -> None:
    summary = kalibrasyon_ozetini_hesapla(
        (row("E3", candidates=2, measured=2, success_rate=100.0),),
        minimum_sample_size=3,
    )

    assert summary.best_stage is None
    assert summary.sufficient_sample is False
    assert "örneklem yetersiz" in summary.note


def test_olcum_yokken_acik_uyari_uretilir() -> None:
    summary = kalibrasyon_ozetini_hesapla(
        (row("E1", candidates=4, measured=0, success_rate=0.0),),
        minimum_sample_size=3,
    )

    assert summary.measurement_coverage_pct == 0.0
    assert "ölçülemedi" in summary.note


def test_guvenilir_asama_filtresi_minimum_olcumu_uygular() -> None:
    selected = guvenilir_asama_satirlarini_sec(
        (
            row("E1", candidates=2, measured=1, success_rate=0.0),
            row("E2", candidates=4, measured=3, success_rate=50.0),
            row("E3", candidates=6, measured=5, success_rate=60.0),
        ),
        minimum_sample_size=3,
    )

    assert [item.stage for item in selected] == ["E2", "E3"]


def test_minimum_orneklem_birden_kucuk_olamaz() -> None:
    try:
        kalibrasyon_ozetini_hesapla((), minimum_sample_size=0)
    except ValueError as error:
        assert "en az 1" in str(error)
    else:
        raise AssertionError("ValueError bekleniyordu")

from backend.app.prebreakout.prebreakout_calibration import PreBreakoutThresholdValidationRow
from backend.app.prebreakout.prebreakout_release_readiness import (
    on_yukselis_surum_hazirligini_degerlendir,
    surum_hazirligini_tabloya_cevir,
)
from backend.app.prebreakout.prebreakout_threshold_policy import (
    PreBreakoutThresholdPolicy,
    mevcut_esik_politikasi,
)


def _validation(verdict: str = "Kontrollü uygulama adayı") -> PreBreakoutThresholdValidationRow:
    return PreBreakoutThresholdValidationRow(
        stage="E3",
        current_minimum_momentum_score=10,
        proposed_minimum_momentum_score=12,
        baseline_measured_count=10,
        baseline_success_rate_pct=50.0,
        candidate_measured_count=8,
        candidate_success_rate_pct=62.5,
        success_rate_delta_pct=12.5,
        candidate_confidence_low_pct=30.0,
        sample_retention_pct=80.0,
        verdict=verdict,
        auto_apply=False,
    )


def test_kapali_politika_guvenli_varsayilanla_hazirdir() -> None:
    report = on_yukselis_surum_hazirligini_degerlendir([], mevcut_esik_politikasi())
    assert report.ready
    assert report.rollback_ready
    assert not report.production_policy_enabled


def test_etkin_politika_dogrulanmis_asama_ister() -> None:
    policy = PreBreakoutThresholdPolicy(
        enabled=True,
        stage_minimum_momentum_scores={"E3": 12},
        source="test",
    )
    report = on_yukselis_surum_hazirligini_degerlendir([_validation()], policy)
    assert report.ready
    assert report.accepted_stage_count == 1


def test_etkin_politika_dogrulama_yoksa_hazir_degildir() -> None:
    policy = PreBreakoutThresholdPolicy(
        enabled=True,
        stage_minimum_momentum_scores={"E3": 12},
        source="test",
    )
    report = on_yukselis_surum_hazirligini_degerlendir([], policy)
    assert not report.ready


def test_sizinti_korumasinda_basarisizlik_surumu_kilitler() -> None:
    report = on_yukselis_surum_hazirligini_degerlendir(
        [_validation()], mevcut_esik_politikasi(), leakage_guard_confirmed=False
    )
    assert report.status == "Kullanıma hazır değil"


def test_hazirlik_tablosu_tum_kontrolleri_icerir() -> None:
    report = on_yukselis_surum_hazirligini_degerlendir([], mevcut_esik_politikasi())
    table = surum_hazirligini_tabloya_cevir(report)
    assert list(table.columns) == ["Kontrol", "Sonuç"]
    assert len(table) == 5

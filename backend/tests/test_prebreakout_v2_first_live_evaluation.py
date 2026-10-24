from backend.app.prebreakout.prebreakout_v2_sample_adequacy import (
    SampleReadiness,
    SampleAdequacyStatus,
)
from backend.app.prebreakout.prebreakout_v2_first_live_evaluation import (
    FirstLiveEvaluationPolicy,
    ModelDecision,
    ilk_gercek_kullanim_degerlendirmesini_yap,
    ilk_gercek_kullanim_raporunu_metne_cevir,
)


def _sample(ready=True):
    return SampleAdequacyStatus(
        observation_days=30 if ready else 10,
        measured_candidate_count=60 if ready else 10,
        mature_20d_candidate_count=30 if ready else 2,
        reliable_regime_group_count=2 if ready else 1,
        covered_stage_count=3 if ready else 2,
        readiness=(
            SampleReadiness.ILK_DEGERLENDIRMEYE_HAZIR
            if ready
            else SampleReadiness.IZLEMEYE_DEVAM
        ),
        first_evaluation_ready=ready,
        completion_ratio=1.0 if ready else 0.4,
        missing_conditions=() if ready else ("Eksik",),
        summary="",
    )


def test_orneklem_yetersizse_model_korunur():
    report = ilk_gercek_kullanim_degerlendirmesini_yap(
        sample_status=_sample(False),
        measured_candidate_count=10,
        mature_20d_candidate_count=2,
        success_rate_pct=80,
        false_positive_rate_pct=5,
        average_trigger_sessions=2,
        portfolio_return_pct=10,
        max_drawdown_pct=3,
    )
    assert report.sample_ready is False
    assert report.model_decision is ModelDecision.MODELI_KORU


def test_tum_olcutler_iyiyse_model_korunur():
    report = ilk_gercek_kullanim_degerlendirmesini_yap(
        sample_status=_sample(True),
        measured_candidate_count=60,
        mature_20d_candidate_count=30,
        success_rate_pct=55,
        false_positive_rate_pct=30,
        average_trigger_sessions=5,
        portfolio_return_pct=4,
        max_drawdown_pct=8,
    )
    assert report.model_decision is ModelDecision.MODELI_KORU
    assert any("kabul sınırları" in r for r in report.reasons)


def test_bir_zayif_olcut_inceleme_uretir():
    report = ilk_gercek_kullanim_degerlendirmesini_yap(
        sample_status=_sample(True),
        measured_candidate_count=60,
        mature_20d_candidate_count=30,
        success_rate_pct=40,
        false_positive_rate_pct=30,
        average_trigger_sessions=5,
        portfolio_return_pct=4,
        max_drawdown_pct=8,
    )
    assert report.model_decision is ModelDecision.INCELE


def test_iki_zayif_olcut_hala_inceleme():
    report = ilk_gercek_kullanim_degerlendirmesini_yap(
        sample_status=_sample(True),
        measured_candidate_count=60,
        mature_20d_candidate_count=30,
        success_rate_pct=40,
        false_positive_rate_pct=50,
        average_trigger_sessions=5,
        portfolio_return_pct=4,
        max_drawdown_pct=8,
    )
    assert report.model_decision is ModelDecision.INCELE


def test_uc_zayif_olcut_kalibrasyon_adayi():
    report = ilk_gercek_kullanim_degerlendirmesini_yap(
        sample_status=_sample(True),
        measured_candidate_count=60,
        mature_20d_candidate_count=30,
        success_rate_pct=40,
        false_positive_rate_pct=50,
        average_trigger_sessions=9,
        portfolio_return_pct=4,
        max_drawdown_pct=8,
    )
    assert report.model_decision is ModelDecision.KALIBRASYON_ADAYI


def test_olculemeyen_metrikler_zayif_sayilir():
    report = ilk_gercek_kullanim_degerlendirmesini_yap(
        sample_status=_sample(True),
        measured_candidate_count=60,
        mature_20d_candidate_count=30,
        success_rate_pct=None,
        false_positive_rate_pct=None,
        average_trigger_sessions=None,
        portfolio_return_pct=4,
        max_drawdown_pct=8,
    )
    assert report.model_decision is ModelDecision.KALIBRASYON_ADAYI


def test_ozel_politika_desteklenir():
    policy = FirstLiveEvaluationPolicy(
        minimum_success_rate_pct=30,
        maximum_false_positive_rate_pct=60,
        maximum_average_trigger_sessions=10,
        maximum_drawdown_pct=20,
        minimum_portfolio_return_pct=-5,
    )
    report = ilk_gercek_kullanim_degerlendirmesini_yap(
        sample_status=_sample(True),
        measured_candidate_count=60,
        mature_20d_candidate_count=30,
        success_rate_pct=35,
        false_positive_rate_pct=55,
        average_trigger_sessions=9,
        portfolio_return_pct=-2,
        max_drawdown_pct=18,
        policy=policy,
    )
    assert report.model_decision is ModelDecision.MODELI_KORU


def test_metin_karari_ve_metrikleri_icerir():
    report = ilk_gercek_kullanim_degerlendirmesini_yap(
        sample_status=_sample(True),
        measured_candidate_count=70,
        mature_20d_candidate_count=40,
        success_rate_pct=52.5,
        false_positive_rate_pct=32.5,
        average_trigger_sessions=4.5,
        portfolio_return_pct=6.2,
        max_drawdown_pct=7.1,
    )
    text = ilk_gercek_kullanim_raporunu_metne_cevir(report)
    assert "V2 İLK GERÇEK KULLANIM DEĞERLENDİRMESİ" in text
    assert "Karar: Modeli koru" in text
    assert "Başarı oranı: 52.50%" in text
    assert "Maksimum düşüş: 7.10%" in text

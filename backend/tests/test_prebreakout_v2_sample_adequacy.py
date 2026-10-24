from backend.app.prebreakout.prebreakout_v2_observation import (
    v2_gozlem_durumunu_degerlendir,
)
from backend.app.prebreakout.prebreakout_v2_sample_adequacy import (
    SampleAdequacyPolicy,
    SampleReadiness,
    canli_orneklem_yeterliligini_degerlendir,
    orneklem_yeterliligini_metne_cevir,
    v2_gozlemden_orneklem_yeterliligi,
)


def test_yetersiz_orneklemde_izlemeye_devam():
    status = canli_orneklem_yeterliligini_degerlendir(
        observation_days=10,
        measured_candidate_count=12,
        mature_20d_candidate_count=2,
        reliable_regime_group_count=1,
        covered_stage_count=2,
    )
    assert status.first_evaluation_ready is False
    assert status.readiness is SampleReadiness.IZLEMEYE_DEVAM
    assert status.missing_conditions


def test_esige_yaklasinca_on_degerlendirme():
    status = canli_orneklem_yeterliligini_degerlendir(
        observation_days=28,
        measured_candidate_count=55,
        mature_20d_candidate_count=25,
        reliable_regime_group_count=2,
        covered_stage_count=3,
    )
    assert status.first_evaluation_ready is False
    assert status.readiness is SampleReadiness.ON_DEGERLENDIRME
    assert 0.75 <= status.completion_ratio < 1.0


def test_tum_kosullar_saglaninca_ilk_degerlendirmeye_hazir():
    status = canli_orneklem_yeterliligini_degerlendir(
        observation_days=30,
        measured_candidate_count=60,
        mature_20d_candidate_count=30,
        reliable_regime_group_count=2,
        covered_stage_count=3,
    )
    assert status.first_evaluation_ready is True
    assert status.readiness is SampleReadiness.ILK_DEGERLENDIRMEYE_HAZIR
    assert status.completion_ratio == 1.0
    assert not status.missing_conditions


def test_teknik_saglik_yoksa_hazir_olamaz():
    status = canli_orneklem_yeterliligini_degerlendir(
        observation_days=60,
        measured_candidate_count=100,
        mature_20d_candidate_count=70,
        reliable_regime_group_count=3,
        covered_stage_count=3,
        technical_ready=False,
    )
    assert status.first_evaluation_ready is False
    assert any("Teknik sağlık" in x for x in status.missing_conditions)


def test_20_gunluk_olgun_sonuc_ayri_kosuldur():
    status = canli_orneklem_yeterliligini_degerlendir(
        observation_days=40,
        measured_candidate_count=80,
        mature_20d_candidate_count=29,
        reliable_regime_group_count=3,
        covered_stage_count=3,
    )
    assert status.first_evaluation_ready is False
    assert any("20 günlük" in x for x in status.missing_conditions)


def test_e2_e4_kapsamasi_eksikse_hazir_degil():
    status = canli_orneklem_yeterliligini_degerlendir(
        observation_days=40,
        measured_candidate_count=80,
        mature_20d_candidate_count=40,
        reliable_regime_group_count=3,
        covered_stage_count=2,
    )
    assert status.first_evaluation_ready is False
    assert any("E2-E4" in x for x in status.missing_conditions)


def test_sprint119_durumu_sprint120ye_tasinir():
    observation = v2_gozlem_durumunu_degerlendir(
        observation_days=35,
        measured_candidate_count=65,
        reliable_regime_group_count=2,
    )
    status = v2_gozlemden_orneklem_yeterliligi(
        observation,
        mature_20d_candidate_count=35,
        covered_stage_count=3,
    )
    assert status.first_evaluation_ready is True


def test_ozel_politika_desteklenir():
    policy = SampleAdequacyPolicy(
        minimum_observation_days=5,
        minimum_measured_candidates=10,
        minimum_mature_20d_candidates=5,
        minimum_reliable_regime_groups=1,
        minimum_stage_coverage=2,
    )
    status = canli_orneklem_yeterliligini_degerlendir(
        observation_days=5,
        measured_candidate_count=10,
        mature_20d_candidate_count=5,
        reliable_regime_group_count=1,
        covered_stage_count=2,
        policy=policy,
    )
    assert status.first_evaluation_ready is True


def test_metin_ilk_degerlendirme_esigini_acikca_yazar():
    status = canli_orneklem_yeterliligini_degerlendir(
        observation_days=30,
        measured_candidate_count=60,
        mature_20d_candidate_count=30,
        reliable_regime_group_count=2,
        covered_stage_count=3,
    )
    text = orneklem_yeterliligini_metne_cevir(status)
    assert "V2 CANLI GÖZLEM - ÖRNEKLEM YETERLİLİĞİ" in text
    assert "İlk değerlendirmeye hazır: EVET" in text
    assert "20 günlük olgun sonuç: 30" in text

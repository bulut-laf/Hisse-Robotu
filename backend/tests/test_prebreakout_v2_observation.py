from backend.app.prebreakout.prebreakout_v2_observation import (
    ObservationDecision,
    ObservationPolicy,
    v2_gozlem_durumunu_degerlendir,
    v2_gozlem_durumunu_metne_cevir,
)


def test_yetersiz_orneklemde_veri_biriktirilir():
    status = v2_gozlem_durumunu_degerlendir(
        observation_days=7,
        measured_candidate_count=8,
        reliable_regime_group_count=1,
    )
    assert status.evidence_ready is False
    assert status.decision is ObservationDecision.VERI_BIRIKTIR
    assert status.model_change_allowed is False
    assert status.remaining_candidate_count == 22
    assert status.remaining_observation_days == 13


def test_yeterli_kanitta_degerlendirmeye_hazirdir():
    status = v2_gozlem_durumunu_degerlendir(
        observation_days=25,
        measured_candidate_count=40,
        reliable_regime_group_count=3,
    )
    assert status.evidence_ready is True
    assert status.decision is ObservationDecision.DEGERLENDIRMEYE_HAZIR
    assert status.model_change_allowed is False
    assert not status.warnings


def test_teknik_saglik_yoksa_model_degisikligi_dondurulur():
    status = v2_gozlem_durumunu_degerlendir(
        observation_days=30,
        measured_candidate_count=50,
        reliable_regime_group_count=3,
        technical_ready=False,
    )
    assert status.evidence_ready is False
    assert status.decision is ObservationDecision.MODEL_DEGISIKLIGINI_DONDUR
    assert any("teknik" in item.lower() for item in status.warnings)


def test_negatif_sayilar_sifira_sabitlenir():
    status = v2_gozlem_durumunu_degerlendir(
        observation_days=-1,
        measured_candidate_count=-10,
        reliable_regime_group_count=-2,
    )
    assert status.observation_days == 0
    assert status.measured_candidate_count == 0
    assert status.reliable_regime_group_count == 0


def test_ozel_politika_desteklenir():
    policy = ObservationPolicy(
        minimum_measured_candidates=10,
        minimum_reliable_regime_groups=1,
        minimum_observation_days=5,
    )
    status = v2_gozlem_durumunu_degerlendir(
        observation_days=5,
        measured_candidate_count=10,
        reliable_regime_group_count=1,
        policy=policy,
    )
    assert status.evidence_ready is True


def test_metinsel_ozet_model_dondurmayi_acikca_yazar():
    status = v2_gozlem_durumunu_degerlendir(
        observation_days=7,
        measured_candidate_count=8,
        reliable_regime_group_count=1,
    )
    text = v2_gozlem_durumunu_metne_cevir(status)
    assert "GERÇEK KULLANIM V2 - CANLI GÖZLEM DURUMU" in text
    assert "Model değişikliği: DONDURULDU" in text
    assert "Kalan ölçülmüş aday: 22" in text


def test_evidence_ready_icin_tum_kosullar_gerekir():
    cases = [
        dict(observation_days=19, measured_candidate_count=30, reliable_regime_group_count=2),
        dict(observation_days=20, measured_candidate_count=29, reliable_regime_group_count=2),
        dict(observation_days=20, measured_candidate_count=30, reliable_regime_group_count=1),
    ]
    for kwargs in cases:
        status = v2_gozlem_durumunu_degerlendir(**kwargs)
        assert status.evidence_ready is False
        assert status.decision is ObservationDecision.VERI_BIRIKTIR

from backend.app.prebreakout.prebreakout_v2_first_live_evaluation import ModelDecision
from backend.app.prebreakout.prebreakout_v2_decision_stability import (
    DecisionSnapshot,
    DecisionStability,
    karar_istikrarini_degerlendir,
    karar_istikrar_raporunu_metne_cevir,
)


def _s(day, decision):
    return DecisionSnapshot(
        observation_day=day,
        decision=decision,
        success_rate_pct=50,
        false_positive_rate_pct=30,
        portfolio_return_pct=3,
    )


def test_gecmis_yoksa_yetersiz():
    report = karar_istikrarini_degerlendir([])
    assert report.stability is DecisionStability.YETERSIZ_GECMIS
    assert report.model_change_allowed is False


def test_uc_kez_modeli_koru_kararli():
    report = karar_istikrarini_degerlendir([
        _s(1, ModelDecision.MODELI_KORU),
        _s(2, ModelDecision.MODELI_KORU),
        _s(3, ModelDecision.MODELI_KORU),
    ])
    assert report.stability is DecisionStability.KARARLI
    assert report.model_change_allowed is False


def test_kararlar_dalgaliysa_model_degismez():
    report = karar_istikrarini_degerlendir([
        _s(1, ModelDecision.MODELI_KORU),
        _s(2, ModelDecision.INCELE),
        _s(3, ModelDecision.MODELI_KORU),
        _s(4, ModelDecision.KALIBRASYON_ADAYI),
    ])
    assert report.stability is DecisionStability.DALGALI
    assert report.model_change_allowed is False


def test_kalibrasyon_adayi_kararliysa_degerlendirilebilir():
    report = karar_istikrarini_degerlendir([
        _s(1, ModelDecision.KALIBRASYON_ADAYI),
        _s(2, ModelDecision.KALIBRASYON_ADAYI),
        _s(3, ModelDecision.KALIBRASYON_ADAYI),
    ])
    assert report.stability is DecisionStability.BOZULUYOR
    assert report.model_change_allowed is True


def test_son_pencerede_bozulma_yakalanir():
    report = karar_istikrarini_degerlendir([
        _s(1, ModelDecision.MODELI_KORU),
        _s(2, ModelDecision.MODELI_KORU),
        _s(3, ModelDecision.INCELE),
        _s(4, ModelDecision.KALIBRASYON_ADAYI),
        _s(5, ModelDecision.KALIBRASYON_ADAYI),
    ])
    assert report.stability is DecisionStability.BOZULUYOR
    assert report.model_change_allowed is True


def test_iki_snapshot_yetersiz():
    report = karar_istikrarini_degerlendir([
        _s(1, ModelDecision.INCELE),
        _s(2, ModelDecision.INCELE),
    ])
    assert report.stability is DecisionStability.YETERSIZ_GECMIS


def test_karar_degisim_sayisi_hesaplanir():
    report = karar_istikrarini_degerlendir([
        _s(1, ModelDecision.MODELI_KORU),
        _s(2, ModelDecision.INCELE),
        _s(3, ModelDecision.MODELI_KORU),
        _s(4, ModelDecision.MODELI_KORU),
    ])
    assert report.decision_changes == 2


def test_metin_raporu_karari_ve_istikrari_icerir():
    report = karar_istikrarini_degerlendir([
        _s(1, ModelDecision.MODELI_KORU),
        _s(2, ModelDecision.MODELI_KORU),
        _s(3, ModelDecision.MODELI_KORU),
    ])
    text = karar_istikrar_raporunu_metne_cevir(report)
    assert "V2 GERÇEK KULLANIM - KARAR İSTİKRARI" in text
    assert "İstikrar: Kararlı" in text
    assert "Model değişikliği değerlendirilebilir: HAYIR" in text

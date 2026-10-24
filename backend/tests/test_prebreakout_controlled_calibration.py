import pytest

from backend.app.prebreakout.prebreakout_controlled_calibration import (
    RegimeCalibrationSample,
    ThresholdCalibrationScenario,
    kalibrasyon_degerlendirme_tablosu,
    kontrollu_esik_kalibrasyonunu_degerlendir,
)


def _scenario(
    name: str,
    *,
    sample: int = 100,
    success: int = 55,
    fp: int = 25,
    missed: int = 10,
    regimes: tuple[RegimeCalibrationSample, ...] | None = None,
):
    if regimes is None:
        regimes = (
            RegimeCalibrationSample("Yükselen", 40, 24),
            RegimeCalibrationSample("Yatay", 35, 18),
            RegimeCalibrationSample("Zayıf", 25, 13),
        )
    return ThresholdCalibrationScenario(
        name=name,
        momentum_min=10.0,
        require_positive_rsi_slope=True,
        require_positive_macd_histogram_slope=True,
        sample_count=sample,
        successful_count=success,
        false_positive_count=fp,
        missed_opportunity_count=missed,
        regimes=regimes,
    )


def test_guclu_aday_kontrollu_kapilari_gecer():
    baseline = _scenario("Mevcut")
    candidate = _scenario(
        "Kalibre-1",
        sample=90,
        success=56,
        fp=17,
        missed=11,
        regimes=(
            RegimeCalibrationSample("Yükselen", 35, 23),
            RegimeCalibrationSample("Yatay", 30, 18),
            RegimeCalibrationSample("Zayıf", 25, 15),
        ),
    )
    report = kontrollu_esik_kalibrasyonunu_degerlendir(baseline, (candidate,))
    assert report.recommended_scenario_name == "Kalibre-1"
    assert report.keep_baseline is False
    assert report.automatic_apply_allowed is False


def test_kucuk_orneklem_yuksek_basariya_ragmen_reddedilir():
    baseline = _scenario("Mevcut")
    candidate = _scenario("Aşırı uyum", sample=20, success=18, fp=1)
    report = kontrollu_esik_kalibrasyonunu_degerlendir(baseline, (candidate,))
    row = report.rows[0]
    assert row.eligible is False
    assert "Toplam örneklem yetersiz" in row.rejection_reasons
    assert "Örneklem kaybı fazla" in row.rejection_reasons


def test_rejim_cesitliligi_yetersizse_aday_reddedilir():
    baseline = _scenario("Mevcut")
    candidate = _scenario(
        "Tek rejim",
        sample=80,
        success=52,
        fp=15,
        regimes=(RegimeCalibrationSample("Yükselen", 80, 52),),
    )
    report = kontrollu_esik_kalibrasyonunu_degerlendir(baseline, (candidate,))
    assert "Rejim çeşitliliği yetersiz" in report.rows[0].rejection_reasons


def test_en_zayif_rejim_fazla_bozulursa_aday_reddedilir():
    baseline = _scenario("Mevcut")
    candidate = _scenario(
        "Rejim bozulması",
        sample=90,
        success=58,
        fp=15,
        regimes=(
            RegimeCalibrationSample("Yükselen", 40, 30),
            RegimeCalibrationSample("Yatay", 30, 20),
            RegimeCalibrationSample("Zayıf", 20, 8),
        ),
    )
    report = kontrollu_esik_kalibrasyonunu_degerlendir(baseline, (candidate,))
    assert "En zayıf rejimde bozulma fazla" in report.rows[0].rejection_reasons


def test_yanlis_pozitif_kotulesirse_basari_artsa_da_reddedilir():
    baseline = _scenario("Mevcut")
    candidate = _scenario("FP kötü", sample=100, success=62, fp=30)
    report = kontrollu_esik_kalibrasyonunu_degerlendir(baseline, (candidate,))
    assert "Yanlış pozitif oranı kötüleşiyor" in report.rows[0].rejection_reasons


def test_hicbir_aday_gecmezse_mevcut_esikler_korunur():
    baseline = _scenario("Mevcut")
    candidate = _scenario("Zayıf aday", sample=95, success=53, fp=24)
    report = kontrollu_esik_kalibrasyonunu_degerlendir(baseline, (candidate,))
    assert report.keep_baseline is True
    assert report.recommended_scenario_name is None
    assert "mevcut eşikler korunmalı" in report.note


def test_birden_fazla_uygun_adayda_en_guclu_skor_secilir():
    baseline = _scenario("Mevcut")
    a = _scenario("A", sample=90, success=55, fp=18, missed=11)
    b = _scenario("B", sample=92, success=59, fp=16, missed=11)
    report = kontrollu_esik_kalibrasyonunu_degerlendir(baseline, (a, b))
    assert report.recommended_scenario_name == "B"


def test_degerlendirme_tablosu_karar_alanlarini_icerir():
    baseline = _scenario("Mevcut")
    candidate = _scenario("A", sample=90, success=56, fp=17)
    report = kontrollu_esik_kalibrasyonunu_degerlendir(baseline, (candidate,))
    table = kalibrasyon_degerlendirme_tablosu(report)
    assert {"Senaryo", "Başarı farkı (puan)", "Örneklem korunumu (%)", "Uygun aday", "Red nedenleri"} <= set(table[0])


def test_gecersiz_senaryo_sayimlari_reddedilir():
    baseline = _scenario("Mevcut")
    bad = _scenario("Bozuk", sample=10, success=11)
    with pytest.raises(ValueError):
        kontrollu_esik_kalibrasyonunu_degerlendir(baseline, (bad,))


@pytest.mark.parametrize(
    "kwargs",
    [
        {"minimum_total_sample": 0},
        {"minimum_regime_sample": 0},
        {"minimum_reliable_regime_count": 0},
        {"minimum_sample_retention_pct": 0},
        {"minimum_sample_retention_pct": 101},
        {"minimum_success_improvement_pp": -1},
        {"maximum_false_positive_increase_pp": -1},
        {"maximum_worst_regime_degradation_pp": -1},
    ],
)
def test_gecersiz_kalibrasyon_parametreleri_reddedilir(kwargs):
    with pytest.raises(ValueError):
        kontrollu_esik_kalibrasyonunu_degerlendir(_scenario("Mevcut"), (), **kwargs)

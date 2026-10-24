from dataclasses import dataclass

from backend.app.prebreakout.prebreakout_v2_closure import (
    EvidenceLevel,
    V2Decision,
    gercek_kullanim_v2_kapanisini_degerlendir,
    v2_kapanis_raporunu_metne_cevir,
)


@dataclass
class Quality:
    measured_count: int = 30
    sufficient_sample: bool = True
    success_rate_pct: float | None = 60.0
    false_positive_rate_pct: float | None = 20.0
    early_trigger_rate_pct: float | None = 55.0
    average_trigger_session: float | None = 2.4


@dataclass
class ReasonRow:
    too_strict: bool = False


@dataclass
class Missed:
    missed_opportunity_count: int = 4
    reason_rows: tuple = ()


@dataclass
class RegimeValue:
    value: str = "Yükselen"


@dataclass
class Regime:
    sufficient_group_count: int = 3
    best_reliable_regime: object = None
    best_reliable_stage: str | None = "E3"

    def __post_init__(self):
        if self.best_reliable_regime is None:
            self.best_reliable_regime = RegimeValue()


@dataclass
class Calibration:
    recommended_scenario_name: str | None = None
    automatic_apply_allowed: bool = False


def test_yeterli_kanitta_mevcut_esikler_korunabilir():
    report = gercek_kullanim_v2_kapanisini_degerlendir(Quality(), Missed(), Regime(), Calibration())
    assert report.technical_ready is True
    assert report.evidence_level is EvidenceLevel.YETERLI
    assert report.decision is V2Decision.MEVCUT_ESIKLERI_KORU
    assert report.automatic_apply_allowed is False


def test_kalibrasyon_adayi_otomatik_uygulanmaz():
    report = gercek_kullanim_v2_kapanisini_degerlendir(Quality(), Missed(), Regime(), Calibration("Kalibre-2"))
    assert report.decision is V2Decision.KALIBRASYON_ADAYINI_INCELE
    assert report.calibration_candidate == "Kalibre-2"
    assert report.automatic_apply_allowed is False
    assert "otomatik uygulanmaz" in report.executive_summary


def test_yetersiz_orneklemde_gozleme_devam_edilir():
    quality = Quality(measured_count=0, sufficient_sample=False, success_rate_pct=None)
    regime = Regime(sufficient_group_count=0, best_reliable_regime=None, best_reliable_stage=None)
    regime.best_reliable_regime = None
    report = gercek_kullanim_v2_kapanisini_degerlendir(quality, Missed(), regime, Calibration("Aday"))
    assert report.evidence_level is EvidenceLevel.YETERSIZ
    assert report.decision is V2Decision.GOZLEME_DEVAM
    assert len(report.warnings) >= 2


def test_gelisen_kanitta_esik_degisikligi_onerilmez():
    quality = Quality(measured_count=10, sufficient_sample=False)
    regime = Regime(sufficient_group_count=1)
    report = gercek_kullanim_v2_kapanisini_degerlendir(quality, Missed(), regime, Calibration("Aday"))
    assert report.evidence_level is EvidenceLevel.GELISIYOR
    assert report.decision is V2Decision.GOZLEME_DEVAM


def test_fazla_kati_filtreler_uyariya_doner():
    missed = Missed(reason_rows=(ReasonRow(True), ReasonRow(False), ReasonRow(True)))
    report = gercek_kullanim_v2_kapanisini_degerlendir(Quality(), missed, Regime(), Calibration())
    assert report.too_strict_filter_count == 2
    assert any("fazla katı" in item for item in report.warnings)


def test_rejim_lideri_rapora_tasinir():
    report = gercek_kullanim_v2_kapanisini_degerlendir(Quality(), Missed(), Regime(), Calibration())
    assert report.best_reliable_regime == "Yükselen"
    assert report.best_reliable_stage == "E3"


def test_final_metin_temel_metrikleri_icerir():
    report = gercek_kullanim_v2_kapanisini_degerlendir(Quality(), Missed(), Regime(), Calibration())
    text = v2_kapanis_raporunu_metne_cevir(report)
    assert "GERÇEK KULLANIM V2 - FINAL PERFORMANS RAPORU" in text
    assert "Teknik hazır: EVET" in text
    assert "Başarı oranı (%)" in text
    assert "Yanlış pozitif (%)" in text
    assert "Otomatik eşik uygulama: HAYIR" in text


def test_olculemeyen_degerler_metinde_acik_yazilir():
    quality = Quality(success_rate_pct=None, false_positive_rate_pct=None, early_trigger_rate_pct=None, average_trigger_session=None)
    report = gercek_kullanim_v2_kapanisini_degerlendir(quality, Missed(), Regime(), Calibration())
    text = v2_kapanis_raporunu_metne_cevir(report)
    assert text.count("Ölçülemiyor") >= 4


def test_kalibrasyon_otomatik_izin_verse_bile_v2_engeller():
    report = gercek_kullanim_v2_kapanisini_degerlendir(Quality(), Missed(), Regime(), Calibration("Aday", True))
    assert report.automatic_apply_allowed is False
    assert any("güvenlik nedeniyle engeller" in item for item in report.warnings)

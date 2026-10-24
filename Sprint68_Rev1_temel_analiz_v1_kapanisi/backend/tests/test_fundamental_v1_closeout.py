from __future__ import annotations

import ast
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DASHBOARD = ROOT / "backend" / "dashboard.py"
APP = ROOT / "backend" / "app"


def source(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def test_temel_analiz_v1_modulleri_mevcuttur():
    expected = (
        APP / "models" / "fundamental_models.py",
        APP / "data" / "fundamental_data.py",
        APP / "data" / "fundamental_store.py",
        APP / "data" / "fundamental_score_store.py",
        APP / "data" / "fundamental_settings.py",
        APP / "analysis" / "fundamental_analysis.py",
        APP / "analysis" / "fundamental_quality.py",
        APP / "analysis" / "fundamental_score_history.py",
        APP / "analysis" / "sector_reference.py",
        APP / "analysis" / "sector_score_ranking.py",
        APP / "analysis" / "sector_strength_map.py",
        APP / "reporting" / "fundamental_report.py",
        APP / "reporting" / "fundamental_report_archive.py",
    )

    missing = [str(path) for path in expected if not path.exists()]

    assert missing == []


def test_temel_analiz_ekrani_tum_v1_bilesenlerini_icerir():
    text = source(DASHBOARD)

    expected = (
        "Temel Analiz ve Bilanço",
        "Temel analiz ayarları",
        "Temel kalite skoru",
        "Temel skor geçmişi",
        "Finansal oran ve sektör referansı",
        "Sektör bazlı temel skor sıralaması",
        "Sektör güç haritası",
        "Temel analiz özet raporu",
        "Temel analiz rapor arşivi",
        "Arşiv arama ve filtreleme",
    )

    for label in expected:
        assert label in text


def test_csv_pdf_ve_arsiv_disari_aktarim_zinciri_mevcuttur():
    text = source(DASHBOARD)

    expected = (
        "fundamental_report_csv_bytes",
        "fundamental_report_pdf_bytes",
        "archived_reports_csv_bytes",
        "archived_reports_pdf_bytes",
        "st.download_button",
    )

    for token in expected:
        assert token in text


def test_temel_analiz_tavsiye_uretmez():
    dashboard = source(DASHBOARD)
    report = source(
        APP / "reporting" / "fundamental_report.py"
    )

    assert "yatırım tavsiyesi değildir" in dashboard.lower()
    assert "alım/satım tavsiyesi" in dashboard
    assert "yatırım danışmanlığı" in report.lower()


def test_temel_filtre_varsayilan_kapalidir():
    text = source(DASHBOARD)

    assert "Temel kalite filtresini kullan" in text
    assert "value=False" in text


def test_vbts_guvenlik_zinciri_korunur():
    text = source(DASHBOARD)

    assert "VBTS" in text
    assert "vbts" in text.lower()
    assert "güvenlik" in text.lower() or "kilit" in text.lower()


def test_temel_ayarlar_yalnizca_temel_modulu_etkiler():
    text = source(DASHBOARD)

    assert "Bu ayarlar yalnızca temel analiz, sektör" in text
    assert "karşılaştırması ve temel rapor arşivini etkiler." in text


def test_dashboard_sozdizimi_gecerlidir():
    ast.parse(source(DASHBOARD))


def test_kapanis_belgeleri_mevcuttur():
    expected = (
        ROOT / "PROJECT_NOTES.md",
        ROOT / "KULLANIM_KILAVUZU.md",
        ROOT / "TEMEL_ANALIZ_V1_KAPANIS.md",
    )

    assert all(path.exists() for path in expected)


def test_snapshot_betigi_guvenli_dislamalar_icerir():
    script = source(
        ROOT / "Hazirla-Temel-Analiz-V1-Snapshot.ps1"
    )

    for token in (
        "__pycache__",
        ".pytest_cache",
        ".venv",
        "backend\\data",
        "SHA256",
        "RELEASE-TEMEL-ANALIZ-V1.json",
    ):
        assert token in script


def test_manifest_sablonu_v1_kapsamini_belirtir():
    manifest_path = ROOT / "TEMEL_ANALIZ_V1_MANIFEST.json"
    manifest = json.loads(source(manifest_path))

    assert manifest["module"] == "Temel Analiz"
    assert manifest["version"] == "V1"
    assert manifest["baseline_tests"] == 1023
    assert manifest["status"] == "VALIDATION_PENDING"

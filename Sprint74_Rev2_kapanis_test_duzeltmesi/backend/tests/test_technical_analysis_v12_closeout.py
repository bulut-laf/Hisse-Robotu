from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_teknik_analiz_v12_modulleri_mevcuttur():
    required = (
        "backend/app/analysis/divergence_analysis.py",
        "backend/app/analysis/technical_decision_matrix.py",
        "backend/app/analysis/signal_outcome_tracking.py",
        "backend/app/analysis/indicator_contribution.py",
        "backend/app/analysis/walk_forward_calibration.py",
    )

    for relative in required:
        assert (PROJECT_ROOT / relative).is_file(), relative


def test_project_notes_teknik_analiz_v12_kapsamini_icerir():
    text = (PROJECT_ROOT / "PROJECT_NOTES.md").read_text(
        encoding="utf-8-sig"
    )

    assert "Teknik Analiz V1.2" in text
    assert "Sprint-69–74" in text
    assert "walk-forward" in text.casefold()
    assert "Canlı veri, emir defteri ve scalping entegrasyonu" in text


def test_kullanim_kilavuzu_yeni_ekranlari_aciklar():
    text = (PROJECT_ROOT / "KULLANIM_KILAVUZU.md").read_text(
        encoding="utf-8-sig"
    )

    assert "RSI/MACD uyumsuzluk" in text
    assert "Günlük/Haftalık karar matrisi" in text
    assert "Sinyal sonuçları" in text
    assert "Gösterge katkısı" in text
    assert "Walk-forward doğrulama" in text


def test_kapanis_betigi_guvenlik_adimlarini_icerir():
    text = (PROJECT_ROOT / "Close-Teknik-Analiz-V1.2.ps1").read_text(
        encoding="utf-8-sig"
    )

    assert "-m pytest -q" in text
    assert "-m backend.run_system_check" in text
    assert "-m compileall backend -q" in text
    assert '$releaseName = "Hisse-Robotu-Teknik-Analiz-V1.2"' in text
    assert '$snapshot = Join-Path $releaseDir "$releaseName.zip"' in text
    assert "Get-FileHash" in text
    assert "RELEASE-TEKNIK-ANALIZ-V1.2.json" in text

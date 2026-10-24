from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_project_notes_v13_kapanisini_icerir():
    text = (ROOT / "PROJECT_NOTES.md").read_text(
        encoding="utf-8-sig"
    )

    assert "V1.3" in text
    assert "Sprint-75–81" in text
    assert "Gecikmeli Veri Pilotu" in text
    assert "Gölge Portföy" in text
    assert "Başarı Karşılaştırması" in text


def test_kullanim_kilavuzu_v13_ekranlarini_aciklar():
    text = (ROOT / "KULLANIM_KILAVUZU.md").read_text(
        encoding="utf-8-sig"
    )

    assert "V1.3 Kalibrasyon Kararı" in text
    assert "Haftalık Performans Raporu" in text
    assert "gerçek emir göndermez" in text.casefold()

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DASHBOARD = ROOT / "backend" / "dashboard.py"


def _source() -> str:
    return DASHBOARD.read_text(encoding="utf-8")


def test_alt_panel_dosya_yok_mesajini_sade_gosterir() -> None:
    source = _source()
    assert "VBTS CSV durumu: Dosya bulunamadı" in source
    assert "Beklenen konum:" in source


def test_alt_panel_ust_kart_hatasini_tekrar_etmez() -> None:
    source = _source()
    marker = "def manuel_vbts_durum_paneli_goster"
    start = source.find(marker)
    assert start >= 0
    next_def = source.find("\ndef ", start + len(marker))
    assert next_def >= 0
    section = source[start:next_def]
    assert 'st.error("VBTS CSV dosyası bulunamadı:' not in section
    assert "Manuel VBTS kaynağı kullanılamıyor" not in section


def test_ust_kart_vbts_hatasinda_taramayi_kilitlemez() -> None:
    source = _source()
    assert "Manuel VBTS kaynağı güncel/doğrulanmış değil" in source
    assert "Toplu tarama devam eder; yeni tedbirler eksik olabilir" in source
    assert "Manuel VBTS kaynağı kullanılamıyor — Toplu tarama kilitli." not in source

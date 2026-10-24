
from pathlib import Path


def _source() -> str:
    return Path("backend/dashboard.py").read_text(encoding="utf-8")


def test_vbts_management_panel_returns_operational_readiness() -> None:
    source = _source()
    assert "def vbts_yonetim_paneli_goster() -> bool:" in source
    assert "return tarama_hazir" in source


def test_vbts_sync_runs_before_status_cards() -> None:
    source = _source()
    start = source.index("def bist_toplu_tarama_formu()")
    section = source[start: source.index("def acik_pozisyon_sonucu_goster", start)]
    assert section.index("vbts_yonetim_paneli_goster()") < section.index(
        "kap_vbts_durum_karti_goster()"
    )


def test_scan_button_is_disabled_when_vbts_is_not_ready() -> None:
    source = _source()
    assert "disabled=not vbts_tarama_hazir" in source


def test_scan_has_backend_guard_for_vbts_readiness() -> None:
    source = _source()
    assert "if not vbts_tarama_hazir or hazir_tarama_servisi is None:" in source
    assert "toplu tarama başlatılmadı" in source

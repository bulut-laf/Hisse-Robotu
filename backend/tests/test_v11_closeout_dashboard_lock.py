from pathlib import Path


def _source() -> str:
    return Path("backend/dashboard.py").read_text(encoding="utf-8")


def _scan_form_source() -> str:
    source = _source()
    start = source.index("def bist_toplu_tarama_formu()")
    end = source.index("def acik_pozisyon_sonucu_goster", start)
    return source[start:end]


def test_vbts_management_panel_returns_operational_readiness() -> None:
    source = _source()
    assert "def vbts_yonetim_paneli_goster() -> bool:" in source
    assert "return tarama_hazir" in source


def test_vbts_sync_runs_before_status_cards() -> None:
    section = _scan_form_source()
    assert section.index("vbts_yonetim_paneli_goster()") < section.index(
        "kap_vbts_durum_karti_goster()"
    )


def test_scan_button_is_not_disabled_by_vbts_readiness() -> None:
    section = _scan_form_source()
    assert "disabled=not vbts_tarama_hazir" not in section
    assert "disabled=hazir_tarama_servisi is None" in section


def test_scan_has_no_vbts_readiness_hard_stop() -> None:
    section = _scan_form_source()
    assert "if not vbts_tarama_hazir or hazir_tarama_servisi is None:" not in section
    assert "VBTS koruması doğrulanamadığı için toplu tarama başlatılmadı" not in section
    assert "vbts_hard_block=False" in section
    assert "Bu durum VBTS kilidi değildir" in section

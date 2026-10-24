from pathlib import Path


UI = Path("backend/app/ui/prebreakout_validation_dashboard.py")


def test_toplu_dogrulama_ekrani_kalibrasyon_raporunu_kullanir() -> None:
    source = UI.read_text(encoding="utf-8-sig")

    assert "generate_calibration_report" in source
    assert 'st.subheader("Eşik kalibrasyon önerisi")' in source
    assert "automatic_change_applied" in source
    assert "Kalibrasyon önerisini CSV indir" in source


def test_ekran_uretim_esigini_yazmaz() -> None:
    source = UI.read_text(encoding="utf-8-sig")

    forbidden = (
        "write_config(",
        "save_config(",
        "set_production_threshold(",
    )
    assert all(item not in source for item in forbidden)


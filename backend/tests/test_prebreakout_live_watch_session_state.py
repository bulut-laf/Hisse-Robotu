from pathlib import Path


DASHBOARD = Path("backend/app/ui/prebreakout_dashboard.py")


def test_on_yukselis_sonucu_oturum_durumunda_saklanir() -> None:
    source = DASHBOARD.read_text(encoding="utf-8-sig")

    assert 'cache_key = "prebreakout_last_completed_run"' in source
    assert "cached_run = st.session_state.get(cache_key)" in source
    assert "st.session_state[cache_key] = {" in source
    assert '"details": tuple(details)' in source


def test_canli_izleme_dugmesi_oncesinde_onbellek_geri_yuklenir() -> None:
    source = DASHBOARD.read_text(encoding="utf-8-sig")

    restore_position = source.index('details = list(cached_run["details"])')
    save_button_position = source.index(
        '"E2–E4 adaylarını canlı izlemeye kaydet"'
    )

    assert restore_position < save_button_position


def test_ayar_degistiginde_eski_sonuc_kullanilmaz() -> None:
    source = DASHBOARD.read_text(encoding="utf-8-sig")

    assert 'cached_run.get("signature") != run_signature' in source
    assert "int(minimum_score)" in source
    assert "float(maximum_daily_return)" in source
    assert "cutoff_date.isoformat()" in source


from pathlib import Path


def test_walk_forward_sonucu_canli_seans_dugmesi_icin_oturumda_korunur() -> None:
    dashboard = Path(__file__).resolve().parents[1] / "dashboard.py"
    kaynak = dashboard.read_text(encoding="utf-8")

    assert 'MOMENTUM_REPLAY_RESULT_KEY = "momentum_walk_forward_sonucu"' in kaynak
    assert 'MOMENTUM_REPLAY_SIGNATURE_KEY = "momentum_walk_forward_imzasi"' in kaynak
    assert "st.session_state[MOMENTUM_REPLAY_RESULT_KEY] = replay_sonucu" in kaynak
    assert "st.session_state[MOMENTUM_REPLAY_SIGNATURE_KEY] = replay_imzasi" in kaynak
    assert "kayitli_replay = st.session_state.get(MOMENTUM_REPLAY_RESULT_KEY)" in kaynak
    assert "kayitli_imza == replay_imzasi" in kaynak
    assert "momentum_walk_forward_sonucu_goster(kayitli_replay)" in kaynak

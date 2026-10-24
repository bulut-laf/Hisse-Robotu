from dataclasses import dataclass
from datetime import date, datetime, timezone

import pytest

from backend.app.analysis.active_shadow_trader import (
    ACTION_EXIT_REVIEW,
    ACTION_HOLD,
    ACTION_STOP_EXIT,
    ACTION_WATCH,
    NEWS_HIGH,
    NEWS_NONE,
    NEWS_WATCH,
    TECH_NEUTRAL,
    TECH_POSITIVE,
    TECH_WEAK,
    TraderPolicy,
    TraderState,
    assess_shadow_position,
    next_state,
    stable_position_key,
)


@dataclass
class Position:
    symbol: str = "TUPRS.IS"
    entry_date: str = "2026-08-04"
    entry_price: float = 100.0
    quantity: int = 100
    stop_loss: float | None = 95.0
    target_1_hit: bool = False
    target_2_hit: bool = False


def test_stable_key_ayni_pozisyonda_ayni_sonucu_verir():
    assert stable_position_key(Position()) == stable_position_key(Position())


def test_stop_ihlali_dogrudan_cikis_uretir():
    result = assess_shadow_position(
        Position(), manual_price=94.5, technical_state=TECH_POSITIVE, observed_on=date(2026, 8, 5)
    )
    assert result.action == ACTION_STOP_EXIT
    assert result.stop_hit is True


def test_bir_r_sonrasi_basa_bas_stop_onerilir():
    result = assess_shadow_position(
        Position(), manual_price=105.0, technical_state=TECH_POSITIVE, observed_on=date(2026, 8, 5)
    )
    assert result.r_multiple == pytest.approx(1.0)
    assert result.recommended_stop == pytest.approx(100.0)
    assert result.stop_phase == "Başa baş"


def test_bir_bucuk_r_sonrasi_kar_koruma_stopu():
    result = assess_shadow_position(
        Position(), manual_price=107.5, technical_state=TECH_POSITIVE, observed_on=date(2026, 8, 5)
    )
    assert result.recommended_stop == pytest.approx(101.25)
    assert result.stop_phase == "Kâr koruma"


def test_iki_r_sonrasi_trailing_stop_high_watera_baglanir():
    state = TraderState(position_key=stable_position_key(Position()), high_water_price=112.0)
    result = assess_shadow_position(
        Position(), manual_price=110.0, state=state, technical_state=TECH_POSITIVE, observed_on=date(2026, 8, 5)
    )
    assert result.high_water_price == 112.0
    assert result.recommended_stop == pytest.approx(108.25)
    assert result.stop_phase == "Trailing stop"


def test_trailing_stop_altina_geri_donus_stop_ihlali_sayilir():
    state = TraderState(position_key=stable_position_key(Position()), high_water_price=112.0)
    result = assess_shadow_position(
        Position(), manual_price=107.0, state=state, technical_state=TECH_POSITIVE, observed_on=date(2026, 8, 5)
    )
    assert result.recommended_stop == pytest.approx(108.25)
    assert result.stop_hit is True
    assert result.action == ACTION_STOP_EXIT


def test_yukseltilmis_stop_asla_asagi_indirilmez():
    state = TraderState(position_key=stable_position_key(Position()), active_stop=103.0, high_water_price=107.0)
    result = assess_shadow_position(
        Position(), manual_price=106.0, state=state, technical_state=TECH_POSITIVE, observed_on=date(2026, 8, 5)
    )
    assert result.recommended_stop >= 103.0


def test_teknik_bozulma_stopa_degmese_de_cikis_degerlendirmesi():
    result = assess_shadow_position(
        Position(), manual_price=102.0, technical_state=TECH_WEAK, observed_on=date(2026, 8, 5)
    )
    assert result.action == ACTION_EXIT_REVIEW


def test_yuksek_haber_riski_cikis_degerlendirmesi():
    result = assess_shadow_position(
        Position(), manual_price=102.0, technical_state=TECH_POSITIVE, news_risk=NEWS_HIGH, observed_on=date(2026, 8, 5)
    )
    assert result.action == ACTION_EXIT_REVIEW


def test_izle_haber_riski_yakin_izleme_uretir():
    result = assess_shadow_position(
        Position(), manual_price=102.0, technical_state=TECH_POSITIVE, news_risk=NEWS_WATCH, observed_on=date(2026, 8, 5)
    )
    assert result.action == ACTION_WATCH


def test_pozitif_ve_risksiz_durum_tut_uretir():
    result = assess_shadow_position(
        Position(), manual_price=102.0, technical_state=TECH_POSITIVE, news_risk=NEWS_NONE, observed_on=date(2026, 8, 5)
    )
    assert result.action == ACTION_HOLD


def test_zaman_stopu_yetersiz_ilerlemede_degerlendirme_uretir():
    result = assess_shadow_position(
        Position(entry_date="2026-07-30"),
        manual_price=101.0,
        technical_state=TECH_POSITIVE,
        observed_on=date(2026, 8, 5),
        policy=TraderPolicy(max_holding_days=5),
    )
    assert result.time_review is True
    assert result.action == ACTION_EXIT_REVIEW


def test_stop_tanimsizsa_r_bazli_stop_uydurulmaz():
    result = assess_shadow_position(
        Position(stop_loss=None), manual_price=110.0, technical_state=TECH_POSITIVE, observed_on=date(2026, 8, 5)
    )
    assert result.r_multiple is None
    assert result.recommended_stop is None


def test_next_state_stop_uygulamadan_sadece_gozlem_kaydeder():
    assessment = assess_shadow_position(
        Position(), manual_price=107.5, technical_state=TECH_POSITIVE, observed_on=date(2026, 8, 5)
    )
    state = next_state(
        assessment,
        observed_at=datetime(2026, 8, 5, 9, 0, tzinfo=timezone.utc),
        apply_recommended_stop=False,
    )
    assert state.active_stop is None
    assert state.high_water_price == 107.5
    assert state.observation_count == 1


def test_next_state_onerilen_stopu_uygular():
    assessment = assess_shadow_position(
        Position(), manual_price=107.5, technical_state=TECH_POSITIVE, observed_on=date(2026, 8, 5)
    )
    state = next_state(
        assessment,
        observed_at=datetime(2026, 8, 5, 9, 0, tzinfo=timezone.utc),
        apply_recommended_stop=True,
    )
    assert state.active_stop == pytest.approx(101.25)


def test_gecersiz_politika_reddedilir():
    with pytest.raises(ValueError):
        TraderPolicy(breakeven_r=2.0, profit_lock_r=1.0)

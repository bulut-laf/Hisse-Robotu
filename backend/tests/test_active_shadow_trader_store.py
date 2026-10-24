from dataclasses import dataclass
from datetime import date, datetime, timezone

from backend.app.analysis.active_shadow_trader import (
    ActiveShadowTraderStore,
    TECH_POSITIVE,
    assess_shadow_position,
    stable_position_key,
)


@dataclass
class Position:
    symbol: str = "REEDR.IS"
    entry_date: str = "2026-08-04"
    entry_price: float = 50.0
    quantity: int = 100
    stop_loss: float = 48.0
    target_1_hit: bool = False
    target_2_hit: bool = False


def test_store_state_kalici_olarak_saklar(tmp_path):
    position = Position()
    assessment = assess_shadow_position(
        position, manual_price=52.0, technical_state=TECH_POSITIVE, observed_on=date(2026, 8, 5)
    )
    store = ActiveShadowTraderStore(tmp_path)
    state = store.record_assessment(
        assessment,
        previous=None,
        apply_recommended_stop=True,
        observed_at=datetime(2026, 8, 5, 10, 0, tzinfo=timezone.utc),
    )
    loaded = ActiveShadowTraderStore(tmp_path).load(stable_position_key(position))
    assert loaded == state


def test_gozlem_jsonl_ayri_audit_izi_tutar(tmp_path):
    assessment = assess_shadow_position(
        Position(), manual_price=52.0, technical_state=TECH_POSITIVE, observed_on=date(2026, 8, 5)
    )
    store = ActiveShadowTraderStore(tmp_path)
    store.record_assessment(
        assessment,
        previous=None,
        apply_recommended_stop=False,
        observed_at=datetime(2026, 8, 5, 10, 0, tzinfo=timezone.utc),
    )
    lines = store.observation_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert "REEDR.IS" in lines[0]

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MorningUserDashboard:
    market_state: str
    action_count: int
    priority_count: int
    inspect_ready: int
    dashboard_state: str


def build_morning_user_dashboard(
    *,
    market_state: str,
    action_count: int,
    priority_count: int,
    inspect_ready: int,
) -> MorningUserDashboard:
    return MorningUserDashboard(
        market_state=str(market_state),
        action_count=int(action_count),
        priority_count=int(priority_count),
        inspect_ready=int(inspect_ready),
        dashboard_state=(
            "SABAH KULLANICI PANELİ HAZIR"
            if action_count > 0
            else "AKSİYON BEKLENİYOR"
        ),
    )

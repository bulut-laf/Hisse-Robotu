from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MorningDashboardIntegration:
    market_state: str
    action_count: int
    priority_count: int
    inspect_ready_count: int
    integration_state: str


def build_morning_dashboard_integration(
    *,
    market_state: str,
    action_count: int,
    priority_count: int,
    inspect_ready_count: int,
) -> MorningDashboardIntegration:
    return MorningDashboardIntegration(
        market_state=str(market_state),
        action_count=int(action_count),
        priority_count=int(priority_count),
        inspect_ready_count=int(inspect_ready_count),
        integration_state=(
            "DASHBOARD ENTEGRASYONU HAZIR"
            if action_count > 0
            else "VERİ BEKLENİYOR"
        ),
    )

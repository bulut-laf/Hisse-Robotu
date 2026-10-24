from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MorningCommandCenterView:
    market_state: str
    candidate_count: int
    priority_symbols: tuple[str, ...]
    pending_actions: int
    view_state: str


def build_morning_command_center_view(
    *,
    market_state: str,
    candidates: tuple[object, ...],
    priority_symbols: tuple[str, ...],
    pending_actions: int,
) -> MorningCommandCenterView:
    return MorningCommandCenterView(
        market_state=str(market_state),
        candidate_count=len(candidates),
        priority_symbols=tuple(priority_symbols),
        pending_actions=int(pending_actions),
        view_state=(
            "SABAH OPERASYON MERKEZİ HAZIR"
            if candidates
            else "ADAY BEKLENİYOR"
        ),
    )

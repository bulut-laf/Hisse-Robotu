from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MorningActionBoard:
    inspect_symbols: tuple[str, ...]
    blocked_symbols: tuple[str, ...]
    pending_count: int
    action_state: str


def build_morning_action_board(
    candidates: tuple[object, ...],
) -> MorningActionBoard:
    inspect = []
    blocked = []

    for item in candidates:
        symbol = str(getattr(item, "symbol", "")).upper()

        if bool(getattr(item, "data_blocked", False)):
            blocked.append(symbol)
        else:
            inspect.append(symbol)

    return MorningActionBoard(
        inspect_symbols=tuple(inspect),
        blocked_symbols=tuple(blocked),
        pending_count=len(inspect) + len(blocked),
        action_state=(
            "BUGÜNÜN AKSİYONLARI HAZIR"
            if candidates
            else "AKSİYON BEKLENİYOR"
        ),
    )

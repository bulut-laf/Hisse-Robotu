from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class MorningFinalAction:
    action_priority: int
    symbol: str
    decision: str
    action: str
    original_priority: int
    selection_source: str
    entry_readiness: str
    jump_quality: str
    technical_score: int
    volume_ratio: float
    risk_reward: float
    data_status: str
    reason: str


def _action_label(decision: str) -> str:
    value = str(decision or "").strip().upper()
    if value == "AL":
        return "AL ADAYI"
    if value == "BEKLE":
        return "İZLE / TEYİT BEKLE"
    return "İŞLEM YOK"


def build_morning_final_actions(
    cards: Iterable[object],
    decisions: Iterable[object],
) -> tuple[MorningFinalAction, ...]:
    card_by_symbol = {
        str(getattr(card, "symbol", "")).strip().upper(): card
        for card in cards
        if str(getattr(card, "symbol", "")).strip()
    }
    items: list[MorningFinalAction] = []
    for decision in decisions:
        symbol = str(getattr(decision, "symbol", "")).strip().upper()
        if not symbol:
            continue
        card = card_by_symbol.get(symbol)
        decision_value = str(getattr(decision, "decision", "İŞLEM YOK")).strip().upper()
        reasons = tuple(getattr(decision, "reasons", ()) or ())
        cautions = tuple(getattr(decision, "cautions", ()) or ())
        reason = " | ".join(reasons) or "-"
        if cautions:
            reason = f"{reason} · Dikkat: {' | '.join(cautions)}"
        items.append(
            MorningFinalAction(
                action_priority=0,
                symbol=symbol,
                decision=decision_value,
                action=_action_label(decision_value),
                original_priority=int(getattr(decision, "priority", len(items) + 1)),
                selection_source=str(getattr(card, "selection_source", "TARAMA") or "TARAMA").upper(),
                entry_readiness=str(getattr(card, "entry_readiness", "-") or "-").upper(),
                jump_quality=str(getattr(card, "jump_quality", "-") or "-").upper(),
                technical_score=int(getattr(decision, "technical_score", 0)),
                volume_ratio=float(getattr(decision, "volume_ratio", 0.0)),
                risk_reward=float(getattr(decision, "risk_reward", 0.0)),
                data_status=str(getattr(decision, "data_status", "UYGUN")),
                reason=reason,
            )
        )

    order = {"AL": 0, "BEKLE": 1, "İŞLEM YOK": 2}
    items.sort(key=lambda item: (order.get(item.decision, 9), item.original_priority))
    return tuple(
        MorningFinalAction(
            action_priority=index,
            symbol=item.symbol,
            decision=item.decision,
            action=item.action,
            original_priority=item.original_priority,
            selection_source=item.selection_source,
            entry_readiness=item.entry_readiness,
            jump_quality=item.jump_quality,
            technical_score=item.technical_score,
            volume_ratio=item.volume_ratio,
            risk_reward=item.risk_reward,
            data_status=item.data_status,
            reason=item.reason,
        )
        for index, item in enumerate(items, start=1)
    )


def morning_final_action_rows(
    actions: Iterable[MorningFinalAction],
) -> tuple[dict[str, object], ...]:
    return tuple(
        {
            "Aksiyon önceliği": f"#{item.action_priority}",
            "Hisse": item.symbol,
            "Sabah aksiyon": item.action,
            "Karar": item.decision,
            "Top-5 sırası": f"#{item.original_priority}",
            "Kaynak": item.selection_source,
            "Giriş hazırlığı": item.entry_readiness,
            "Sıçrama kalite": item.jump_quality,
            "Teknik skor": item.technical_score,
            "Hacim": round(item.volume_ratio, 2),
            "Risk/Getiri": round(item.risk_reward, 2),
            "Veri": item.data_status,
            "Neden / dikkat": item.reason,
        }
        for item in actions
    )

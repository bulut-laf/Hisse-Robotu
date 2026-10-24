from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class EodMorningBoardDeltaItem:
    symbol: str
    evening_decision: str
    morning_decision: str
    delta_type: str
    evening_rank: int | None
    morning_rank: int | None
    reason: str


@dataclass(frozen=True)
class EodMorningBoardDeltaSummary:
    evening_total: int
    morning_total: int
    evening_buy: int
    morning_buy: int
    unchanged: int
    upgrades: int
    downgrades: int
    added: int
    removed: int
    headline: str
    items: tuple[EodMorningBoardDeltaItem, ...]


_DECISION_WEIGHT = {
    "İŞLEM YOK": 0,
    "BEKLE": 1,
    "AL": 2,
}


def _decision(value: object) -> str:
    text = str(value or "İŞLEM YOK").strip().upper()
    return text if text in _DECISION_WEIGHT else "İŞLEM YOK"


def _reason(old: object | None, new: object | None, delta_type: str) -> str:
    if old is None:
        source = str(getattr(new, "selection_source", "TARAMA") or "TARAMA").upper()
        readiness = str(getattr(new, "entry_readiness", "-") or "-").upper()
        return f"Sabah Top-5'e girdi · Kaynak: {source} · Giriş hazırlığı: {readiness}"
    if new is None:
        return "Akşam Top-5'teydi; sabah nihai listede yer almıyor."

    parts: list[str] = []
    old_decision = _decision(getattr(old, "decision", None))
    new_decision = _decision(getattr(new, "decision", None))
    if old_decision != new_decision:
        parts.append(f"Karar {old_decision}→{new_decision}")

    old_ready = str(getattr(old, "entry_readiness", "-") or "-").upper()
    new_ready = str(getattr(new, "entry_readiness", "-") or "-").upper()
    if old_ready != new_ready:
        parts.append(f"Giriş hazırlığı {old_ready}→{new_ready}")

    old_quality = str(getattr(old, "jump_quality", "-") or "-").upper()
    new_quality = str(getattr(new, "jump_quality", "-") or "-").upper()
    if old_quality != new_quality:
        parts.append(f"Sıçrama kalite {old_quality}→{new_quality}")

    old_source = str(getattr(old, "selection_source", "TARAMA") or "TARAMA").upper()
    new_source = str(getattr(new, "selection_source", "TARAMA") or "TARAMA").upper()
    if old_source != new_source:
        parts.append(f"Kaynak {old_source}→{new_source}")

    if not parts:
        if delta_type == "AYNI":
            return "Karar yapısı değişmedi."
        return "Sabah yeniden değerlendirmesinde karar seviyesi değişti."
    return " · ".join(parts)


def build_eod_morning_board_delta(
    evening: object | None,
    morning: object | None,
) -> EodMorningBoardDeltaSummary | None:
    """Akşam ve sabah Top-5 snapshot'larının karar farkını read-only özetler."""
    if evening is None or morning is None:
        return None

    evening_candidates = tuple(getattr(evening, "candidates", ()) or ())
    morning_candidates = tuple(getattr(morning, "candidates", ()) or ())
    evening_by_symbol = {
        str(getattr(item, "symbol", "")).strip().upper(): item
        for item in evening_candidates
        if str(getattr(item, "symbol", "")).strip()
    }
    morning_by_symbol = {
        str(getattr(item, "symbol", "")).strip().upper(): item
        for item in morning_candidates
        if str(getattr(item, "symbol", "")).strip()
    }

    symbols = list(dict.fromkeys([
        *(str(getattr(item, "symbol", "")).strip().upper() for item in evening_candidates),
        *(str(getattr(item, "symbol", "")).strip().upper() for item in morning_candidates),
    ]))

    items: list[EodMorningBoardDeltaItem] = []
    unchanged = upgrades = downgrades = added = removed = 0

    for symbol in symbols:
        old = evening_by_symbol.get(symbol)
        new = morning_by_symbol.get(symbol)
        if old is None:
            delta_type = "YENİ"
            added += 1
        elif new is None:
            delta_type = "ÇIKTI"
            removed += 1
        else:
            old_decision = _decision(getattr(old, "decision", None))
            new_decision = _decision(getattr(new, "decision", None))
            old_weight = _DECISION_WEIGHT[old_decision]
            new_weight = _DECISION_WEIGHT[new_decision]
            if new_weight > old_weight:
                delta_type = "GÜÇLENDİ"
                upgrades += 1
            elif new_weight < old_weight:
                delta_type = "ZAYIFLADI"
                downgrades += 1
            else:
                delta_type = "AYNI"
                unchanged += 1

        items.append(
            EodMorningBoardDeltaItem(
                symbol=symbol,
                evening_decision=(
                    _decision(getattr(old, "decision", None)) if old is not None else "-"
                ),
                morning_decision=(
                    _decision(getattr(new, "decision", None)) if new is not None else "-"
                ),
                delta_type=delta_type,
                evening_rank=(int(getattr(old, "rank")) if old is not None else None),
                morning_rank=(int(getattr(new, "rank")) if new is not None else None),
                reason=_reason(old, new, delta_type),
            )
        )

    evening_buy = sum(
        1 for item in evening_candidates if _decision(getattr(item, "decision", None)) == "AL"
    )
    morning_buy = sum(
        1 for item in morning_candidates if _decision(getattr(item, "decision", None)) == "AL"
    )

    if upgrades == downgrades == added == removed == 0:
        headline = "Akşam Top-5 ile 09:00 nihai liste aynı karar yapısını korudu."
    else:
        headline = (
            f"09:00 sonucu: {morning_buy} AL · {upgrades} güçlenen · "
            f"{downgrades} zayıflayan · {added} yeni · {removed} çıkan aday."
        )

    return EodMorningBoardDeltaSummary(
        evening_total=len(evening_candidates),
        morning_total=len(morning_candidates),
        evening_buy=evening_buy,
        morning_buy=morning_buy,
        unchanged=unchanged,
        upgrades=upgrades,
        downgrades=downgrades,
        added=added,
        removed=removed,
        headline=headline,
        items=tuple(items),
    )


def eod_morning_board_delta_rows(
    summary: EodMorningBoardDeltaSummary,
    *,
    changed_only: bool = True,
) -> tuple[dict[str, object], ...]:
    items: Iterable[EodMorningBoardDeltaItem] = summary.items
    if changed_only:
        items = (item for item in items if item.delta_type != "AYNI")
    return tuple(
        {
            "Hisse": item.symbol,
            "Akşam": item.evening_decision,
            "09:00": item.morning_decision,
            "Değişim": item.delta_type,
            "Akşam sıra": item.evening_rank if item.evening_rank is not None else "-",
            "Sabah sıra": item.morning_rank if item.morning_rank is not None else "-",
            "Kısa neden": item.reason,
        }
        for item in items
    )

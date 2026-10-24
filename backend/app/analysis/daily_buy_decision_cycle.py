from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
import json
from pathlib import Path
from typing import Iterable
from zoneinfo import ZoneInfo

ISTANBUL = ZoneInfo("Europe/Istanbul")
DEFAULT_DAILY_BUY_DECISION_PATH = Path("backend/data/daily_buy_decision_cycle.json")


@dataclass(frozen=True)
class DailyBuyDecisionCandidate:
    rank: int
    symbol: str
    technical_score: int
    technical_view: str
    research_priority: str
    visibility_state: str | None
    rank_change: int | None
    operational_status: str
    data_blocked: bool
    decision: str | None = None
    volume_ratio: float | None = None
    risk_reward: float | None = None
    selection_source: str = "TARAMA"
    jump_quality: str = "-"
    entry_readiness: str = "-"
    decision_reasons: tuple[str, ...] = ()
    decision_cautions: tuple[str, ...] = ()


@dataclass(frozen=True)
class DailyBuyDecisionSnapshot:
    phase: str
    created_at: str
    candidates: tuple[DailyBuyDecisionCandidate, ...]


@dataclass(frozen=True)
class DailyBuyDecisionChange:
    symbol: str
    evening_rank: int | None
    morning_rank: int | None
    rank_delta: int | None
    evening_status: str | None
    morning_status: str | None
    change_reason: str
    evening_decision: str | None = None
    morning_decision: str | None = None


@dataclass(frozen=True)
class DailyBuyDecisionReplacement:
    outgoing_symbol: str
    incoming_symbol: str
    outgoing_rank: int | None
    incoming_rank: int | None
    outgoing_decision: str | None
    incoming_decision: str | None
    replacement_context: str


def resolve_daily_buy_decision_phase(now: datetime | None = None) -> str | None:
    local = (now or datetime.now(ISTANBUL)).astimezone(ISTANBUL)
    hour = local.hour
    if hour >= 17:
        return "EVENING"
    if 7 <= hour < 12:
        return "MORNING"
    return None


def _candidate_from_card(
    card: object,
    decision: object | None = None,
) -> DailyBuyDecisionCandidate:
    return DailyBuyDecisionCandidate(
        rank=int(getattr(card, "rank")),
        symbol=str(getattr(card, "symbol", "")).strip().upper(),
        technical_score=int(getattr(card, "technical_score")),
        technical_view=str(getattr(card, "technical_view", "")),
        research_priority=str(getattr(card, "research_priority", "NORMAL")),
        visibility_state=(
            str(getattr(card, "visibility_state"))
            if getattr(card, "visibility_state", None) is not None
            else None
        ),
        rank_change=(
            int(getattr(card, "rank_change"))
            if getattr(card, "rank_change", None) is not None
            else None
        ),
        operational_status=str(getattr(card, "operational_status", "")),
        data_blocked=bool(getattr(card, "data_blocked", False)),
        decision=(
            str(getattr(decision, "decision"))
            if decision is not None and getattr(decision, "decision", None) is not None
            else None
        ),
        volume_ratio=(
            float(getattr(card, "volume_ratio"))
            if getattr(card, "volume_ratio", None) is not None
            else None
        ),
        risk_reward=(
            float(getattr(card, "risk_reward"))
            if getattr(card, "risk_reward", None) is not None
            else None
        ),
        selection_source=str(getattr(card, "selection_source", "TARAMA") or "TARAMA").upper(),
        jump_quality=str(getattr(card, "jump_quality", "-") or "-").upper(),
        entry_readiness=str(getattr(card, "entry_readiness", "-") or "-").upper(),
        decision_reasons=tuple(getattr(decision, "reasons", ()) or ()),
        decision_cautions=tuple(getattr(decision, "cautions", ()) or ()),
    )


def build_daily_buy_decision_snapshot(
    cards: Iterable[object],
    *,
    phase: str,
    now: datetime | None = None,
    decisions: Iterable[object] = (),
) -> DailyBuyDecisionSnapshot:
    phase_value = str(phase).strip().upper()
    if phase_value not in {"EVENING", "MORNING"}:
        raise ValueError("phase EVENING veya MORNING olmalıdır.")
    timestamp = (now or datetime.now(ISTANBUL)).astimezone(ISTANBUL)
    decision_by_symbol = {
        str(getattr(item, "symbol", "")).strip().upper(): item
        for item in decisions
        if str(getattr(item, "symbol", "")).strip()
    }
    candidates = tuple(cards)
    return DailyBuyDecisionSnapshot(
        phase=phase_value,
        created_at=timestamp.isoformat(timespec="seconds"),
        candidates=tuple(
            _candidate_from_card(
                card,
                decision_by_symbol.get(str(getattr(card, "symbol", "")).strip().upper()),
            )
            for card in candidates
        ),
    )


class DailyBuyDecisionJsonStore:
    def __init__(self, path: Path | str = DEFAULT_DAILY_BUY_DECISION_PATH) -> None:
        self.path = Path(path)

    def load(self) -> dict[str, DailyBuyDecisionSnapshot]:
        if not self.path.exists():
            return {}
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        result: dict[str, DailyBuyDecisionSnapshot] = {}
        for phase, payload in dict(raw).items():
            candidates = tuple(
                DailyBuyDecisionCandidate(**item)
                for item in payload.get("candidates", ())
            )
            result[str(phase).upper()] = DailyBuyDecisionSnapshot(
                phase=str(payload["phase"]).upper(),
                created_at=str(payload["created_at"]),
                candidates=candidates,
            )
        return result

    def save(self, snapshot: DailyBuyDecisionSnapshot) -> None:
        snapshots = self.load()
        snapshots[snapshot.phase] = snapshot
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            phase: {
                "phase": item.phase,
                "created_at": item.created_at,
                "candidates": [asdict(candidate) for candidate in item.candidates],
            }
            for phase, item in snapshots.items()
        }
        self.path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def _fmt_number(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value:.2f}"


def _decision_change_reasons(
    old: DailyBuyDecisionCandidate,
    new: DailyBuyDecisionCandidate,
) -> list[str]:
    reasons: list[str] = []
    if old.decision != new.decision:
        reasons.append(f"Karar {old.decision or '-'}→{new.decision or '-'}")

    if old.technical_view != new.technical_view:
        reasons.append(f"Teknik görünüm değişti ({old.technical_view}→{new.technical_view})")
    if old.technical_score != new.technical_score:
        reasons.append(f"Teknik skor {old.technical_score}→{new.technical_score}")

    if old.volume_ratio != new.volume_ratio:
        old_ok = old.volume_ratio is not None and old.volume_ratio >= 1.0
        new_ok = new.volume_ratio is not None and new.volume_ratio >= 1.0
        if old_ok != new_ok:
            label = "Hacim teyidi geldi" if new_ok else "Hacim teyidi kayboldu"
            reasons.append(f"{label} ({_fmt_number(old.volume_ratio)}→{_fmt_number(new.volume_ratio)})")
        else:
            reasons.append(f"Hacim {_fmt_number(old.volume_ratio)}→{_fmt_number(new.volume_ratio)}")

    if old.risk_reward != new.risk_reward:
        old_buy_ok = old.risk_reward is not None and old.risk_reward >= 1.5
        new_buy_ok = new.risk_reward is not None and new.risk_reward >= 1.5
        old_no_trade = old.risk_reward is not None and old.risk_reward < 1.0
        new_no_trade = new.risk_reward is not None and new.risk_reward < 1.0
        if old_buy_ok != new_buy_ok:
            label = "Risk/getiri AL eşiğini geçti" if new_buy_ok else "Risk/getiri AL eşiğinin altına indi"
            reasons.append(f"{label} ({_fmt_number(old.risk_reward)}→{_fmt_number(new.risk_reward)})")
        elif old_no_trade != new_no_trade:
            label = "Risk/getiri işlem eşiğinin altına indi" if new_no_trade else "Risk/getiri işlem eşiğinin üzerine çıktı"
            reasons.append(f"{label} ({_fmt_number(old.risk_reward)}→{_fmt_number(new.risk_reward)})")
        else:
            reasons.append(f"Risk/getiri {_fmt_number(old.risk_reward)}→{_fmt_number(new.risk_reward)}")

    if old.entry_readiness != new.entry_readiness:
        reasons.append(f"Giriş hazırlığı {old.entry_readiness}→{new.entry_readiness}")
    if old.jump_quality != new.jump_quality:
        reasons.append(f"Sıçrama kalite kapısı {old.jump_quality}→{new.jump_quality}")
    if old.selection_source != new.selection_source:
        reasons.append(f"Aday kaynağı {old.selection_source}→{new.selection_source}")
    if old.research_priority != new.research_priority:
        reasons.append(f"Araştırma önceliği {old.research_priority}→{new.research_priority}")
    if old.visibility_state != new.visibility_state:
        reasons.append(f"Erken görünürlük {old.visibility_state or '-'}→{new.visibility_state or '-'}")
    return reasons


def compare_evening_morning(
    evening: DailyBuyDecisionSnapshot | None,
    morning: DailyBuyDecisionSnapshot | None,
) -> tuple[DailyBuyDecisionChange, ...]:
    if evening is None or morning is None:
        return ()

    evening_by_symbol = {item.symbol: item for item in evening.candidates}
    morning_by_symbol = {item.symbol: item for item in morning.candidates}
    symbols = list(dict.fromkeys([
        *(item.symbol for item in evening.candidates),
        *(item.symbol for item in morning.candidates),
    ]))
    changes: list[DailyBuyDecisionChange] = []

    for symbol in symbols:
        old = evening_by_symbol.get(symbol)
        new = morning_by_symbol.get(symbol)
        reasons: list[str] = []
        if old is None:
            reasons.append("Sabah listesine yeni girdi")
        elif new is None:
            reasons.append("Sabah listeden çıktı")
        else:
            reasons.extend(_decision_change_reasons(old, new))
            if old.rank != new.rank:
                reasons.append(f"Öncelik sırası {old.rank}→{new.rank}")
            if old.operational_status != new.operational_status:
                reasons.append(
                    f"Durum {old.operational_status}→{new.operational_status}"
                )
            if old.rank_change != new.rank_change:
                reasons.append("Sıralama hareketi güncellendi")
            if old.data_blocked != new.data_blocked:
                reasons.append("Veri kalite durumu değişti")
        changes.append(
            DailyBuyDecisionChange(
                symbol=symbol,
                evening_rank=old.rank if old else None,
                morning_rank=new.rank if new else None,
                rank_delta=(old.rank - new.rank) if old and new else None,
                evening_status=old.operational_status if old else None,
                morning_status=new.operational_status if new else None,
                change_reason="; ".join(reasons) if reasons else "Değişiklik yok",
                evening_decision=old.decision if old else None,
                morning_decision=new.decision if new else None,
            )
        )
    return tuple(changes)


def daily_buy_decision_change_rows(
    changes: Iterable[DailyBuyDecisionChange],
) -> tuple[dict[str, object], ...]:
    return tuple(
        {
            "Hisse": item.symbol,
            "Akşam sıra": item.evening_rank if item.evening_rank is not None else "-",
            "Sabah sıra": item.morning_rank if item.morning_rank is not None else "-",
            "Sıra farkı": item.rank_delta if item.rank_delta is not None else "-",
            "Akşam karar": item.evening_decision or "-",
            "Sabah karar": item.morning_decision or "-",
            "Akşam durum": item.evening_status or "-",
            "Sabah durum": item.morning_status or "-",
            "Değişim nedeni": item.change_reason,
        }
        for item in changes
    )


def _replacement_context(
    outgoing: DailyBuyDecisionCandidate,
    incoming: DailyBuyDecisionCandidate,
) -> str:
    parts: list[str] = []
    if incoming.selection_source == "SICRAMA":
        parts.append("Sabah sıçrama havuzundan listeye girdi")
    else:
        parts.append("Sabah tarama havuzundan listeye girdi")

    if incoming.entry_readiness not in {"", "-"}:
        parts.append(f"Giriş hazırlığı: {incoming.entry_readiness}")
    if incoming.jump_quality not in {"", "-"}:
        parts.append(f"Sıçrama kalite kapısı: {incoming.jump_quality}")
    if incoming.decision:
        parts.append(f"Sabah karar: {incoming.decision}")

    if outgoing.decision:
        parts.append(f"Çıkan aday akşam kararı: {outgoing.decision}")
    if outgoing.entry_readiness not in {"", "-"}:
        parts.append(f"Çıkan aday giriş hazırlığı: {outgoing.entry_readiness}")

    return "; ".join(parts)


def compare_evening_morning_replacements(
    evening: DailyBuyDecisionSnapshot | None,
    morning: DailyBuyDecisionSnapshot | None,
) -> tuple[DailyBuyDecisionReplacement, ...]:
    """Top-5 üyeliğindeki akşam→sabah giriş/çıkışları eşleştirir."""
    if evening is None or morning is None:
        return ()

    evening_symbols = {item.symbol for item in evening.candidates}
    morning_symbols = {item.symbol for item in morning.candidates}

    outgoing = [item for item in evening.candidates if item.symbol not in morning_symbols]
    incoming = [item for item in morning.candidates if item.symbol not in evening_symbols]

    outgoing.sort(key=lambda item: item.rank)
    incoming.sort(key=lambda item: item.rank)

    replacements: list[DailyBuyDecisionReplacement] = []
    for old, new in zip(outgoing, incoming):
        replacements.append(
            DailyBuyDecisionReplacement(
                outgoing_symbol=old.symbol,
                incoming_symbol=new.symbol,
                outgoing_rank=old.rank,
                incoming_rank=new.rank,
                outgoing_decision=old.decision,
                incoming_decision=new.decision,
                replacement_context=_replacement_context(old, new),
            )
        )
    return tuple(replacements)


def daily_buy_decision_replacement_rows(
    replacements: Iterable[DailyBuyDecisionReplacement],
) -> tuple[dict[str, object], ...]:
    return tuple(
        {
            "Listeden çıkan": item.outgoing_symbol,
            "Akşam sıra": item.outgoing_rank if item.outgoing_rank is not None else "-",
            "Akşam karar": item.outgoing_decision or "-",
            "Listeye giren": item.incoming_symbol,
            "Sabah sıra": item.incoming_rank if item.incoming_rank is not None else "-",
            "Sabah karar": item.incoming_decision or "-",
            "Yer değişimi bağlamı": item.replacement_context,
        }
        for item in replacements
    )

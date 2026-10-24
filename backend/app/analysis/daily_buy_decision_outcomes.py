from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import date, datetime
import json
from pathlib import Path
from typing import Iterable, Mapping
from zoneinfo import ZoneInfo

ISTANBUL = ZoneInfo("Europe/Istanbul")
DEFAULT_BUY_DECISION_OUTCOME_PATH = Path("backend/data/daily_buy_decision_outcomes.json")
HORIZONS = (1, 3, 5)


@dataclass(frozen=True)
class BuyDecisionOutcomeRecord:
    decision_id: str
    decision_date: str
    phase: str
    symbol: str
    priority: int
    decision: str
    reference_price: float | None
    technical_score: int = 0
    volume_ratio: float = 0.0
    risk_reward: float = 0.0
    rank_change: int | None = None
    research_priority: str = "NORMAL"
    visibility_state: str | None = None
    observations: tuple[tuple[str, float], ...] = ()
    return_1s: float | None = None
    return_3s: float | None = None
    return_5s: float | None = None


def _normalize_symbol(value: object) -> str:
    return str(value or "").strip().upper().removesuffix(".IS")


def _today(now: datetime | None = None) -> date:
    return (now or datetime.now(ISTANBUL)).astimezone(ISTANBUL).date()


def _decision_id(day: date, phase: str, symbol: str) -> str:
    return f"{day.isoformat()}:{phase.upper()}:{_normalize_symbol(symbol)}"


def _session_returns(
    reference_price: float | None,
    observations: tuple[tuple[str, float], ...],
) -> tuple[float | None, float | None, float | None]:
    if reference_price is None or reference_price <= 0:
        return (None, None, None)
    returns: list[float | None] = []
    for horizon in HORIZONS:
        if len(observations) < horizon:
            returns.append(None)
            continue
        price = float(observations[horizon - 1][1])
        returns.append(((price / reference_price) - 1.0) * 100.0)
    return tuple(returns)  # type: ignore[return-value]


def register_buy_decisions(
    existing: Iterable[BuyDecisionOutcomeRecord],
    decisions: Iterable[object],
    *,
    phase: str = "MORNING",
    now: datetime | None = None,
) -> tuple[BuyDecisionOutcomeRecord, ...]:
    day = _today(now)
    result = list(existing)
    known = {item.decision_id for item in result}
    phase_value = str(phase).strip().upper()

    for item in decisions:
        if str(getattr(item, "decision", "")).upper() != "AL":
            continue
        symbol = _normalize_symbol(getattr(item, "symbol", ""))
        if not symbol:
            continue
        decision_id = _decision_id(day, phase_value, symbol)
        if decision_id in known:
            continue
        raw_price = getattr(item, "reference_price", None)
        reference_price = float(raw_price) if raw_price not in (None, "") else None
        result.append(
            BuyDecisionOutcomeRecord(
                decision_id=decision_id,
                decision_date=day.isoformat(),
                phase=phase_value,
                symbol=symbol,
                priority=int(getattr(item, "priority", 0)),
                decision="AL",
                reference_price=reference_price,
                technical_score=int(getattr(item, "technical_score", 0)),
                volume_ratio=float(getattr(item, "volume_ratio", 0.0)),
                risk_reward=float(getattr(item, "risk_reward", 0.0)),
                rank_change=(
                    int(getattr(item, "rank_change"))
                    if getattr(item, "rank_change", None) is not None
                    else None
                ),
                research_priority=str(getattr(item, "research_priority", "NORMAL")),
                visibility_state=(
                    str(getattr(item, "visibility_state"))
                    if getattr(item, "visibility_state", None) is not None
                    else None
                ),
            )
        )
        known.add(decision_id)
    return tuple(result)


def apply_session_prices(
    records: Iterable[BuyDecisionOutcomeRecord],
    prices: Mapping[str, float],
    *,
    observation_date: date | None = None,
) -> tuple[BuyDecisionOutcomeRecord, ...]:
    day = observation_date or _today()
    normalized_prices = {
        _normalize_symbol(symbol): float(price)
        for symbol, price in prices.items()
        if price is not None and float(price) > 0
    }
    updated: list[BuyDecisionOutcomeRecord] = []

    for record in records:
        price = normalized_prices.get(record.symbol)
        observations = list(record.observations)
        decision_day = date.fromisoformat(record.decision_date)
        if price is not None and day > decision_day:
            day_key = day.isoformat()
            if all(existing_day != day_key for existing_day, _ in observations):
                observations.append((day_key, price))
                observations.sort(key=lambda item: item[0])
        returns = _session_returns(record.reference_price, tuple(observations))
        updated.append(
            replace(
                record,
                observations=tuple(observations),
                return_1s=returns[0],
                return_3s=returns[1],
                return_5s=returns[2],
            )
        )
    return tuple(updated)


class BuyDecisionOutcomeJsonStore:
    def __init__(self, path: Path | str = DEFAULT_BUY_DECISION_OUTCOME_PATH) -> None:
        self.path = Path(path)

    def load(self) -> tuple[BuyDecisionOutcomeRecord, ...]:
        if not self.path.exists():
            return ()
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        return tuple(
            BuyDecisionOutcomeRecord(
                **{
                    **item,
                    "observations": tuple(tuple(obs) for obs in item.get("observations", ())),
                }
            )
            for item in raw
        )

    def save(self, records: Iterable[BuyDecisionOutcomeRecord]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps([asdict(item) for item in records], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def buy_decision_outcome_rows(
    records: Iterable[BuyDecisionOutcomeRecord],
) -> tuple[dict[str, object], ...]:
    rows = []
    for item in records:
        rows.append(
            {
                "Tarih": item.decision_date,
                "Faz": item.phase,
                "Hisse": item.symbol,
                "Öncelik": f"#{item.priority}",
                "Referans fiyat": round(item.reference_price, 4) if item.reference_price else "-",
                "1S getiri (%)": round(item.return_1s, 2) if item.return_1s is not None else "-",
                "3S getiri (%)": round(item.return_3s, 2) if item.return_3s is not None else "-",
                "5S getiri (%)": round(item.return_5s, 2) if item.return_5s is not None else "-",
                "Gözlem": len(item.observations),
            }
        )
    return tuple(rows)


def buy_decision_hit_summary(
    records: Iterable[BuyDecisionOutcomeRecord],
) -> tuple[dict[str, object], ...]:
    items = tuple(records)
    result: list[dict[str, object]] = []
    for horizon, attr in ((1, "return_1s"), (3, "return_3s"), (5, "return_5s")):
        values = [float(value) for item in items if (value := getattr(item, attr)) is not None]
        positives = sum(value > 0 for value in values)
        result.append(
            {
                "Ufuk": f"{horizon}S",
                "Değerlendirilen": len(values),
                "Pozitif": positives,
                "İsabet (%)": round((positives / len(values)) * 100.0, 1) if values else "-",
                "Ortalama getiri (%)": round(sum(values) / len(values), 2) if values else "-",
            }
        )
    return tuple(result)

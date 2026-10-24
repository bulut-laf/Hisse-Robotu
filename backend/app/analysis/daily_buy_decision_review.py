from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class DailyDecisionReview:
    decision_date: str
    phase: str
    symbol: str
    priority: int
    horizon: str
    return_pct: float | None
    outcome: str
    supporting_evidence: tuple[str, ...]
    caution_evidence: tuple[str, ...]


def _latest_result(record: object) -> tuple[str, float | None]:
    for horizon, attr in (("5S", "return_5s"), ("3S", "return_3s"), ("1S", "return_1s")):
        value = getattr(record, attr, None)
        if value is not None:
            return horizon, float(value)
    return "BEKLIYOR", None


def _evidence(record: object) -> tuple[tuple[str, ...], tuple[str, ...]]:
    supporting: list[str] = []
    caution: list[str] = []

    technical = int(getattr(record, "technical_score", 0) or 0)
    if technical >= 80:
        supporting.append("Teknik skor 80+")
    elif technical < 70:
        caution.append("Teknik skor 70 altı")

    volume = float(getattr(record, "volume_ratio", 0.0) or 0.0)
    if volume >= 1.3:
        supporting.append("Hacim teyidi güçlü")
    elif volume < 1.0:
        caution.append("Hacim teyidi zayıf")

    rr = float(getattr(record, "risk_reward", 0.0) or 0.0)
    if rr >= 2.0:
        supporting.append("Risk/getiri 2.0+")
    elif rr and rr < 1.5:
        caution.append("Risk/getiri 1.5 altı")

    rank_change = getattr(record, "rank_change", None)
    if rank_change is not None:
        rank_change = int(rank_change)
        if rank_change >= 30:
            supporting.append("Sıralama ivmesi +30 ve üzeri")
        elif rank_change < 0:
            caution.append("Sıralama gerilemesi")

    research_priority = str(getattr(record, "research_priority", "") or "").upper()
    if research_priority == "HIGH":
        supporting.append("Araştırma önceliği HIGH")

    visibility = str(getattr(record, "visibility_state", "") or "").upper()
    if visibility in {"IMPROVING", "STRONG", "RISING"}:
        supporting.append(f"Erken görünürlük {visibility}")
    elif visibility in {"WEAKENING", "FALLING", "DETERIORATING"}:
        caution.append(f"Erken görünürlük {visibility}")

    return tuple(supporting), tuple(caution)


def build_daily_decision_reviews(records: Iterable[object]) -> tuple[DailyDecisionReview, ...]:
    reviews: list[DailyDecisionReview] = []
    for record in records:
        horizon, value = _latest_result(record)
        outcome = "BEKLIYOR" if value is None else ("POZITIF" if value > 0 else "NEGATIF")
        supporting, caution = _evidence(record)
        reviews.append(
            DailyDecisionReview(
                decision_date=str(getattr(record, "decision_date", "-")),
                phase=str(getattr(record, "phase", "-")).upper(),
                symbol=str(getattr(record, "symbol", "-")).upper(),
                priority=int(getattr(record, "priority", 0) or 0),
                horizon=horizon,
                return_pct=value,
                outcome=outcome,
                supporting_evidence=supporting,
                caution_evidence=caution,
            )
        )
    return tuple(sorted(reviews, key=lambda item: (item.decision_date, item.phase, item.priority, item.symbol), reverse=True))


def daily_decision_review_rows(reviews: Iterable[DailyDecisionReview]) -> tuple[dict[str, object], ...]:
    return tuple(
        {
            "Tarih": item.decision_date,
            "Faz": item.phase,
            "Hisse": item.symbol,
            "Öncelik": f"#{item.priority}",
            "Son ufuk": item.horizon,
            "Getiri (%)": round(item.return_pct, 2) if item.return_pct is not None else "-",
            "Sonuç": item.outcome,
            "Destekleyen kanıt": "; ".join(item.supporting_evidence) or "-",
            "Dikkat kanıtı": "; ".join(item.caution_evidence) or "-",
        }
        for item in reviews
    )


def daily_decision_review_summary(reviews: Iterable[DailyDecisionReview]) -> tuple[dict[str, object], ...]:
    buckets: dict[str, list[DailyDecisionReview]] = defaultdict(list)
    for item in reviews:
        buckets[item.decision_date].append(item)

    rows: list[dict[str, object]] = []
    for day in sorted(buckets, reverse=True):
        items = buckets[day]
        evaluated = [item for item in items if item.return_pct is not None]
        positives = [item for item in evaluated if item.return_pct is not None and item.return_pct > 0]
        negatives = [item for item in evaluated if item.return_pct is not None and item.return_pct <= 0]
        avg = sum(item.return_pct for item in evaluated if item.return_pct is not None) / len(evaluated) if evaluated else None
        rows.append(
            {
                "Tarih": day,
                "AL kararı": len(items),
                "Değerlendirilen": len(evaluated),
                "Pozitif": len(positives),
                "Negatif": len(negatives),
                "İsabet (%)": round((len(positives) / len(evaluated)) * 100.0, 1) if evaluated else "-",
                "Ort. getiri (%)": round(avg, 2) if avg is not None else "-",
            }
        )
    return tuple(rows)

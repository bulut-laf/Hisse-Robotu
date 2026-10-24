from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class DailyBuyDecision:
    priority: int
    symbol: str
    decision: str
    technical_score: int
    technical_view: str
    rank_change: int | None
    research_priority: str
    visibility_state: str | None
    volume_ratio: float
    risk_reward: float
    data_status: str
    reasons: tuple[str, ...]
    cautions: tuple[str, ...]


def _positive_technical(view: str) -> bool:
    return "pozitif" in str(view or "").casefold()


def _negative_technical(view: str) -> bool:
    value = str(view or "").casefold()
    return "negatif" in value or "olumsuz" in value


def _decision_for(card: object) -> tuple[str, tuple[str, ...], tuple[str, ...]]:
    score = int(getattr(card, "technical_score"))
    view = str(getattr(card, "technical_view", ""))
    priority = str(getattr(card, "research_priority", "NORMAL")).upper()
    visibility = str(getattr(card, "visibility_state", "") or "").upper()
    rank_change = getattr(card, "rank_change", None)
    volume = float(getattr(card, "volume_ratio", 0.0))
    rr = float(getattr(card, "risk_reward", 0.0))
    blocked = bool(getattr(card, "data_blocked", False))
    selection_source = str(getattr(card, "selection_source", "TARAMA") or "TARAMA").upper()
    jump_quality = str(getattr(card, "jump_quality", "-") or "-").upper()
    entry_readiness = str(getattr(card, "entry_readiness", "-") or "-").upper()

    reasons: list[str] = []
    cautions: list[str] = list(getattr(card, "risks", ()) or ())

    if _positive_technical(view):
        reasons.append("Teknik görünüm pozitif")
    if score >= 70:
        reasons.append(f"Teknik skor güçlü ({score})")
    if volume >= 1.0:
        reasons.append(f"Hacim teyidi mevcut ({volume:.2f})")
    if rr >= 1.5:
        reasons.append(f"Risk/getiri yeterli ({rr:.2f})")
    if priority == "HIGH":
        reasons.append("Araştırma önceliği yüksek")
    if rank_change is not None and int(rank_change) > 0:
        reasons.append(f"Sıralama iyileşiyor (+{int(rank_change)})")
    if visibility in {"IMPROVING", "RISING", "ACCELERATING"}:
        reasons.append(f"Erken görünürlük {visibility}")

    if blocked:
        cautions.append("Kısmi/gecikmeli veri — karar mevcut son güvenilir veriyle üretildi")
    if volume < 1.0:
        cautions.append(f"Hacim teyidi zayıf ({volume:.2f})")
    if rr < 1.5:
        cautions.append(f"Risk/getiri hedefin altında ({rr:.2f})")
    if rank_change is not None and int(rank_change) < 0:
        cautions.append(f"Sıralama geriliyor ({int(rank_change)})")

    jump_ready_for_buy = True
    if selection_source == "SICRAMA":
        if jump_quality not in {"UYGUN", "-"}:
            jump_ready_for_buy = False
            cautions.append("Sıçrama kalite kapısı AL için uygun değil")
        if entry_readiness not in {"GİRİŞE HAZIR", "-"}:
            jump_ready_for_buy = False
            cautions.append(f"Sıçrama giriş hazırlığı: {entry_readiness}")

    # Closeout yeni birleşik skor üretmez; mevcut kanıtlar için deterministik kapı uygular.
    if _negative_technical(view) or score < 55 or rr < 1.0:
        decision = "İŞLEM YOK"
    elif (
        _positive_technical(view)
        and score >= 70
        and rr >= 1.5
        and volume >= 1.0
        and jump_ready_for_buy
    ):
        decision = "AL"
    else:
        decision = "BEKLE"

    return decision, tuple(reasons), tuple(dict.fromkeys(cautions))


def build_daily_buy_decisions(cards: Iterable[object]) -> tuple[DailyBuyDecision, ...]:
    result: list[DailyBuyDecision] = []
    for index, card in enumerate(cards, start=1):
        decision, reasons, cautions = _decision_for(card)
        result.append(
            DailyBuyDecision(
                priority=index,
                symbol=str(getattr(card, "symbol", "")).strip().upper(),
                decision=decision,
                technical_score=int(getattr(card, "technical_score")),
                technical_view=str(getattr(card, "technical_view", "")),
                rank_change=(
                    int(getattr(card, "rank_change"))
                    if getattr(card, "rank_change", None) is not None
                    else None
                ),
                research_priority=str(getattr(card, "research_priority", "NORMAL")),
                visibility_state=(
                    str(getattr(card, "visibility_state"))
                    if getattr(card, "visibility_state", None) is not None
                    else None
                ),
                volume_ratio=float(getattr(card, "volume_ratio", 0.0)),
                risk_reward=float(getattr(card, "risk_reward", 0.0)),
                data_status=("KISMİ" if bool(getattr(card, "data_blocked", False)) else "UYGUN"),
                reasons=reasons,
                cautions=cautions,
            )
        )
    return tuple(result)


def daily_buy_decision_rows(decisions: Iterable[DailyBuyDecision]) -> tuple[dict[str, object], ...]:
    return tuple(
        {
            "Öncelik": f"#{item.priority}",
            "Hisse": item.symbol,
            "Karar": item.decision,
            "Teknik skor": item.technical_score,
            "Sıra değişimi": item.rank_change if item.rank_change is not None else "-",
            "Hacim": round(item.volume_ratio, 2),
            "Risk/Getiri": round(item.risk_reward, 2),
            "Veri": item.data_status,
            "Karar gerekçesi": " | ".join(item.reasons) or "-",
            "Dikkat": " | ".join(item.cautions) or "-",
        }
        for item in decisions
    )

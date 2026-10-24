from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


HIGH_CONFIDENCE = "AL — YÜKSEK GÜVEN"
NORMAL_CONFIDENCE = "AL — NORMAL GÜVEN"
WAIT = "BEKLE"
NO_TRADE = "İŞLEM YOK"

_SUPPORTIVE_VISIBILITY = {"IMPROVING", "RISING", "ACCELERATING"}


@dataclass(frozen=True)
class HistoricalSupport:
    status: str
    supportive_slices: int
    evaluated_slices: int
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class HighConvictionDecision:
    priority: int
    symbol: str
    base_decision: str
    conviction: str
    technical_gate: str
    volume_gate: str
    risk_reward_gate: str
    timing_gate: str
    entry_gate: str
    data_gate: str
    history_gate: str
    reasons: tuple[str, ...]
    blockers: tuple[str, ...]


def _positive_technical(view: object) -> bool:
    return "pozitif" in str(view or "").casefold()


def _score_segment(value: int) -> str:
    if value >= 80:
        return "80+"
    if value >= 70:
        return "70-79"
    return "<70"


def _ratio_segment(value: float, *, high: float, mid: float) -> str:
    if value >= high:
        return f">={high:g}"
    if value >= mid:
        return f"{mid:g}-{high:g}"
    return f"<{mid:g}"


def _relevant_calibration_keys(decision: object) -> tuple[tuple[str, str], ...]:
    return (
        ("Teknik skor", _score_segment(int(getattr(decision, "technical_score", 0)))),
        (
            "Hacim",
            _ratio_segment(
                float(getattr(decision, "volume_ratio", 0.0)), high=1.3, mid=1.0
            ),
        ),
        (
            "Risk/Getiri",
            _ratio_segment(
                float(getattr(decision, "risk_reward", 0.0)), high=2.0, mid=1.5
            ),
        ),
    )


def evaluate_historical_support(
    decision: object,
    calibration_slices: Iterable[object] = (),
) -> HistoricalSupport:
    """Use only existing outcome calibration; never creates a new score.

    High-confidence history support requires at least two supportive core
    calibration slices at 3S/5S. A slice is supportive only when the existing
    calibration layer already labels it DESTEKLEYİCİ with >=10 samples,
    >=60% hit rate and positive average return.
    """
    keys = set(_relevant_calibration_keys(decision))
    relevant = []
    for item in calibration_slices:
        key = (str(getattr(item, "dimension", "")), str(getattr(item, "segment", "")))
        horizon = str(getattr(item, "horizon", "")).upper()
        if key in keys and horizon in {"3S", "5S"}:
            relevant.append(item)

    supportive = []
    for item in relevant:
        sample_size = int(getattr(item, "sample_size", 0))
        hit_rate = getattr(item, "hit_rate", None)
        average_return = getattr(item, "average_return", None)
        status = str(getattr(item, "status", "")).upper()
        if (
            status == "DESTEKLEYİCİ"
            and sample_size >= 10
            and hit_rate is not None
            and float(hit_rate) >= 60.0
            and average_return is not None
            and float(average_return) > 0.0
        ):
            supportive.append(item)

    reasons = tuple(
        f"{getattr(item, 'dimension', '-')} {getattr(item, 'segment', '-')} "
        f"{getattr(item, 'horizon', '-')} · n={int(getattr(item, 'sample_size', 0))} · "
        f"isabet={float(getattr(item, 'hit_rate', 0.0)):.1f}% · "
        f"ort={float(getattr(item, 'average_return', 0.0)):.2f}%"
        for item in supportive
    )

    if len(supportive) >= 2:
        status = "DESTEKLEYİCİ"
    elif relevant:
        status = "YETERSİZ / KARIŞIK"
    else:
        status = "YETERSİZ VERİ"

    return HistoricalSupport(
        status=status,
        supportive_slices=len(supportive),
        evaluated_slices=len(relevant),
        reasons=reasons,
    )


def _timing_pass(card: object, decision: object) -> tuple[bool, str]:
    rank_change = getattr(decision, "rank_change", None)
    priority = str(getattr(decision, "research_priority", "NORMAL") or "NORMAL").upper()
    visibility = str(getattr(decision, "visibility_state", "") or "").upper()

    if rank_change is not None and int(rank_change) < 0:
        return False, f"Sıralama geriliyor ({int(rank_change)})"
    if rank_change is not None and int(rank_change) > 0:
        return True, f"Sıralama iyileşiyor (+{int(rank_change)})"
    if visibility in _SUPPORTIVE_VISIBILITY:
        return True, f"Erken görünürlük {visibility}"
    if priority == "HIGH":
        return True, "Araştırma önceliği HIGH"
    return False, "Pozitif zamanlama/ranking kanıtı yok"


def _entry_pass(card: object) -> tuple[bool, str]:
    source = str(getattr(card, "selection_source", "TARAMA") or "TARAMA").upper()
    quality = str(getattr(card, "jump_quality", "-") or "-").upper()
    readiness = str(getattr(card, "entry_readiness", "-") or "-").upper()

    if source == "SICRAMA":
        if quality != "UYGUN":
            return False, f"Sıçrama kalite kapısı {quality}"
        if readiness != "GİRİŞE HAZIR":
            return False, f"Giriş hazırlığı {readiness}"
        return True, "Sıçrama kalite + giriş hazırlığı uygun"

    if readiness in {"TEYİT BEKLİYOR", "ERKEN", "AŞIRI UZAMIŞ"}:
        return False, f"Giriş hazırlığı {readiness}"
    return True, "Mevcut giriş kapısı engel üretmiyor"


def build_high_conviction_buy_gate(
    cards: Iterable[object],
    decisions: Iterable[object],
    *,
    calibration_slices: Iterable[object] = (),
) -> tuple[HighConvictionDecision, ...]:
    """Classify existing daily decisions without changing the AL/SAT engine.

    This is a strict confidence overlay. It never upgrades BEKLE/İŞLEM YOK to AL,
    never changes existing thresholds, and creates no combined confidence score.
    """
    cards_by_symbol = {
        str(getattr(card, "symbol", "")).strip().upper(): card for card in cards
    }
    calibration = tuple(calibration_slices)
    result: list[HighConvictionDecision] = []

    for decision in decisions:
        symbol = str(getattr(decision, "symbol", "")).strip().upper()
        card = cards_by_symbol.get(symbol)
        base = str(getattr(decision, "decision", "")).upper()
        priority = int(getattr(decision, "priority", 0))

        score = int(getattr(decision, "technical_score", 0))
        view = str(getattr(decision, "technical_view", ""))
        volume = float(getattr(decision, "volume_ratio", 0.0))
        rr = float(getattr(decision, "risk_reward", 0.0))
        data_status = str(getattr(decision, "data_status", "UYGUN") or "UYGUN").upper()

        technical_ok = _positive_technical(view) and score >= 80
        volume_ok = volume >= 1.30
        rr_ok = rr >= 2.0
        timing_ok, timing_reason = _timing_pass(card, decision)
        entry_ok, entry_reason = _entry_pass(card) if card is not None else (False, "Aday kartı yok")
        data_ok = data_status == "UYGUN"
        history = evaluate_historical_support(decision, calibration)
        history_ok = history.status == "DESTEKLEYİCİ"

        reasons: list[str] = []
        blockers: list[str] = []

        if technical_ok:
            reasons.append(f"Teknik kapı geçti ({score})")
        else:
            blockers.append(f"Teknik kapı: pozitif görünüm + skor >=80 gerekli ({score})")
        if volume_ok:
            reasons.append(f"Hacim kapısı geçti ({volume:.2f})")
        else:
            blockers.append(f"Hacim kapısı: >=1.30 gerekli ({volume:.2f})")
        if rr_ok:
            reasons.append(f"Risk/getiri kapısı geçti ({rr:.2f})")
        else:
            blockers.append(f"Risk/getiri kapısı: >=2.00 gerekli ({rr:.2f})")
        if timing_ok:
            reasons.append(timing_reason)
        else:
            blockers.append(timing_reason)
        if entry_ok:
            reasons.append(entry_reason)
        else:
            blockers.append(entry_reason)
        if data_ok:
            reasons.append("Veri durumu UYGUN")
        else:
            blockers.append("Kısmi/gecikmeli veri yüksek güveni engelliyor")
        if history_ok:
            reasons.append("Outcome geçmişi destekleyici")
            reasons.extend(history.reasons)
        else:
            blockers.append(
                "Outcome geçmişi yüksek güven için henüz destekleyici değil "
                f"({history.supportive_slices}/{max(history.evaluated_slices, 1)} destekleyici dilim)"
            )

        if base != "AL":
            conviction = NO_TRADE if base == NO_TRADE else WAIT
        elif all((technical_ok, volume_ok, rr_ok, timing_ok, entry_ok, data_ok, history_ok)):
            conviction = HIGH_CONFIDENCE
        else:
            conviction = NORMAL_CONFIDENCE

        result.append(
            HighConvictionDecision(
                priority=priority,
                symbol=symbol,
                base_decision=base,
                conviction=conviction,
                technical_gate="GEÇTİ" if technical_ok else "KALDI",
                volume_gate="GEÇTİ" if volume_ok else "KALDI",
                risk_reward_gate="GEÇTİ" if rr_ok else "KALDI",
                timing_gate="GEÇTİ" if timing_ok else "KALDI",
                entry_gate="GEÇTİ" if entry_ok else "KALDI",
                data_gate="GEÇTİ" if data_ok else "KALDI",
                history_gate=history.status,
                reasons=tuple(dict.fromkeys(reasons)),
                blockers=tuple(dict.fromkeys(blockers)),
            )
        )

    return tuple(result)


def high_conviction_rows(
    decisions: Iterable[HighConvictionDecision],
) -> tuple[dict[str, object], ...]:
    return tuple(
        {
            "Öncelik": f"#{item.priority}",
            "Hisse": item.symbol,
            "Mevcut karar": item.base_decision,
            "Güven sonucu": item.conviction,
            "Teknik": item.technical_gate,
            "Hacim": item.volume_gate,
            "R/R": item.risk_reward_gate,
            "Zamanlama": item.timing_gate,
            "Giriş": item.entry_gate,
            "Veri": item.data_gate,
            "Geçmiş kanıt": item.history_gate,
            "Destek": " | ".join(item.reasons) or "-",
            "Eksik / engel": " | ".join(item.blockers) or "-",
        }
        for item in decisions
    )

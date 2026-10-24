from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class EarlyRadarDecision(str, Enum):
    YOK = "Yok"
    IZLE = "İzle"
    YUKSEK_ONCELIK = "Yüksek Öncelik"


class MaturityDecision(str, Enum):
    NORMAL = "Normal"
    OLGUNLASIYOR = "Olgunlaşıyor"
    KAR_KORUMA = "Kâr Koruma"


@dataclass(frozen=True)
class EarlyRadarInput:
    rank: int | None
    stage: str | None
    momentum: float | None
    rank_velocity: float | None
    score_velocity: float | None
    momentum_velocity: float | None
    sessions_since_first_seen: int
    realized_move_pct: float
    score: float | None = None
    resistance_distance_pct: float | None = None

    def __post_init__(self) -> None:
        if self.rank is not None and self.rank < 1:
            raise ValueError("rank 1 veya daha büyük olmalıdır.")
        if self.sessions_since_first_seen < 0:
            raise ValueError("sessions_since_first_seen negatif olamaz.")
        if self.score is not None and not 0 <= self.score <= 100:
            raise ValueError("score 0-100 arasında olmalıdır.")


@dataclass(frozen=True)
class EarlyRadarOutput:
    early_radar: EarlyRadarDecision
    maturity: MaturityDecision
    movement_phase: str
    priority_score: float
    new_entry_message: str
    position_message: str
    reasons: tuple[str, ...]


EARLY_STAGES = {"E0", "E1", "E2"}


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def _priority_score(data: EarlyRadarInput) -> float:
    """
    Ayrı bir erken-fırsat öncelik puanı.
    Ana Hisse Robotu teknik skorunu değiştirmez.
    """
    score = 0.0

    if data.rank is not None:
        if 11 <= data.rank <= 20:
            score += 30
        elif 21 <= data.rank <= 30:
            score += 26
        elif 6 <= data.rank <= 10:
            score += 16
        elif data.rank <= 5:
            score += 6
        elif data.rank <= 40:
            score += 10

    if (data.stage or "").upper() in EARLY_STAGES:
        score += 22

    if data.rank_velocity is not None:
        if data.rank_velocity >= 4:
            score += 18
        elif data.rank_velocity >= 2:
            score += 12
        elif data.rank_velocity > 0:
            score += 6

    if data.score_velocity is not None and data.score_velocity > 0:
        score += 8

    if data.momentum_velocity is not None and data.momentum_velocity > 0:
        score += 10

    # Hareket çok uzamışsa erken fırsat puanı düşer.
    if data.realized_move_pct >= 25:
        score -= 28
    elif data.realized_move_pct >= 18:
        score -= 18
    elif data.realized_move_pct >= 10:
        score -= 8

    if data.sessions_since_first_seen >= 8:
        score -= 12
    elif data.sessions_since_first_seen >= 6:
        score -= 6

    return _clamp(score)


def classify_early_radar(
    data: EarlyRadarInput,
    *,
    high_priority_threshold: float = 62.0,
    watch_threshold: float = 38.0,
    maturity_sessions: int = 6,
    maturity_move_pct: float = 18.0,
) -> EarlyRadarOutput:
    if high_priority_threshold <= watch_threshold:
        raise ValueError("high_priority_threshold, watch_threshold değerinden büyük olmalıdır.")
    if maturity_sessions < 1:
        raise ValueError("maturity_sessions en az 1 olmalıdır.")
    if maturity_move_pct <= 0:
        raise ValueError("maturity_move_pct pozitif olmalıdır.")

    reasons: list[str] = []
    priority = _priority_score(data)
    stage = (data.stage or "").upper()

    if data.rank is not None and 11 <= data.rank <= 30:
        reasons.append("Aday erken radar sıra bandında.")
    if stage in EARLY_STAGES:
        reasons.append(f"Aday erken PreBreakout aşamasında ({stage}).")
    if data.rank_velocity is not None and data.rank_velocity > 0:
        reasons.append("Sıralama ivmesi yukarı.")
    if data.momentum_velocity is not None and data.momentum_velocity > 0:
        reasons.append("Momentum ivmesi yukarı.")

    mature_by_rank = data.rank is not None and data.rank <= 5
    mature_by_age = data.sessions_since_first_seen >= maturity_sessions
    mature_by_move = data.realized_move_pct >= maturity_move_pct

    if mature_by_rank and (mature_by_age or mature_by_move):
        maturity = MaturityDecision.KAR_KORUMA
        reasons.append("İlk 5'e ulaştığında hareket yaşı/getirisi olgunluk eşiğinde.")
    elif mature_by_rank or mature_by_age or mature_by_move:
        maturity = MaturityDecision.OLGUNLASIYOR
        reasons.append("Hareket olgunlaşma kontrolünde.")
    else:
        maturity = MaturityDecision.NORMAL

    if maturity is MaturityDecision.KAR_KORUMA:
        early = EarlyRadarDecision.YOK
        movement_phase = "OLGUN"
        new_entry_message = "Yeni giriş için geç olabilir; teyit sonrası risk/ödül yeniden değerlendir."
        position_message = "Mevcut pozisyonda kâr koruma / stop sıkılaştırma değerlendirmesi."
    else:
        if priority >= high_priority_threshold:
            early = EarlyRadarDecision.YUKSEK_ONCELIK
        elif priority >= watch_threshold:
            early = EarlyRadarDecision.IZLE
        else:
            early = EarlyRadarDecision.YOK

        if maturity is MaturityDecision.OLGUNLASIYOR:
            movement_phase = "GÜÇLÜ / OLGUNLAŞIYOR"
            new_entry_message = "Yeni girişte hareket yaşını ve kalan risk/ödülü kontrol et."
            position_message = "Pozisyon varsa momentum bozulmasını izle."
        elif early is EarlyRadarDecision.YUKSEK_ONCELIK:
            movement_phase = "ERKEN / GELİŞİYOR"
            new_entry_message = "Erken Radar yüksek öncelik: teyit koşulları yakından izlenmeli."
            position_message = "Pozisyon yoksa izleme adayı; mevcut pozisyon varsa trend korunuyor."
        elif early is EarlyRadarDecision.IZLE:
            movement_phase = "HAZIRLIK / GELİŞİYOR"
            new_entry_message = "Erken Radar izleme: henüz yüksek öncelik değil."
            position_message = "Güçlenme ve teyit devamı izlenmeli."
        else:
            movement_phase = "NÖTR"
            new_entry_message = "Erken fırsat sinyali yok."
            position_message = "Mevcut teknik plan korunur."

    return EarlyRadarOutput(
        early_radar=early,
        maturity=maturity,
        movement_phase=movement_phase,
        priority_score=priority,
        new_entry_message=new_entry_message,
        position_message=position_message,
        reasons=tuple(reasons),
    )


def as_display_dict(output: EarlyRadarOutput) -> dict[str, object]:
    return {
        "Erken Radar": output.early_radar.value,
        "Erken Fırsat Puanı": round(output.priority_score, 1),
        "Hareket Fazı": output.movement_phase,
        "Olgunlaşma": output.maturity.value,
        "Yeni Giriş": output.new_entry_message,
        "Mevcut Pozisyon": output.position_message,
        "Gerekçeler": list(output.reasons),
    }

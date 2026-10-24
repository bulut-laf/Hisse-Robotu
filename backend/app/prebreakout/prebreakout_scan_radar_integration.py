from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from backend.app.prebreakout.prebreakout_early_radar import (
    EarlyRadarInput,
    classify_early_radar,
)
from backend.app.prebreakout.prebreakout_early_radar_ui import (
    EarlyRadarCard,
    card_from_output,
)


@dataclass(frozen=True)
class ScanCandidateSnapshot:
    symbol: str
    rank: int | None
    stage: str | None
    momentum: float | None
    score: float | None
    resistance_distance_pct: float | None
    sessions_since_first_seen: int
    realized_move_pct: float
    rank_velocity: float | None
    score_velocity: float | None
    momentum_velocity: float | None

    def __post_init__(self) -> None:
        if not self.symbol.strip():
            raise ValueError("symbol boş olamaz.")
        if self.rank is not None and self.rank < 1:
            raise ValueError("rank 1 veya daha büyük olmalıdır.")
        if self.sessions_since_first_seen < 0:
            raise ValueError("sessions_since_first_seen negatif olamaz.")
        if self.score is not None and not 0 <= self.score <= 100:
            raise ValueError("score 0-100 arasında olmalıdır.")


def candidate_to_radar_input(candidate: ScanCandidateSnapshot) -> EarlyRadarInput:
    return EarlyRadarInput(
        rank=candidate.rank,
        stage=candidate.stage,
        momentum=candidate.momentum,
        rank_velocity=candidate.rank_velocity,
        score_velocity=candidate.score_velocity,
        momentum_velocity=candidate.momentum_velocity,
        sessions_since_first_seen=candidate.sessions_since_first_seen,
        realized_move_pct=candidate.realized_move_pct,
        score=candidate.score,
        resistance_distance_pct=candidate.resistance_distance_pct,
    )


def candidate_to_card(candidate: ScanCandidateSnapshot) -> EarlyRadarCard:
    output = classify_early_radar(candidate_to_radar_input(candidate))
    return card_from_output(candidate.symbol, output)


def build_radar_cards(
    candidates: Iterable[ScanCandidateSnapshot],
) -> list[EarlyRadarCard]:
    return [candidate_to_card(candidate) for candidate in candidates]


def snapshot_from_mapping(row: Mapping[str, object]) -> ScanCandidateSnapshot:
    """
    Tarama/export satırlarından entegrasyon için güvenli dönüştürücü.
    Türkçe veya sade anahtarları kabul eder; eksik geçmiş metrikleri None/0 kalabilir.
    """
    def first(*keys: str, default=None):
        for key in keys:
            if key in row:
                return row[key]
        return default

    symbol = first("symbol", "Hisse")
    if symbol is None:
        raise ValueError("Hisse/symbol alanı zorunludur.")

    rank = first("rank", "Sıra")
    stage = first("stage", "Kesim sınıfı")
    momentum = first("momentum", "Momentum")
    score = first("score", "Teknik skor", default=None)
    resistance_distance = first(
        "resistance_distance_pct",
        "Dirence uzaklık (%)",
        default=None,
    )

    return ScanCandidateSnapshot(
        symbol=str(symbol),
        rank=None if rank in (None, "") else int(rank),
        stage=None if stage in (None, "") else str(stage),
        momentum=None if momentum in (None, "") else float(momentum),
        score=None if score in (None, "") else float(score),
        resistance_distance_pct=(
            None
            if resistance_distance in (None, "")
            else float(resistance_distance)
        ),
        sessions_since_first_seen=int(
            first("sessions_since_first_seen", "Hareket yaşı", default=0) or 0
        ),
        realized_move_pct=float(
            first("realized_move_pct", "Gerçekleşmiş hareket (%)", default=0.0) or 0.0
        ),
        rank_velocity=_optional_float(
            first("rank_velocity", "Sıra ivmesi", default=None)
        ),
        score_velocity=_optional_float(
            first("score_velocity", "Skor ivmesi", default=None)
        ),
        momentum_velocity=_optional_float(
            first("momentum_velocity", "Momentum ivmesi", default=None)
        ),
    )


def _optional_float(value: object) -> float | None:
    if value in (None, ""):
        return None
    return float(value)


def build_radar_cards_from_rows(
    rows: Iterable[Mapping[str, object]],
) -> list[EarlyRadarCard]:
    return build_radar_cards(snapshot_from_mapping(row) for row in rows)

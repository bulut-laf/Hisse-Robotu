from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal


@dataclass(frozen=True)
class ScoreComponent:
    code: str
    score: Decimal
    weight: Decimal
    reason: str


@dataclass(frozen=True)
class InvestabilityResult:
    symbol: str
    as_of_date: date
    score: int | None
    label: str
    locked: bool
    components: tuple[ScoreComponent, ...]
    strengths: tuple[str, ...]
    risks: tuple[str, ...]
    explanation: str
    confidence: str
    engine_version: str


@dataclass(frozen=True)
class MarketContextInput:
    technical_trend: Decimal | None = None
    relative_strength: Decimal | None = None
    volume_liquidity: Decimal | None = None
    catalyst: Decimal | None = None
    entry_risk: Decimal | None = None
    earnings_surprise: Decimal | None = None


@dataclass(frozen=True)
class LongTermContextInput:
    business_quality: Decimal | None = None
    growth_durability: Decimal | None = None
    governance: Decimal | None = None
    sector_risk: Decimal | None = None


@dataclass(frozen=True)
class IntelligencePanelPayload:
    symbol: str
    as_of: datetime
    financial_health_score: int | None
    financial_health_grade: str
    financial_risk: str
    valuation_status: str | None
    current_price: Decimal | None
    bear_value: Decimal | None
    base_value: Decimal | None
    bull_value: Decimal | None
    upside_downside_to_base: Decimal | None
    margin_of_safety_status: str | None
    short_term_score: int | None
    short_term_label: str
    long_term_score: int | None
    long_term_label: str
    confidence: str
    strengths: tuple[str, ...]
    risks: tuple[str, ...]
    what_to_watch_next: tuple[str, ...]
    read_only: bool = True
    schema_version: str = "fin015-v1"


@dataclass(frozen=True)
class PointInTimeObservation:
    observation_date: date
    publication_date: date
    score: int | None
    forward_return: Decimal | None


@dataclass(frozen=True)
class CalibrationSummary:
    sample_size: int
    usable_size: int
    mean_forward_return: Decimal | None
    high_score_mean_return: Decimal | None
    low_score_mean_return: Decimal | None
    separation: Decimal | None
    status: str

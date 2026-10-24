from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from enum import Enum
from typing import Iterable

import pandas as pd


class MissedOpportunityReason(str, Enum):
    MOMENTUM = "Momentum"
    RSI_EGIMI = "RSI eğimi"
    MACD_EGIMI = "MACD histogram eğimi"
    ASAMA_KAPISI = "Aşama kapısı"
    VERI_EKSIK = "Veri eksikliği"
    DIGER = "Diğer"
    BILINMIYOR = "Bilinmiyor"


_REASON_ALIASES = {
    "momentum": MissedOpportunityReason.MOMENTUM,
    "momentum_score": MissedOpportunityReason.MOMENTUM,
    "momentum skoru": MissedOpportunityReason.MOMENTUM,
    "rsi": MissedOpportunityReason.RSI_EGIMI,
    "rsi_slope": MissedOpportunityReason.RSI_EGIMI,
    "rsi eğimi": MissedOpportunityReason.RSI_EGIMI,
    "macd": MissedOpportunityReason.MACD_EGIMI,
    "macd_hist_slope": MissedOpportunityReason.MACD_EGIMI,
    "macd histogram eğimi": MissedOpportunityReason.MACD_EGIMI,
    "stage": MissedOpportunityReason.ASAMA_KAPISI,
    "stage_gate": MissedOpportunityReason.ASAMA_KAPISI,
    "aşama": MissedOpportunityReason.ASAMA_KAPISI,
    "aşama kapısı": MissedOpportunityReason.ASAMA_KAPISI,
    "data": MissedOpportunityReason.VERI_EKSIK,
    "missing_data": MissedOpportunityReason.VERI_EKSIK,
    "veri eksikliği": MissedOpportunityReason.VERI_EKSIK,
    "other": MissedOpportunityReason.DIGER,
    "diğer": MissedOpportunityReason.DIGER,
}


@dataclass(frozen=True)
class HistoricalCandidateDecision:
    symbol: str
    cut_date: str
    selected: bool
    future_session_count: int
    close_return_20_pct: float | None
    max_return_20_pct: float | None
    rejected_by: tuple[str, ...] = ()


@dataclass(frozen=True)
class MissedOpportunity:
    symbol: str
    cut_date: str
    max_return_20_pct: float
    close_return_20_pct: float | None
    primary_reason: MissedOpportunityReason
    all_reasons: tuple[MissedOpportunityReason, ...]


@dataclass(frozen=True)
class MissedOpportunityReasonRow:
    reason: MissedOpportunityReason
    rejected_count: int
    missed_strong_move_count: int
    missed_rate_pct: float | None
    average_missed_max_return_pct: float | None
    potentially_too_strict: bool


@dataclass(frozen=True)
class MissedOpportunityReport:
    evaluated_count: int
    rejected_count: int
    complete_rejected_count: int
    missed_strong_move_count: int
    missed_opportunity_rate_pct: float | None
    strong_move_threshold_pct: float
    minimum_future_sessions: int
    sufficient_sample: bool
    minimum_required_rejected_sample: int
    opportunities: tuple[MissedOpportunity, ...]
    reason_rows: tuple[MissedOpportunityReasonRow, ...]
    note: str


def _round(value: float | None) -> float | None:
    return None if value is None else round(float(value), 4)


def _rate(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return _round(numerator * 100.0 / denominator)


def _normalize_reason(value: str) -> MissedOpportunityReason:
    key = str(value).strip().casefold()
    if not key:
        return MissedOpportunityReason.BILINMIYOR
    return _REASON_ALIASES.get(key, MissedOpportunityReason.DIGER)


def _normalized_reasons(values: Iterable[str]) -> tuple[MissedOpportunityReason, ...]:
    result: list[MissedOpportunityReason] = []
    for value in values:
        reason = _normalize_reason(value)
        if reason not in result:
            result.append(reason)
    return tuple(result) if result else (MissedOpportunityReason.BILINMIYOR,)


def _primary_reason(reasons: tuple[MissedOpportunityReason, ...]) -> MissedOpportunityReason:
    # Veri eksikliği bir eşik sertliği değildir; önce veri kalitesini görünür yaparız.
    priority = (
        MissedOpportunityReason.VERI_EKSIK,
        MissedOpportunityReason.MOMENTUM,
        MissedOpportunityReason.RSI_EGIMI,
        MissedOpportunityReason.MACD_EGIMI,
        MissedOpportunityReason.ASAMA_KAPISI,
        MissedOpportunityReason.DIGER,
        MissedOpportunityReason.BILINMIYOR,
    )
    for item in priority:
        if item in reasons:
            return item
    return MissedOpportunityReason.BILINMIYOR


def kacirilan_firsatlari_degerlendir(
    decisions: Iterable[HistoricalCandidateDecision],
    *,
    strong_move_threshold_pct: float = 10.0,
    minimum_future_sessions: int = 20,
    minimum_required_rejected_sample: int = 30,
    too_strict_missed_rate_pct: float = 20.0,
    too_strict_minimum_missed_count: int = 3,
) -> MissedOpportunityReport:
    """Seçilmeyen fakat sonradan güçlü yükselen örnekleri post-hoc analiz eder.

    Gelecek getirileri yalnız performans ölçümü için kullanılır. Bu fonksiyon aday
    üretmez, geçmiş kararları değiştirmez ve hiçbir eşiği otomatik olarak güncellemez.
    """
    if strong_move_threshold_pct <= 0:
        raise ValueError("Güçlü hareket eşiği pozitif olmalıdır.")
    if minimum_future_sessions < 1:
        raise ValueError("Minimum gelecek seans sayısı en az 1 olmalıdır.")
    if minimum_required_rejected_sample < 1:
        raise ValueError("Minimum reddedilen örneklem en az 1 olmalıdır.")
    if not 0 <= too_strict_missed_rate_pct <= 100:
        raise ValueError("Sert filtre oran eşiği 0-100 aralığında olmalıdır.")
    if too_strict_minimum_missed_count < 1:
        raise ValueError("Sert filtre minimum kaçırılan fırsat sayısı en az 1 olmalıdır.")

    rows = tuple(decisions)
    rejected = tuple(item for item in rows if not item.selected)
    complete_rejected = tuple(
        item
        for item in rejected
        if item.future_session_count >= minimum_future_sessions
        and item.max_return_20_pct is not None
    )

    rejected_by_reason: Counter[MissedOpportunityReason] = Counter()
    missed_by_reason: Counter[MissedOpportunityReason] = Counter()
    missed_max_returns: dict[MissedOpportunityReason, list[float]] = defaultdict(list)

    for item in complete_rejected:
        reasons = _normalized_reasons(item.rejected_by)
        for reason in reasons:
            rejected_by_reason[reason] += 1

    opportunities: list[MissedOpportunity] = []
    for item in complete_rejected:
        max_return = float(item.max_return_20_pct)
        if max_return < strong_move_threshold_pct:
            continue
        reasons = _normalized_reasons(item.rejected_by)
        opportunity = MissedOpportunity(
            symbol=item.symbol,
            cut_date=item.cut_date,
            max_return_20_pct=_round(max_return) or 0.0,
            close_return_20_pct=_round(item.close_return_20_pct),
            primary_reason=_primary_reason(reasons),
            all_reasons=reasons,
        )
        opportunities.append(opportunity)
        for reason in reasons:
            missed_by_reason[reason] += 1
            missed_max_returns[reason].append(max_return)

    all_reasons = tuple(
        reason
        for reason in MissedOpportunityReason
        if rejected_by_reason[reason] > 0 or missed_by_reason[reason] > 0
    )
    reason_rows: list[MissedOpportunityReasonRow] = []
    for reason in all_reasons:
        rejected_count = rejected_by_reason[reason]
        missed_count = missed_by_reason[reason]
        missed_rate = _rate(missed_count, rejected_count)
        too_strict = (
            reason not in {MissedOpportunityReason.VERI_EKSIK, MissedOpportunityReason.BILINMIYOR}
            and missed_count >= too_strict_minimum_missed_count
            and missed_rate is not None
            and missed_rate >= too_strict_missed_rate_pct
        )
        reason_rows.append(
            MissedOpportunityReasonRow(
                reason=reason,
                rejected_count=rejected_count,
                missed_strong_move_count=missed_count,
                missed_rate_pct=missed_rate,
                average_missed_max_return_pct=(
                    _round(sum(missed_max_returns[reason]) / len(missed_max_returns[reason]))
                    if missed_max_returns[reason]
                    else None
                ),
                potentially_too_strict=too_strict,
            )
        )

    reason_rows.sort(
        key=lambda item: (
            item.potentially_too_strict,
            item.missed_strong_move_count,
            item.missed_rate_pct or 0.0,
        ),
        reverse=True,
    )
    sufficient = len(complete_rejected) >= minimum_required_rejected_sample
    if sufficient:
        note = (
            f"Örneklem yeterli: {len(complete_rejected)} tamamlanmış reddedilen karar; "
            "filtre sertliği yalnız tarihsel karşılaştırma için değerlendirilebilir."
        )
    else:
        note = (
            f"Erken değerlendirme: {len(complete_rejected)}/{minimum_required_rejected_sample} "
            "tamamlanmış reddedilen karar; eşik değişikliği için kesin hüküm verilmemeli."
        )

    return MissedOpportunityReport(
        evaluated_count=len(rows),
        rejected_count=len(rejected),
        complete_rejected_count=len(complete_rejected),
        missed_strong_move_count=len(opportunities),
        missed_opportunity_rate_pct=_rate(len(opportunities), len(complete_rejected)),
        strong_move_threshold_pct=float(strong_move_threshold_pct),
        minimum_future_sessions=minimum_future_sessions,
        sufficient_sample=sufficient,
        minimum_required_rejected_sample=minimum_required_rejected_sample,
        opportunities=tuple(opportunities),
        reason_rows=tuple(reason_rows),
        note=note,
    )


def kacirilan_firsatlar_tablosu(report: MissedOpportunityReport) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Sembol": item.symbol,
                "Kesim tarihi": item.cut_date,
                "20G en yüksek (%)": item.max_return_20_pct,
                "20G kapanış (%)": item.close_return_20_pct,
                "Birincil elenme nedeni": item.primary_reason.value,
                "Tüm elenme nedenleri": ", ".join(reason.value for reason in item.all_reasons),
            }
            for item in report.opportunities
        ]
    )


def filtre_etki_tablosu(report: MissedOpportunityReport) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Filtre": row.reason.value,
                "Reddedilen": row.rejected_count,
                "Kaçırılan güçlü hareket": row.missed_strong_move_count,
                "Kaçırma oranı (%)": row.missed_rate_pct,
                "Ort. kaçırılan tepe (%)": row.average_missed_max_return_pct,
                "Potansiyel fazla sert": "Evet" if row.potentially_too_strict else "Hayır",
            }
            for row in report.reason_rows
        ]
    )

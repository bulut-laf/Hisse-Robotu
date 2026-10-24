from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from typing import Iterable

import pandas as pd


class MarketRegime(str, Enum):
    YUKSELEN = "Yükselen"
    YATAY = "Yatay"
    ZAYIF = "Zayıf"
    BILINMIYOR = "Bilinmiyor"


_REGIME_ALIASES = {
    "yükselen": MarketRegime.YUKSELEN,
    "yukselen": MarketRegime.YUKSELEN,
    "bull": MarketRegime.YUKSELEN,
    "bullish": MarketRegime.YUKSELEN,
    "up": MarketRegime.YUKSELEN,
    "yatay": MarketRegime.YATAY,
    "sideways": MarketRegime.YATAY,
    "neutral": MarketRegime.YATAY,
    "zayıf": MarketRegime.ZAYIF,
    "zayif": MarketRegime.ZAYIF,
    "bear": MarketRegime.ZAYIF,
    "bearish": MarketRegime.ZAYIF,
    "down": MarketRegime.ZAYIF,
}


@dataclass(frozen=True)
class RegimeCandidateResult:
    symbol: str
    signal_date: str
    stage: str
    market_regime: str | MarketRegime
    future_session_count: int
    close_return_20_pct: float | None
    max_return_20_pct: float | None
    outcome_label: str | None = None


@dataclass(frozen=True)
class RegimeStagePerformanceRow:
    market_regime: MarketRegime
    stage: str
    sample_count: int
    successful_count: int
    limited_count: int
    unsuccessful_count: int
    success_rate_pct: float | None
    average_close_return_20_pct: float | None
    average_max_return_20_pct: float | None
    sufficient_sample: bool


@dataclass(frozen=True)
class RegimePerformanceReport:
    evaluated_count: int
    complete_count: int
    minimum_future_sessions: int
    minimum_sample_per_group: int
    success_threshold_pct: float
    rows: tuple[RegimeStagePerformanceRow, ...]
    sufficient_group_count: int
    best_reliable_regime: MarketRegime | None
    best_reliable_stage: str | None
    note: str


def _round(value: float | None) -> float | None:
    return None if value is None else round(float(value), 4)


def _normalize_regime(value: str | MarketRegime) -> MarketRegime:
    if isinstance(value, MarketRegime):
        return value
    key = str(value).strip().casefold()
    return _REGIME_ALIASES.get(key, MarketRegime.BILINMIYOR)


def _normalize_stage(value: str) -> str:
    stage = str(value).strip().upper()
    return stage if stage in {"E2", "E3", "E4"} else stage


def _label_result(item: RegimeCandidateResult, success_threshold_pct: float) -> str:
    label = (item.outcome_label or "").strip().casefold()
    if label in {"başarılı", "basarili", "successful", "success"}:
        return "Başarılı"
    if label in {"sınırlı hareket", "sinirli hareket", "limited", "limited move"}:
        return "Sınırlı hareket"
    if label in {"başarısız", "basarisiz", "failed", "failure", "unsuccessful"}:
        return "Başarısız"

    close20 = item.close_return_20_pct
    max20 = item.max_return_20_pct
    if max20 is not None and float(max20) >= success_threshold_pct and (close20 is None or float(close20) >= 0.0):
        return "Başarılı"
    if max20 is not None and float(max20) >= success_threshold_pct:
        return "Sınırlı hareket"
    return "Başarısız"


def piyasa_rejimine_gore_performansi_degerlendir(
    results: Iterable[RegimeCandidateResult],
    *,
    minimum_future_sessions: int = 20,
    minimum_sample_per_group: int = 10,
    success_threshold_pct: float = 10.0,
) -> RegimePerformanceReport:
    """E2-E4 sonuçlarını piyasa rejimi bazında post-hoc karşılaştırır.

    Bu analiz geçmiş sinyal sonucunu ölçer; aday üretim kurallarını veya eşikleri
    otomatik değiştirmez. Eksik 20 seans sonuçları başarı oranına dahil edilmez.
    """
    if minimum_future_sessions < 1:
        raise ValueError("Minimum gelecek seans sayısı en az 1 olmalıdır.")
    if minimum_sample_per_group < 1:
        raise ValueError("Minimum grup örneklemi en az 1 olmalıdır.")
    if success_threshold_pct <= 0:
        raise ValueError("Başarı hareket eşiği pozitif olmalıdır.")

    raw = tuple(results)
    complete = tuple(
        item
        for item in raw
        if _normalize_stage(item.stage) in {"E2", "E3", "E4"}
        and item.future_session_count >= minimum_future_sessions
        and item.max_return_20_pct is not None
    )

    groups: dict[tuple[MarketRegime, str], list[RegimeCandidateResult]] = defaultdict(list)
    for item in complete:
        groups[(_normalize_regime(item.market_regime), _normalize_stage(item.stage))].append(item)

    rows: list[RegimeStagePerformanceRow] = []
    for regime in (MarketRegime.YUKSELEN, MarketRegime.YATAY, MarketRegime.ZAYIF, MarketRegime.BILINMIYOR):
        for stage in ("E2", "E3", "E4"):
            items = groups.get((regime, stage), [])
            if not items:
                continue
            labels = [_label_result(item, success_threshold_pct) for item in items]
            successful = labels.count("Başarılı")
            limited = labels.count("Sınırlı hareket")
            unsuccessful = labels.count("Başarısız")
            close_values = [float(item.close_return_20_pct) for item in items if item.close_return_20_pct is not None]
            max_values = [float(item.max_return_20_pct) for item in items if item.max_return_20_pct is not None]
            count = len(items)
            rows.append(
                RegimeStagePerformanceRow(
                    market_regime=regime,
                    stage=stage,
                    sample_count=count,
                    successful_count=successful,
                    limited_count=limited,
                    unsuccessful_count=unsuccessful,
                    success_rate_pct=_round(successful * 100.0 / count),
                    average_close_return_20_pct=_round(sum(close_values) / len(close_values)) if close_values else None,
                    average_max_return_20_pct=_round(sum(max_values) / len(max_values)) if max_values else None,
                    sufficient_sample=count >= minimum_sample_per_group,
                )
            )

    reliable = [row for row in rows if row.sufficient_sample and row.market_regime is not MarketRegime.BILINMIYOR]
    reliable.sort(
        key=lambda row: (
            row.success_rate_pct if row.success_rate_pct is not None else -1.0,
            row.average_close_return_20_pct if row.average_close_return_20_pct is not None else -999999.0,
            row.sample_count,
        ),
        reverse=True,
    )
    best = reliable[0] if reliable else None
    if best is None:
        note = "Yeterli rejim/aşama örneklemi yok; en iyi rejim veya aşama için kesin hüküm verilmemeli."
    else:
        note = (
            f"Yeterli örneklemli gruplar içinde temkinli lider: {best.market_regime.value} / {best.stage}; "
            "sonuç yalnız tarihsel doğrulama içindir, üretim eşikleri otomatik değiştirilmez."
        )

    return RegimePerformanceReport(
        evaluated_count=len(raw),
        complete_count=len(complete),
        minimum_future_sessions=minimum_future_sessions,
        minimum_sample_per_group=minimum_sample_per_group,
        success_threshold_pct=float(success_threshold_pct),
        rows=tuple(rows),
        sufficient_group_count=len(reliable),
        best_reliable_regime=best.market_regime if best else None,
        best_reliable_stage=best.stage if best else None,
        note=note,
    )


def rejim_performans_tablosu(report: RegimePerformanceReport) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Piyasa rejimi": row.market_regime.value,
                "Aşama": row.stage,
                "Örneklem": row.sample_count,
                "Başarılı": row.successful_count,
                "Sınırlı hareket": row.limited_count,
                "Başarısız": row.unsuccessful_count,
                "Başarı oranı (%)": row.success_rate_pct,
                "Ort. 20G kapanış (%)": row.average_close_return_20_pct,
                "Ort. 20G en yüksek (%)": row.average_max_return_20_pct,
                "Örneklem yeterli": row.sufficient_sample,
            }
            for row in report.rows
        ]
    )


def rejim_ozet_tablosu(report: RegimePerformanceReport) -> pd.DataFrame:
    aggregate: dict[MarketRegime, list[RegimeStagePerformanceRow]] = defaultdict(list)
    for row in report.rows:
        aggregate[row.market_regime].append(row)

    rows: list[dict[str, object]] = []
    for regime in (MarketRegime.YUKSELEN, MarketRegime.YATAY, MarketRegime.ZAYIF, MarketRegime.BILINMIYOR):
        items = aggregate.get(regime, [])
        if not items:
            continue
        sample_count = sum(item.sample_count for item in items)
        successful = sum(item.successful_count for item in items)
        sufficient = sample_count >= report.minimum_sample_per_group
        rows.append(
            {
                "Piyasa rejimi": regime.value,
                "Toplam örneklem": sample_count,
                "Başarı oranı (%)": _round(successful * 100.0 / sample_count) if sample_count else None,
                "Örneklem yeterli": sufficient,
            }
        )
    return pd.DataFrame(rows)

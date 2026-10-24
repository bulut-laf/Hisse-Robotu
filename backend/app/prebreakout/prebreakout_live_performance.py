from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from enum import Enum
import json
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from backend.app.prebreakout.prebreakout_candidate_lifecycle import CandidatePriceObservation
from backend.app.prebreakout.prebreakout_live_watch import PreBreakoutLiveSignal

DEFAULT_LIVE_PERFORMANCE_PATH = Path("backend/data/prebreakout_live_performance.json")
LIVE_PERFORMANCE_HORIZONS = (5, 10, 20)


class LivePerformanceLabel(str, Enum):
    BASARILI = "Başarılı"
    SINIRLI_HAREKET = "Sınırlı hareket"
    BASARISIZ = "Başarısız"
    OLCULEMIYOR = "Ölçülemiyor"


@dataclass(frozen=True)
class LiveHorizonPerformance:
    horizon: int
    measured_session_count: int
    close_return_pct: float | None
    max_return_pct: float | None
    min_return_pct: float | None
    max_drawdown_pct: float | None


@dataclass(frozen=True)
class LiveSignalPerformance:
    signal_id: str
    symbol: str
    signal_date: str
    signal_stage: str
    entry_close: float
    as_of_date: str
    available_session_count: int
    label: LivePerformanceLabel
    horizons: tuple[LiveHorizonPerformance, ...]
    note: str


def _return_pct(value: float, base: float) -> float:
    if base <= 0:
        raise ValueError("Giriş kapanışı pozitif olmalıdır.")
    return round(((float(value) / float(base)) - 1.0) * 100.0, 10)


def _maximum_drawdown_pct(observations: Sequence[CandidatePriceObservation]) -> float | None:
    if not observations:
        return None
    peak = float(observations[0].close)
    maximum_drawdown = 0.0
    for item in observations:
        close = float(item.close)
        if close > peak:
            peak = close
        drawdown = _return_pct(close, peak)
        maximum_drawdown = min(maximum_drawdown, drawdown)
    return maximum_drawdown


def _horizon_performance(
    signal: PreBreakoutLiveSignal,
    observations: Sequence[CandidatePriceObservation],
    horizon: int,
) -> LiveHorizonPerformance:
    measured = tuple(observations[:horizon])
    if len(measured) < horizon:
        return LiveHorizonPerformance(
            horizon=horizon,
            measured_session_count=len(measured),
            close_return_pct=None,
            max_return_pct=None,
            min_return_pct=None,
            max_drawdown_pct=None,
        )

    return LiveHorizonPerformance(
        horizon=horizon,
        measured_session_count=horizon,
        close_return_pct=_return_pct(measured[-1].close, signal.close),
        max_return_pct=max(_return_pct(item.high, signal.close) for item in measured),
        min_return_pct=min(_return_pct(item.low, signal.close) for item in measured),
        max_drawdown_pct=_maximum_drawdown_pct(measured),
    )


def canli_performans_etiketi_belirle(
    horizons: Sequence[LiveHorizonPerformance],
) -> LivePerformanceLabel:
    by_horizon = {item.horizon: item for item in horizons}
    result_20 = by_horizon.get(20)
    if result_20 is None or result_20.close_return_pct is None:
        return LivePerformanceLabel.OLCULEMIYOR

    close_return = result_20.close_return_pct
    maximum_return = result_20.max_return_pct or 0.0
    minimum_return = result_20.min_return_pct or 0.0

    if close_return >= 5.0 and maximum_return >= 10.0:
        return LivePerformanceLabel.BASARILI
    if close_return <= -5.0 or minimum_return <= -10.0:
        return LivePerformanceLabel.BASARISIZ
    if maximum_return >= 5.0 or close_return > 0.0:
        return LivePerformanceLabel.SINIRLI_HAREKET
    return LivePerformanceLabel.BASARISIZ


def canli_sinyal_performansini_hesapla(
    signal: PreBreakoutLiveSignal,
    observations: Sequence[CandidatePriceObservation],
    *,
    as_of_date: date | None = None,
    horizons: Sequence[int] = LIVE_PERFORMANCE_HORIZONS,
) -> LiveSignalPerformance:
    signal_day = date.fromisoformat(signal.signal_date)
    ordered = tuple(
        sorted(
            (item for item in observations if item.observation_date > signal_day),
            key=lambda item: item.observation_date,
        )
    )
    normalized_horizons = tuple(sorted({int(item) for item in horizons}))
    if not normalized_horizons or normalized_horizons[0] < 1:
        raise ValueError("Performans vadeleri pozitif olmalıdır.")

    horizon_rows = tuple(
        _horizon_performance(signal, ordered, horizon)
        for horizon in normalized_horizons
    )
    label = canli_performans_etiketi_belirle(horizon_rows)
    effective_date = as_of_date or (ordered[-1].observation_date if ordered else signal_day)
    note = (
        "20 işlem günü tamamlanmadığı için kesin sonuç etiketi üretilmedi."
        if label is LivePerformanceLabel.OLCULEMIYOR
        else "Sonuç etiketi 20 işlem günlük kapanış ve dönem içi hareketlerle hesaplandı."
    )
    return LiveSignalPerformance(
        signal_id=signal.signal_id,
        symbol=signal.symbol,
        signal_date=signal.signal_date,
        signal_stage=signal.stage,
        entry_close=float(signal.close),
        as_of_date=effective_date.isoformat(),
        available_session_count=len(ordered),
        label=label,
        horizons=horizon_rows,
        note=note,
    )


def canli_performans_ozeti(
    records: Iterable[LiveSignalPerformance],
) -> Mapping[str, int]:
    counts = {label.value: 0 for label in LivePerformanceLabel}
    for record in records:
        counts[record.label.value] += 1
    counts["TOPLAM"] = sum(counts.values())
    counts["ÖLÇÜLEN"] = counts[LivePerformanceLabel.BASARILI.value] + counts[LivePerformanceLabel.SINIRLI_HAREKET.value] + counts[LivePerformanceLabel.BASARISIZ.value]
    return counts


def canli_performanslari_kaydet(
    records: Iterable[LiveSignalPerformance],
    path: str | Path = DEFAULT_LIVE_PERFORMANCE_PATH,
) -> None:
    target = Path(path)
    payload = []
    for record in records:
        row = asdict(record)
        row["label"] = record.label.value
        payload.append(row)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def canli_performanslari_yukle(
    path: str | Path = DEFAULT_LIVE_PERFORMANCE_PATH,
) -> tuple[LiveSignalPerformance, ...]:
    target = Path(path)
    if not target.exists():
        return ()
    raw = json.loads(target.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("Canlı performans dosyası liste biçiminde olmalıdır.")
    records: list[LiveSignalPerformance] = []
    for row in raw:
        payload = dict(row)
        payload["label"] = LivePerformanceLabel(payload["label"])
        payload["horizons"] = tuple(
            LiveHorizonPerformance(**item) for item in payload["horizons"]
        )
        records.append(LiveSignalPerformance(**payload))
    return tuple(records)

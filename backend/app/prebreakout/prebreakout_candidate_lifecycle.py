from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from enum import Enum
import json
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from backend.app.prebreakout.prebreakout_live_watch import PreBreakoutLiveSignal

DEFAULT_LIFECYCLE_PATH = Path("backend/data/prebreakout_candidate_lifecycle.json")


class CandidateLifecycleStatus(str, Enum):
    HAZIRLIK = "HAZIRLIK"
    TETIKLENDI = "TETIKLENDI"
    BASARISIZ = "BASARISIZ"
    SURESI_DOLDU = "SURESI_DOLDU"


@dataclass(frozen=True)
class CandidatePriceObservation:
    observation_date: date
    high: float
    low: float
    close: float


@dataclass(frozen=True)
class CandidateLifecycleConfig:
    trigger_return_pct: float = 3.0
    failure_return_pct: float = -5.0
    expiry_observation_count: int = 10
    duplicate_cooldown_days: int = 5

    def __post_init__(self) -> None:
        if self.trigger_return_pct <= 0:
            raise ValueError("Tetiklenme getirisi pozitif olmalıdır.")
        if self.failure_return_pct >= 0:
            raise ValueError("Başarısızlık getirisi negatif olmalıdır.")
        if self.expiry_observation_count < 1:
            raise ValueError("Süre sonu gözlem sayısı en az 1 olmalıdır.")
        if self.duplicate_cooldown_days < 0:
            raise ValueError("Tekrar bekleme süresi negatif olamaz.")


@dataclass(frozen=True)
class CandidateLifecycleRecord:
    signal_id: str
    symbol: str
    signal_date: str
    signal_stage: str
    entry_close: float
    status: CandidateLifecycleStatus
    status_date: str | None
    elapsed_calendar_days: int
    observed_session_count: int
    last_close: float | None
    max_return_pct: float | None
    min_return_pct: float | None
    note: str


def _return_pct(value: float, base: float) -> float:
    return ((float(value) / float(base)) - 1.0) * 100.0


def adayin_yasam_dongusunu_degerlendir(
    signal: PreBreakoutLiveSignal,
    observations: Sequence[CandidatePriceObservation],
    *,
    config: CandidateLifecycleConfig = CandidateLifecycleConfig(),
    as_of_date: date | None = None,
) -> CandidateLifecycleRecord:
    signal_day = date.fromisoformat(signal.signal_date)
    ordered = sorted(
        (item for item in observations if item.observation_date > signal_day),
        key=lambda item: item.observation_date,
    )
    relevant = ordered[: config.expiry_observation_count]

    max_return: float | None = None
    min_return: float | None = None
    last_close: float | None = None

    for index, item in enumerate(relevant, start=1):
        high_return = _return_pct(item.high, signal.close)
        low_return = _return_pct(item.low, signal.close)
        max_return = high_return if max_return is None else max(max_return, high_return)
        min_return = low_return if min_return is None else min(min_return, low_return)
        last_close = float(item.close)

        # Aynı barda hem stop hem tetik görülürse temkinli biçimde risk önce değerlendirilir.
        if low_return <= config.failure_return_pct:
            return CandidateLifecycleRecord(
                signal_id=signal.signal_id,
                symbol=signal.symbol,
                signal_date=signal.signal_date,
                signal_stage=signal.stage,
                entry_close=signal.close,
                status=CandidateLifecycleStatus.BASARISIZ,
                status_date=item.observation_date.isoformat(),
                elapsed_calendar_days=(item.observation_date - signal_day).days,
                observed_session_count=index,
                last_close=last_close,
                max_return_pct=max_return,
                min_return_pct=min_return,
                note="Başarısızlık eşiği tetiklenme eşiğinden önce veya aynı barda görüldü.",
            )
        if high_return >= config.trigger_return_pct:
            return CandidateLifecycleRecord(
                signal_id=signal.signal_id,
                symbol=signal.symbol,
                signal_date=signal.signal_date,
                signal_stage=signal.stage,
                entry_close=signal.close,
                status=CandidateLifecycleStatus.TETIKLENDI,
                status_date=item.observation_date.isoformat(),
                elapsed_calendar_days=(item.observation_date - signal_day).days,
                observed_session_count=index,
                last_close=last_close,
                max_return_pct=max_return,
                min_return_pct=min_return,
                note="Tetiklenme eşiğine ulaşıldı.",
            )

    effective_date = as_of_date or (relevant[-1].observation_date if relevant else signal_day)
    if len(relevant) >= config.expiry_observation_count:
        return CandidateLifecycleRecord(
            signal_id=signal.signal_id,
            symbol=signal.symbol,
            signal_date=signal.signal_date,
            signal_stage=signal.stage,
            entry_close=signal.close,
            status=CandidateLifecycleStatus.SURESI_DOLDU,
            status_date=relevant[-1].observation_date.isoformat(),
            elapsed_calendar_days=(relevant[-1].observation_date - signal_day).days,
            observed_session_count=len(relevant),
            last_close=last_close,
            max_return_pct=max_return,
            min_return_pct=min_return,
            note="İzleme süresi içinde tetiklenme veya başarısızlık eşiği oluşmadı.",
        )

    return CandidateLifecycleRecord(
        signal_id=signal.signal_id,
        symbol=signal.symbol,
        signal_date=signal.signal_date,
        signal_stage=signal.stage,
        entry_close=signal.close,
        status=CandidateLifecycleStatus.HAZIRLIK,
        status_date=None,
        elapsed_calendar_days=max(0, (effective_date - signal_day).days),
        observed_session_count=len(relevant),
        last_close=last_close,
        max_return_pct=max_return,
        min_return_pct=min_return,
        note="Aday izleme süresi devam ediyor.",
    )


def yeni_sinyal_tekrar_mi(
    existing_signals: Iterable[PreBreakoutLiveSignal],
    *,
    symbol: str,
    signal_date: date,
    cooldown_days: int = 5,
) -> bool:
    if cooldown_days < 0:
        raise ValueError("Tekrar bekleme süresi negatif olamaz.")
    normalized = symbol.upper()
    for item in existing_signals:
        if item.symbol.upper() != normalized:
            continue
        previous_day = date.fromisoformat(item.signal_date)
        day_difference = (signal_date - previous_day).days
        if 0 <= day_difference <= cooldown_days:
            return True
    return False


def yasam_dongusu_ozeti(
    records: Iterable[CandidateLifecycleRecord],
) -> Mapping[str, int]:
    counts = {status.value: 0 for status in CandidateLifecycleStatus}
    for record in records:
        counts[record.status.value] += 1
    counts["TOPLAM"] = sum(counts.values())
    return counts


def yasam_dongusu_kaydet(
    records: Iterable[CandidateLifecycleRecord],
    path: str | Path = DEFAULT_LIFECYCLE_PATH,
) -> None:
    target = Path(path)
    payload = []
    for record in records:
        row = asdict(record)
        row["status"] = record.status.value
        payload.append(row)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def yasam_dongusu_yukle(
    path: str | Path = DEFAULT_LIFECYCLE_PATH,
) -> tuple[CandidateLifecycleRecord, ...]:
    target = Path(path)
    if not target.exists():
        return ()
    raw = json.loads(target.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("Yaşam döngüsü dosyası liste biçiminde olmalıdır.")
    records: list[CandidateLifecycleRecord] = []
    for row in raw:
        payload = dict(row)
        payload["status"] = CandidateLifecycleStatus(payload["status"])
        records.append(CandidateLifecycleRecord(**payload))
    return tuple(records)

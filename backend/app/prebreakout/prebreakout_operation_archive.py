from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any, Iterable


DEFAULT_OPERATION_ARCHIVE_PATH = Path("backend/data/prebreakout_daily_operation_archive.jsonl")


@dataclass(frozen=True)
class DailyOperationArchiveRecord:
    run_date: str
    status: str
    attempt_count: int
    new_signal_count: int
    total_signal_count: int
    lifecycle_count: int
    performance_count: int
    paper_trade_count: int
    portfolio_return_pct: float
    health_ready: bool | None
    warning_count: int
    error_count: int
    missing_observation_count: int


@dataclass(frozen=True)
class DailyOperationComparison:
    current_run_date: str
    previous_run_date: str | None
    new_signal_delta: int | None
    total_signal_delta: int | None
    portfolio_return_delta_pct: float | None
    warning_delta: int | None
    error_delta: int | None
    health_changed: bool


def _number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def gunluk_operasyon_arsiv_kaydi_olustur(run_result: Any) -> DailyOperationArchiveRecord:
    state = run_result.state
    monitor = run_result.monitor_result
    health = run_result.health_report

    portfolio_summary = getattr(monitor, "portfolio_summary", None) if monitor is not None else None
    status = getattr(state.status, "value", state.status)
    return DailyOperationArchiveRecord(
        run_date=str(state.run_date),
        status=str(status),
        attempt_count=int(state.attempt_count),
        new_signal_count=int(getattr(monitor, "new_signal_count", 0) or 0),
        total_signal_count=int(getattr(monitor, "total_signal_count", 0) or 0),
        lifecycle_count=len(getattr(monitor, "lifecycle_records", ()) or ()),
        performance_count=len(getattr(monitor, "performance_records", ()) or ()),
        paper_trade_count=len(getattr(monitor, "paper_trades", ()) or ()),
        portfolio_return_pct=round(
            _number(getattr(portfolio_summary, "portfolio_return_pct", 0.0)), 6
        ),
        health_ready=(bool(health.ready) if health is not None else None),
        warning_count=int(getattr(health, "warning_count", 0) or 0),
        error_count=int(getattr(health, "error_count", 0) or 0),
        missing_observation_count=len(
            getattr(monitor, "missing_observation_symbols", ()) or ()
        ),
    )


def gunluk_operasyon_arsivini_yukle(
    path: str | Path = DEFAULT_OPERATION_ARCHIVE_PATH,
) -> tuple[DailyOperationArchiveRecord, ...]:
    target = Path(path)
    if not target.exists():
        return ()

    records: list[DailyOperationArchiveRecord] = []
    try:
        for line in target.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            payload = json.loads(line)
            records.append(DailyOperationArchiveRecord(**payload))
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return ()
    return tuple(sorted(records, key=lambda item: item.run_date))


def gunluk_operasyon_arsivini_kaydet(
    record: DailyOperationArchiveRecord,
    path: str | Path = DEFAULT_OPERATION_ARCHIVE_PATH,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    existing = {
        item.run_date: item for item in gunluk_operasyon_arsivini_yukle(target)
    }
    existing[record.run_date] = record
    rows = [existing[key] for key in sorted(existing)]
    content = "".join(
        json.dumps(asdict(item), ensure_ascii=False, sort_keys=True) + "\n"
        for item in rows
    )
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(target)


def gunluk_operasyon_karsilastirmasi(
    current: DailyOperationArchiveRecord,
    previous: DailyOperationArchiveRecord | None,
) -> DailyOperationComparison:
    if previous is None:
        return DailyOperationComparison(
            current_run_date=current.run_date,
            previous_run_date=None,
            new_signal_delta=None,
            total_signal_delta=None,
            portfolio_return_delta_pct=None,
            warning_delta=None,
            error_delta=None,
            health_changed=False,
        )

    return DailyOperationComparison(
        current_run_date=current.run_date,
        previous_run_date=previous.run_date,
        new_signal_delta=current.new_signal_count - previous.new_signal_count,
        total_signal_delta=current.total_signal_count - previous.total_signal_count,
        portfolio_return_delta_pct=round(
            current.portfolio_return_pct - previous.portfolio_return_pct, 6
        ),
        warning_delta=current.warning_count - previous.warning_count,
        error_delta=current.error_count - previous.error_count,
        health_changed=current.health_ready != previous.health_ready,
    )


def yonetici_ozeti_olustur(
    current: DailyOperationArchiveRecord,
    previous: DailyOperationArchiveRecord | None = None,
) -> str:
    health_text = (
        "hazır"
        if current.health_ready is True
        else "hazır değil"
        if current.health_ready is False
        else "ölçülemedi"
    )
    base = (
        f"{current.run_date}: sistem {health_text}; {current.new_signal_count} yeni aday, "
        f"{current.total_signal_count} toplam aday, portföy %{current.portfolio_return_pct:.2f}."
    )
    if previous is None:
        return base

    comparison = gunluk_operasyon_karsilastirmasi(current, previous)
    return (
        base
        + f" Önceki güne göre aday farkı {comparison.total_signal_delta:+d}, "
        + f"portföy değişimi {comparison.portfolio_return_delta_pct:+.2f} puan; "
        + f"uyarı {comparison.warning_delta:+d}, hata {comparison.error_delta:+d}."
    )


def gunluk_operasyon_arsivini_tabloya_cevir(
    records: Iterable[DailyOperationArchiveRecord],
) -> list[dict[str, Any]]:
    return [
        {
            "Tarih": item.run_date,
            "Durum": item.status,
            "Yeni aday": item.new_signal_count,
            "Toplam aday": item.total_signal_count,
            "Yaşam döngüsü": item.lifecycle_count,
            "Ölçülen performans": item.performance_count,
            "Deneme işlemi": item.paper_trade_count,
            "Portföy getirisi %": item.portfolio_return_pct,
            "Sistem hazır": item.health_ready,
            "Uyarı": item.warning_count,
            "Hata": item.error_count,
            "Eksik veri": item.missing_observation_count,
        }
        for item in records
    ]

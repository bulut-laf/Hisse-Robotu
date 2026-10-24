from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from backend.app.prebreakout.prebreakout_operation_archive import (
    DailyOperationArchiveRecord,
    gunluk_operasyon_karsilastirmasi,
)


class OperationTrendAlarmLevel(str, Enum):
    NORMAL = "NORMAL"
    WARNING = "UYARI"
    CRITICAL = "KRİTİK"


@dataclass(frozen=True)
class OperationTrendAlarm:
    code: str
    level: OperationTrendAlarmLevel
    title: str
    message: str


@dataclass(frozen=True)
class OperationExecutiveSummary:
    level: OperationTrendAlarmLevel
    headline: str
    detail: str
    alarms: tuple[OperationTrendAlarm, ...]


def _level_rank(level: OperationTrendAlarmLevel) -> int:
    return {
        OperationTrendAlarmLevel.NORMAL: 0,
        OperationTrendAlarmLevel.WARNING: 1,
        OperationTrendAlarmLevel.CRITICAL: 2,
    }[level]


def operasyon_trend_alarmlarini_degerlendir(
    current: DailyOperationArchiveRecord,
    previous: DailyOperationArchiveRecord | None,
    *,
    portfolio_warning_drop_pct: float = 1.0,
    portfolio_critical_drop_pct: float = 3.0,
) -> tuple[OperationTrendAlarm, ...]:
    if previous is None:
        return ()

    comparison = gunluk_operasyon_karsilastirmasi(current, previous)
    alarms: list[OperationTrendAlarm] = []

    if previous.health_ready is True and current.health_ready is False:
        alarms.append(
            OperationTrendAlarm(
                code="HEALTH_LOST",
                level=OperationTrendAlarmLevel.CRITICAL,
                title="Sistem sağlığı bozuldu",
                message="Sistem önceki gün hazırdı; güncel kayıtta hazır değil.",
            )
        )

    if comparison.error_delta is not None and comparison.error_delta > 0:
        alarms.append(
            OperationTrendAlarm(
                code="ERROR_INCREASE",
                level=(
                    OperationTrendAlarmLevel.CRITICAL
                    if current.error_count >= 2
                    else OperationTrendAlarmLevel.WARNING
                ),
                title="Hata sayısı arttı",
                message=f"Hata sayısı önceki güne göre {comparison.error_delta:+d} değişti.",
            )
        )

    if comparison.warning_delta is not None and comparison.warning_delta >= 2:
        alarms.append(
            OperationTrendAlarm(
                code="WARNING_INCREASE",
                level=OperationTrendAlarmLevel.WARNING,
                title="Uyarı yoğunluğu arttı",
                message=f"Uyarı sayısı önceki güne göre {comparison.warning_delta:+d} değişti.",
            )
        )

    portfolio_delta = comparison.portfolio_return_delta_pct
    if portfolio_delta is not None:
        if portfolio_delta <= -abs(portfolio_critical_drop_pct):
            alarms.append(
                OperationTrendAlarm(
                    code="PORTFOLIO_DROP_CRITICAL",
                    level=OperationTrendAlarmLevel.CRITICAL,
                    title="Portföyde sert günlük bozulma",
                    message=f"Deneme portföyü getirisi {portfolio_delta:+.2f} puan değişti.",
                )
            )
        elif portfolio_delta <= -abs(portfolio_warning_drop_pct):
            alarms.append(
                OperationTrendAlarm(
                    code="PORTFOLIO_DROP_WARNING",
                    level=OperationTrendAlarmLevel.WARNING,
                    title="Portföy getirisi geriledi",
                    message=f"Deneme portföyü getirisi {portfolio_delta:+.2f} puan değişti.",
                )
            )

    if current.missing_observation_count > previous.missing_observation_count:
        delta = current.missing_observation_count - previous.missing_observation_count
        alarms.append(
            OperationTrendAlarm(
                code="MISSING_DATA_INCREASE",
                level=OperationTrendAlarmLevel.WARNING,
                title="Eksik gözlem arttı",
                message=f"Eksik gözlem sayısı {delta:+d} arttı.",
            )
        )

    return tuple(sorted(alarms, key=lambda item: _level_rank(item.level), reverse=True))


def gunluk_yonetici_ozetini_hesapla(
    records: Iterable[DailyOperationArchiveRecord],
) -> OperationExecutiveSummary | None:
    rows = tuple(sorted(records, key=lambda item: item.run_date))
    if not rows:
        return None

    current = rows[-1]
    previous = rows[-2] if len(rows) > 1 else None
    alarms = operasyon_trend_alarmlarini_degerlendir(current, previous)
    level = max(
        (alarm.level for alarm in alarms),
        key=_level_rank,
        default=OperationTrendAlarmLevel.NORMAL,
    )

    if previous is None:
        detail = (
            f"{current.run_date}: ilk günlük kayıt; {current.new_signal_count} yeni aday, "
            f"{current.total_signal_count} toplam aday, portföy %{current.portfolio_return_pct:.2f}."
        )
    else:
        comparison = gunluk_operasyon_karsilastirmasi(current, previous)
        detail = (
            f"{current.run_date}: yeni aday {current.new_signal_count}, toplam aday "
            f"{current.total_signal_count}; portföy günlük farkı "
            f"{comparison.portfolio_return_delta_pct:+.2f} puan; "
            f"uyarı {current.warning_count}, hata {current.error_count}."
        )

    headline = {
        OperationTrendAlarmLevel.NORMAL: "Günlük operasyon normal",
        OperationTrendAlarmLevel.WARNING: "Günlük operasyonda dikkat gereken değişim var",
        OperationTrendAlarmLevel.CRITICAL: "Günlük operasyonda kritik değişim var",
    }[level]
    return OperationExecutiveSummary(level=level, headline=headline, detail=detail, alarms=alarms)


def operasyon_alarmlarini_tabloya_cevir(
    alarms: Iterable[OperationTrendAlarm],
) -> list[dict[str, str]]:
    return [
        {
            "Seviye": alarm.level.value,
            "Alarm": alarm.title,
            "Açıklama": alarm.message,
        }
        for alarm in alarms
    ]

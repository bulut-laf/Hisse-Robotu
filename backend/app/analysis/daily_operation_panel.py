from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Iterable

from ..analysis.signal_outcome_tracking import SignalOutcome
from ..data.delayed_data_pilot import PilotLogRecord
from ..history.trade_journal import TradeRecord
from .shadow_portfolio import ShadowPosition


@dataclass(frozen=True)
class OperationAlert:
    priority: int
    level: str
    title: str
    detail: str


@dataclass(frozen=True)
class OperationTask:
    priority: int
    title: str
    detail: str
    target_module: str


@dataclass(frozen=True)
class DailyOperationSummary:
    delayed_data_status: str
    delayed_data_age_minutes: float | None
    delayed_data_locked: bool
    pending_signal_horizons: int
    completed_signal_horizons: int
    signal_record_count: int
    trade_record_count: int
    shadow_trade_count: int
    real_trade_count: int
    alerts: tuple[OperationAlert, ...]
    tasks: tuple[OperationTask, ...]


def _latest_pilot(
    records: Iterable[PilotLogRecord],
) -> PilotLogRecord | None:
    items = tuple(records)
    if not items:
        return None
    return max(items, key=lambda item: item.received_time)


def _signal_counts(
    outcomes: Iterable[SignalOutcome],
) -> tuple[int, int, int]:
    records = tuple(outcomes)
    pending = 0
    completed = 0
    for outcome in records:
        for horizon in outcome.horizons:
            if horizon.available:
                completed += 1
            else:
                pending += 1
    return len(records), pending, completed


def build_daily_operation_summary(
    *,
    pilot_records: Iterable[PilotLogRecord],
    signal_outcomes: Iterable[SignalOutcome],
    trade_records: Iterable[TradeRecord],
    shadow_positions: Iterable[ShadowPosition] = (),
) -> DailyOperationSummary:
    latest = _latest_pilot(pilot_records)
    signals, pending, completed = _signal_counts(signal_outcomes)
    trades = tuple(trade_records)

    journal_shadow_count = sum(
        item.account_type.casefold().startswith("deneme")
        for item in trades
    )
    shadow_count = journal_shadow_count + len(tuple(shadow_positions))
    real_count = len(trades) - journal_shadow_count

    alerts: list[OperationAlert] = []
    tasks: list[OperationTask] = []

    if latest is None:
        delayed_status = "Ölçüm yok"
        delayed_age = None
        delayed_locked = True
        alerts.append(
            OperationAlert(
                1,
                "Kritik",
                "Gecikmeli veri ölçümü yok",
                "Gün içi veri kalitesi ve gecikme durumu doğrulanamadı.",
            )
        )
        tasks.append(
            OperationTask(
                1,
                "Gecikmeli veriyi güncelle",
                "Pilot ekranda en az bir ölçüm alın.",
                "Gecikmeli Veri Pilotu",
            )
        )
    else:
        delayed_age = float(latest.measured_delay_minutes)

        # Günlük Operasyon son geçerli kapanış verisi ile çalışabilir.
        # Sert kilit yalnızca kullanılabilir veri hiç yoksa uygulanır.
        delayed_locked = bool(
            latest.locked and latest.status in {"Veri yok", "Ölçüm yok"}
        )
        delayed_status = (
            latest.status
            if not latest.locked or delayed_locked
            else "Eski/gecikmeli veri — son geçerli veriyle devam"
        )

        if latest.locked and not delayed_locked:
            alerts.append(
                OperationAlert(
                    2,
                    "Uyarı",
                    "Veri eski/gecikmeli — operasyon devam ediyor",
                    "Son geçerli güvenilir veri kullanılıyor; yeni veri geldikçe yeniden değerlendirilecek.",
                )
            )
        elif delayed_locked:
            alerts.append(
                OperationAlert(
                    1,
                    "Kritik",
                    "Kullanılabilir veri yok",
                    latest.status,
                )
            )

        if delayed_locked:
            tasks.append(
                OperationTask(
                    1,
                    "Veri kaynağını yeniden kontrol et",
                    "Yeni ölçüm alıp eksik bar ve gecikmeyi doğrulayın.",
                    "Gecikmeli Veri Pilotu",
                )
            )
        if latest.preview_only and not latest.locked:
            alerts.append(
                OperationAlert(
                    3,
                    "Bilgi",
                    "Gün içi ön izleme",
                    "Gecikmeli veri kesin işlem sinyali değildir.",
                )
            )

        if latest.missing_bar_count > 0:
            alerts.append(
                OperationAlert(
                    2,
                    "Uyarı",
                    "Eksik gün içi bar",
                    f"{latest.missing_bar_count} bar eksik.",
                )
            )

    if pending > 0:
        alerts.append(
            OperationAlert(
                2,
                "Uyarı",
                "Bekleyen sonuç ölçümleri",
                f"{pending} adet 5/10/20 günlük ölçüm henüz tamamlanmadı.",
            )
        )
        tasks.append(
            OperationTask(
                2,
                "Sinyal sonuçlarını güncelle",
                "Tamamlanan ölçüm ufuklarını yeniden hesaplayın.",
                "Sinyal Sonuçları",
            )
        )

    if signals == 0:
        tasks.append(
            OperationTask(
                2,
                "İlk sinyal kaydını oluştur",
                "Karar matrisi sonucu için referans kayıt oluşturun.",
                "Sinyal Sonuçları",
            )
        )

    if shadow_count == 0:
        tasks.append(
            OperationTask(
                3,
                "Gölge işlem kaydı oluştur",
                "Gerçek para kullanmadan işlem günlüğü verisi biriktirin.",
                "İşlem Kayıp Analizi",
            )
        )

    tasks.append(
        OperationTask(
            4,
            "Günlük teknik taramayı çalıştır",
            "Günlük ve haftalık karar matrisi adaylarını gözden geçirin.",
            "BIST Toplu Tarama",
        )
    )
    tasks.append(
        OperationTask(
            5,
            "Temel analiz bağlamını kontrol et",
            "Adayların temel kalite ve sektör görünümünü inceleyin.",
            "Temel Analiz",
        )
    )

    alerts.sort(key=lambda item: item.priority)
    tasks.sort(key=lambda item: item.priority)

    return DailyOperationSummary(
        delayed_data_status=delayed_status,
        delayed_data_age_minutes=delayed_age,
        delayed_data_locked=delayed_locked,
        pending_signal_horizons=pending,
        completed_signal_horizons=completed,
        signal_record_count=signals,
        trade_record_count=len(trades),
        shadow_trade_count=shadow_count,
        real_trade_count=real_count,
        alerts=tuple(alerts),
        tasks=tuple(tasks),
    )


def alert_rows(
    alerts: Iterable[OperationAlert],
) -> list[dict[str, object]]:
    return [
        {
            "Öncelik": item.priority,
            "Seviye": item.level,
            "Başlık": item.title,
            "Açıklama": item.detail,
        }
        for item in alerts
    ]


def task_rows(
    tasks: Iterable[OperationTask],
) -> list[dict[str, object]]:
    return [
        {
            "Öncelik": item.priority,
            "Yapılacak işlem": item.title,
            "Açıklama": item.detail,
            "İlgili ekran": item.target_module,
        }
        for item in tasks
    ]

# V11_TRACK1_OBSERVABILITY_ROWS
def observability_rows(summary: DailyOperationSummary) -> list[dict[str, object]]:
    """Mevcut günlük operasyon kanıtını yeni skor/sinyal üretmeden tek görünümde özetler."""
    critical = sum(item.level.casefold() == "kritik" for item in summary.alerts)
    warning = sum(item.level.casefold() == "uyarı" for item in summary.alerts)
    information = max(0, len(summary.alerts) - critical - warning)
    age = "Ölçüm yok" if summary.delayed_data_age_minutes is None else f"{summary.delayed_data_age_minutes:.1f} dk"
    readiness = "BLOKE" if summary.delayed_data_locked or critical > 0 else "UYARI" if warning > 0 else "HAZIR"
    return [
        {"Alan": "Operasyon durumu", "Değer": readiness},
        {"Alan": "Veri durumu", "Değer": summary.delayed_data_status},
        {"Alan": "Veri yaşı", "Değer": age},
        {"Alan": "Veri güvenlik kilidi", "Değer": "AKTİF" if summary.delayed_data_locked else "Kapalı"},
        {"Alan": "Kritik uyarı", "Değer": critical},
        {"Alan": "Uyarı", "Değer": warning},
        {"Alan": "Bilgi", "Değer": information},
        {"Alan": "Bekleyen sinyal sonucu", "Değer": summary.pending_signal_horizons},
        {"Alan": "Operasyon görevi", "Değer": len(summary.tasks)},
    ]


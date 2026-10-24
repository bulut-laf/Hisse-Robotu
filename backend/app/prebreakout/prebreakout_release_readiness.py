from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import pandas as pd

from backend.app.prebreakout.prebreakout_calibration import (
    PreBreakoutThresholdValidationRow,
)
from backend.app.prebreakout.prebreakout_threshold_policy import (
    DEFAULT_MINIMUM_MOMENTUM_SCORE,
    PreBreakoutThresholdPolicy,
)


@dataclass(frozen=True)
class PreBreakoutReleaseReadiness:
    status: str
    production_policy_enabled: bool
    accepted_stage_count: int
    rollback_ready: bool
    leakage_guard_confirmed: bool
    message: str

    @property
    def ready(self) -> bool:
        return self.status == "Kullanıma hazır"


def on_yukselis_surum_hazirligini_degerlendir(
    validations: Iterable[PreBreakoutThresholdValidationRow],
    policy: PreBreakoutThresholdPolicy,
    *,
    leakage_guard_confirmed: bool = True,
) -> PreBreakoutReleaseReadiness:
    rows = tuple(validations)
    accepted = tuple(row for row in rows if row.verdict == "Kontrollü uygulama adayı")
    rollback_ready = all(
        policy.minimum_momentum_score(stage) == DEFAULT_MINIMUM_MOMENTUM_SCORE
        for stage in ("E2", "E3", "E4")
    ) if not policy.enabled else True

    if not leakage_guard_confirmed:
        status = "Kullanıma hazır değil"
        message = "Gelecek veri sızıntısı güvenlik kontrolü doğrulanmadı."
    elif policy.enabled and not accepted:
        status = "Kullanıma hazır değil"
        message = "Etkin politika için tarihsel doğrulamayı geçen eşik bulunamadı."
    elif not rollback_ready:
        status = "Kullanıma hazır değil"
        message = "Varsayılan eşiklere geri dönüş doğrulanamadı."
    else:
        status = "Kullanıma hazır"
        if policy.enabled:
            message = (
                "Kontrollü eşik politikası etkin; tarihsel doğrulama ve geri alma "
                "mekanizması hazır."
            )
        else:
            message = (
                "Kontrollü eşik politikası kapalı; mevcut 10/20 üretim eşiği korunuyor "
                "ve sistem güvenli varsayılanla çalışıyor."
            )

    return PreBreakoutReleaseReadiness(
        status=status,
        production_policy_enabled=policy.enabled,
        accepted_stage_count=len(accepted),
        rollback_ready=rollback_ready,
        leakage_guard_confirmed=leakage_guard_confirmed,
        message=message,
    )


def surum_hazirligini_tabloya_cevir(
    report: PreBreakoutReleaseReadiness,
) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"Kontrol": "Genel durum", "Sonuç": report.status},
            {
                "Kontrol": "Kontrollü eşik politikası",
                "Sonuç": "Etkin" if report.production_policy_enabled else "Kapalı",
            },
            {
                "Kontrol": "Doğrulamayı geçen aşama",
                "Sonuç": report.accepted_stage_count,
            },
            {
                "Kontrol": "Geri alma hazır",
                "Sonuç": "Evet" if report.rollback_ready else "Hayır",
            },
            {
                "Kontrol": "Gelecek veri sızıntısı koruması",
                "Sonuç": "Doğrulandı" if report.leakage_guard_confirmed else "Doğrulanmadı",
            },
        ]
    )

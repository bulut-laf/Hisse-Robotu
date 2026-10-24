from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal


class FundamentalSettingsError(ValueError):
    """Temel analiz ayarları okunamadığında veya geçersiz olduğunda kullanılır."""


ArchiveSortPreference = Literal[
    "period_desc",
    "period_asc",
    "created_desc",
    "created_asc",
    "score_desc",
    "score_asc",
]


@dataclass(frozen=True)
class FundamentalAnalysisSettings:
    strong_threshold: int = 80
    balanced_threshold: int = 65
    watch_threshold: int = 50
    minimum_sector_company_count: int = 3
    sector_change_threshold: float = 3.0
    score_history_maximum_age_days: int = 730
    report_archive_maximum_age_days: int = 1095
    default_archive_sort: ArchiveSortPreference = "period_desc"

    def __post_init__(self) -> None:
        thresholds = (
            self.strong_threshold,
            self.balanced_threshold,
            self.watch_threshold,
        )
        if any(not 0 <= value <= 100 for value in thresholds):
            raise FundamentalSettingsError(
                "Temel kalite eşikleri 0–100 aralığında olmalıdır."
            )
        if not (
            self.strong_threshold
            > self.balanced_threshold
            > self.watch_threshold
        ):
            raise FundamentalSettingsError(
                "Kalite eşikleri Güçlü > Dengeli > İzlenmeli "
                "sırasını korumalıdır."
            )
        if self.minimum_sector_company_count < 2:
            raise FundamentalSettingsError(
                "Sektör karşılaştırması için asgari şirket sayısı "
                "en az 2 olmalıdır."
            )
        if not 0.1 <= self.sector_change_threshold <= 25:
            raise FundamentalSettingsError(
                "Sektör değişim eşiği 0,1–25 aralığında olmalıdır."
            )
        if self.score_history_maximum_age_days < 30:
            raise FundamentalSettingsError(
                "Temel skor geçmişi yaşı en az 30 gün olmalıdır."
            )
        if self.report_archive_maximum_age_days < 30:
            raise FundamentalSettingsError(
                "Rapor arşivi yaşı en az 30 gün olmalıdır."
            )
        valid_sorts = {
            "period_desc",
            "period_asc",
            "created_desc",
            "created_asc",
            "score_desc",
            "score_asc",
        }
        if self.default_archive_sort not in valid_sorts:
            raise FundamentalSettingsError(
                "Varsayılan arşiv sıralaması geçersiz."
            )


DEFAULT_FUNDAMENTAL_SETTINGS = FundamentalAnalysisSettings()


class FundamentalSettingsJsonStore:
    def __init__(
        self,
        path: Path | str = Path(
            "backend/data/fundamental_analysis_settings.json"
        ),
    ) -> None:
        self.path = Path(path)

    def load(self) -> FundamentalAnalysisSettings:
        if not self.path.exists():
            return DEFAULT_FUNDAMENTAL_SETTINGS
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raise TypeError("Ayar kökü nesne olmalıdır.")
            return FundamentalAnalysisSettings(**raw)
        except (
            OSError,
            json.JSONDecodeError,
            TypeError,
            FundamentalSettingsError,
        ) as exc:
            raise FundamentalSettingsError(
                "Temel analiz ayar dosyası okunamadı veya geçersiz."
            ) from exc

    def save(
        self,
        settings: FundamentalAnalysisSettings,
    ) -> FundamentalAnalysisSettings:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(
                asdict(settings),
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        temporary.replace(self.path)
        return settings

    def reset(self) -> FundamentalAnalysisSettings:
        return self.save(DEFAULT_FUNDAMENTAL_SETTINGS)

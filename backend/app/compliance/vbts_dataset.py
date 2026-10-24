from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterable

from backend.app.compliance.vbts_models import VbtsMeasure
from backend.app.compliance.vbts_source_status import VbtsSourceStatus


@dataclass(frozen=True, slots=True)
class VbtsDataset:
    measures: tuple[VbtsMeasure, ...]
    status: VbtsSourceStatus

    def __init__(
        self,
        measures: Iterable[VbtsMeasure],
        status: VbtsSourceStatus,
    ) -> None:
        normalized_measures = tuple(measures)

        if len(normalized_measures) != status.record_count:
            raise ValueError(
                "Kaynak kayıt sayısı ile VBTS tedbir sayısı uyuşmuyor."
            )

        mismatched_sources = {
            measure.source
            for measure in normalized_measures
            if measure.source != status.source
        }

        if mismatched_sources:
            raise ValueError(
                "VBTS tedbirlerinin kaynağı ile veri paketi kaynağı uyuşmuyor."
            )

        object.__setattr__(self, "measures", normalized_measures)
        object.__setattr__(self, "status", status)

    def is_usable_at(
        self,
        control_time: datetime,
        maximum_age: timedelta,
    ) -> bool:
        return self.status.is_usable_at(
            control_time=control_time,
            maximum_age=maximum_age,
        )
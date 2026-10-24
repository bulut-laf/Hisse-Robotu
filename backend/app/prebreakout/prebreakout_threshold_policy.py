from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping


DEFAULT_MINIMUM_MOMENTUM_SCORE = 10


@dataclass(frozen=True)
class PreBreakoutThresholdPolicy:
    """Üretim motorunda kontrollü ve geri alınabilir momentum eşiği politikası."""

    enabled: bool = False
    stage_minimum_momentum_scores: Mapping[str, int] = field(default_factory=dict)
    source: str = "Mevcut üretim eşiği"

    def __post_init__(self) -> None:
        normalized: dict[str, int] = {}
        for stage, score in dict(self.stage_minimum_momentum_scores).items():
            stage_name = str(stage).upper()
            if stage_name not in {"E2", "E3", "E4"}:
                raise ValueError("Eşik politikası yalnızca E2, E3 ve E4 için tanımlanabilir.")
            numeric_score = int(score)
            if not 0 <= numeric_score <= 20:
                raise ValueError("Momentum eşiği 0 ile 20 arasında olmalıdır.")
            normalized[stage_name] = numeric_score
        object.__setattr__(self, "stage_minimum_momentum_scores", MappingProxyType(normalized))

    def minimum_momentum_score(self, stage: str) -> int:
        if not self.enabled:
            return DEFAULT_MINIMUM_MOMENTUM_SCORE
        return self.stage_minimum_momentum_scores.get(
            str(stage).upper(), DEFAULT_MINIMUM_MOMENTUM_SCORE
        )


def mevcut_esik_politikasi() -> PreBreakoutThresholdPolicy:
    return PreBreakoutThresholdPolicy()

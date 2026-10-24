from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass(frozen=True, slots=True)
class VbtsSourceStatus:
    source: str
    fetched_at: datetime
    is_verified: bool
    record_count: int

    def __post_init__(self) -> None:
        normalized_source = self.source.strip().upper()

        if not normalized_source:
            raise ValueError("Kaynak adı boş bırakılamaz.")

        if self.fetched_at.tzinfo is None:
            raise ValueError("Kaynak zamanı saat dilimi bilgisi içermelidir.")

        if self.record_count < 0:
            raise ValueError("Kayıt sayısı negatif olamaz.")

        object.__setattr__(self, "source", normalized_source)

    def is_usable_at(
        self,
        control_time: datetime,
        maximum_age: timedelta,
    ) -> bool:
        if control_time.tzinfo is None:
            raise ValueError("Kontrol zamanı saat dilimi bilgisi içermelidir.")

        if maximum_age < timedelta(0):
            raise ValueError("Azami veri yaşı negatif olamaz.")

        if not self.is_verified:
            return False

        age = control_time - self.fetched_at

        if age < timedelta(0):
            return False

        return age <= maximum_age
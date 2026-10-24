from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Iterable

from ..models.fundamental_models import FinancialPeriod


class FundamentalStoreError(RuntimeError):
    """Finansal dönem deposu hata türü."""


@dataclass(frozen=True)
class FundamentalStoreResult:
    inserted: int
    updated: int
    unchanged: int
    total_records: int


def _serialize_value(value: object) -> object:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, date):
        return value.isoformat()
    return value


def _period_to_record(period: FinancialPeriod) -> dict[str, object]:
    return {
        key: _serialize_value(value)
        for key, value in asdict(period).items()
    }


def _period_digest(period: FinancialPeriod) -> str:
    raw = json.dumps(
        _period_to_record(period),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class FundamentalJsonStore:
    """Finansal dönemleri sembol-yıl-çeyrek anahtarıyla güvenle saklar."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    @staticmethod
    def _key(period: FinancialPeriod) -> str:
        return (
            f"{period.symbol}|"
            f"{period.fiscal_year}|"
            f"{period.fiscal_quarter}"
        )

    def _read(self) -> dict[str, dict[str, object]]:
        if not self.path.exists():
            return {}
        try:
            payload = json.loads(
                self.path.read_text(encoding="utf-8")
            )
        except Exception as exc:
            raise FundamentalStoreError(
                "Finansal dönem deposu okunamadı."
            ) from exc
        if not isinstance(payload, dict):
            raise FundamentalStoreError(
                "Finansal dönem deposu nesne biçiminde olmalıdır."
            )
        return payload

    def upsert(
        self,
        periods: Iterable[FinancialPeriod],
    ) -> FundamentalStoreResult:
        existing = self._read()
        inserted = 0
        updated = 0
        unchanged = 0

        for period in periods:
            key = self._key(period)
            record = _period_to_record(period)
            digest = _period_digest(period)
            stored = existing.get(key)

            if stored is None:
                inserted += 1
            elif stored.get("_digest") == digest:
                unchanged += 1
                continue
            else:
                updated += 1

            existing[key] = {
                **record,
                "_digest": digest,
            }

        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(
            self.path.suffix + ".tmp"
        )
        temporary.write_text(
            json.dumps(
                existing,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        temporary.replace(self.path)

        return FundamentalStoreResult(
            inserted=inserted,
            updated=updated,
            unchanged=unchanged,
            total_records=len(existing),
        )

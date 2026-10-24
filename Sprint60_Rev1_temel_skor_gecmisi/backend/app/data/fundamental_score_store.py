from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Iterable, Mapping

from ..analysis.fundamental_quality import (
    FundamentalQualityComponent,
    FundamentalQualityScore,
)
from ..models.fundamental_models import FinancialPeriod


class FundamentalScoreStoreError(RuntimeError):
    """Temel kalite skoru deposu okunamadığında veya doğrulanamadığında kullanılır."""


@dataclass(frozen=True)
class FundamentalScoreStoreResult:
    inserted: int
    updated: int
    unchanged: int
    total_records: int


@dataclass(frozen=True)
class StoredFundamentalScore:
    symbol: str
    period_key: str
    period_end: date
    data_identity: str
    score: FundamentalQualityScore
    calculated_at: datetime


def financial_periods_identity(
    periods: Iterable[FinancialPeriod],
) -> str:
    records: list[dict[str, str]] = []

    for period in sorted(
        periods,
        key=lambda item: (
            item.symbol,
            item.period_end,
            item.fiscal_year,
            item.fiscal_quarter,
        ),
    ):
        raw = asdict(period)
        records.append(
            {
                key: (
                    value.isoformat()
                    if isinstance(value, (date, datetime))
                    else str(value)
                )
                for key, value in raw.items()
            }
        )

    encoded = json.dumps(
        records,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:20]


def _component_to_record(
    component: FundamentalQualityComponent,
) -> dict[str, object]:
    return {
        "name": component.name,
        "score": component.score,
        "maximum_score": component.maximum_score,
        "reasons": list(component.reasons),
        "risks": list(component.risks),
    }


def _component_from_record(
    record: Mapping[str, object],
) -> FundamentalQualityComponent:
    return FundamentalQualityComponent(
        name=str(record.get("name", "")),
        score=int(record.get("score", 0)),
        maximum_score=int(record.get("maximum_score", 0)),
        reasons=tuple(
            str(item) for item in record.get("reasons", [])
        ),
        risks=tuple(
            str(item) for item in record.get("risks", [])
        ),
    )


def _score_to_record(
    score: FundamentalQualityScore,
) -> dict[str, object]:
    return {
        "symbol": score.symbol,
        "period_key": score.period_key,
        "total_score": score.total_score,
        "locked": score.locked,
        "explanation": score.explanation,
        "profitability": _component_to_record(
            score.profitability
        ),
        "growth": _component_to_record(score.growth),
        "leverage": _component_to_record(score.leverage),
        "liquidity": _component_to_record(score.liquidity),
        "cash_flow": _component_to_record(score.cash_flow),
    }


def _score_from_record(
    record: Mapping[str, object],
) -> FundamentalQualityScore:
    total_raw = record.get("total_score")
    return FundamentalQualityScore(
        symbol=str(record["symbol"]),
        period_key=str(record["period_key"]),
        total_score=(
            None if total_raw is None else int(total_raw)
        ),
        profitability=_component_from_record(
            record.get("profitability", {})
        ),
        growth=_component_from_record(
            record.get("growth", {})
        ),
        leverage=_component_from_record(
            record.get("leverage", {})
        ),
        liquidity=_component_from_record(
            record.get("liquidity", {})
        ),
        cash_flow=_component_from_record(
            record.get("cash_flow", {})
        ),
        locked=bool(record.get("locked", True)),
        explanation=str(record.get("explanation", "")),
    )


class FundamentalScoreJsonStore:
    """Temel kalite skorlarını şirket ve bilanço dönemi bazında saklar."""

    def __init__(
        self,
        path: str | Path = "backend/data/fundamental_scores.json",
    ) -> None:
        self.path = Path(path)

    @staticmethod
    def _key(symbol: str, period_key: str) -> str:
        return f"{symbol.strip().upper()}|{period_key}"

    def _read(self) -> dict[str, dict[str, object]]:
        if not self.path.exists():
            return {}

        try:
            payload = json.loads(
                self.path.read_text(encoding="utf-8")
            )
        except Exception as exc:
            raise FundamentalScoreStoreError(
                "Temel skor deposu okunamadı."
            ) from exc

        if not isinstance(payload, dict):
            raise FundamentalScoreStoreError(
                "Temel skor deposu nesne biçiminde olmalıdır."
            )

        return payload

    def save(
        self,
        *,
        periods: Iterable[FinancialPeriod],
        score: FundamentalQualityScore,
    ) -> FundamentalScoreStoreResult:
        items = tuple(periods)
        if not items:
            raise ValueError(
                "Temel skor kaydı için finansal dönem gereklidir."
            )
        if score.locked or score.total_score is None:
            raise ValueError(
                "Kilitli veya hesaplanamayan temel skor kaydedilemez."
            )

        latest = max(items, key=lambda item: item.period_end)
        if latest.symbol != score.symbol:
            raise ValueError(
                "Temel skor sembolü finansal dönemlerle eşleşmiyor."
            )
        if latest.period_key != score.period_key:
            raise ValueError(
                "Temel skor dönemi son finansal dönemle eşleşmiyor."
            )

        identity = financial_periods_identity(items)
        key = self._key(score.symbol, score.period_key)
        records = self._read()
        existing = records.get(key)

        record = {
            "symbol": score.symbol,
            "period_key": score.period_key,
            "period_end": latest.period_end.isoformat(),
            "data_identity": identity,
            "calculated_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "score": _score_to_record(score),
        }

        inserted = 0
        updated = 0
        unchanged = 0

        if existing is None:
            inserted = 1
        elif (
            existing.get("data_identity") == identity
            and existing.get("score") == record["score"]
        ):
            unchanged = 1
            record = existing
        else:
            updated = 1

        records[key] = record
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(
            self.path.suffix + ".tmp"
        )
        temporary.write_text(
            json.dumps(
                records,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        temporary.replace(self.path)

        return FundamentalScoreStoreResult(
            inserted=inserted,
            updated=updated,
            unchanged=unchanged,
            total_records=len(records),
        )

    def load_latest_scores(
        self,
        *,
        today: date | None = None,
        maximum_age_days: int = 190,
    ) -> dict[str, FundamentalQualityScore]:
        reference = today or date.today()
        records = self._read()
        latest_by_symbol: dict[str, StoredFundamentalScore] = {}

        for record in records.values():
            try:
                period_end = date.fromisoformat(
                    str(record["period_end"])
                )
                calculated_at = datetime.fromisoformat(
                    str(record["calculated_at"])
                )
                score = _score_from_record(record["score"])
                stored = StoredFundamentalScore(
                    symbol=str(record["symbol"]).upper(),
                    period_key=str(record["period_key"]),
                    period_end=period_end,
                    data_identity=str(record["data_identity"]),
                    score=score,
                    calculated_at=calculated_at,
                )
            except Exception as exc:
                raise FundamentalScoreStoreError(
                    "Temel skor deposunda geçersiz kayıt bulundu."
                ) from exc

            age_days = (reference - stored.period_end).days
            if age_days < 0 or age_days > maximum_age_days:
                continue
            if stored.score.locked:
                continue

            current = latest_by_symbol.get(stored.symbol)
            if (
                current is None
                or stored.period_end > current.period_end
            ):
                latest_by_symbol[stored.symbol] = stored

        return {
            symbol: stored.score
            for symbol, stored in latest_by_symbol.items()
        }

    def load_history(
        self,
        symbol: str,
        *,
        today: date | None = None,
        maximum_age_days: int = 730,
    ) -> tuple[StoredFundamentalScore, ...]:
        """Bir şirketin geçerli temel skor geçmişini dönem sırasıyla döndürür."""

        normalized_symbol = symbol.strip().upper()
        if not normalized_symbol:
            raise ValueError("Şirket sembolü boş olamaz.")
        if maximum_age_days < 1:
            raise ValueError(
                "Azami geçmiş yaşı en az 1 gün olmalıdır."
            )

        reference = today or date.today()
        history: list[StoredFundamentalScore] = []

        for record in self._read().values():
            if str(record.get("symbol", "")).upper() != normalized_symbol:
                continue

            try:
                period_end = date.fromisoformat(
                    str(record["period_end"])
                )
                calculated_at = datetime.fromisoformat(
                    str(record["calculated_at"])
                )
                score = _score_from_record(record["score"])
                stored = StoredFundamentalScore(
                    symbol=normalized_symbol,
                    period_key=str(record["period_key"]),
                    period_end=period_end,
                    data_identity=str(record["data_identity"]),
                    score=score,
                    calculated_at=calculated_at,
                )
            except Exception as exc:
                raise FundamentalScoreStoreError(
                    "Temel skor geçmişinde geçersiz kayıt bulundu."
                ) from exc

            age_days = (reference - stored.period_end).days
            if age_days < 0 or age_days > maximum_age_days:
                continue
            if stored.score.locked or stored.score.total_score is None:
                continue

            history.append(stored)

        return tuple(
            sorted(
                history,
                key=lambda item: (
                    item.period_end,
                    item.period_key,
                ),
            )
        )

    def load_comparable_latest(
        self,
        symbols: Iterable[str] | None = None,
        *,
        today: date | None = None,
        maximum_age_days: int = 190,
    ) -> tuple[StoredFundamentalScore, ...]:
        """Güncel şirket skorlarını aynı dönem karşılaştırması için döndürür."""

        requested = (
            {str(symbol).strip().upper() for symbol in symbols}
            if symbols is not None
            else None
        )
        reference = today or date.today()
        latest: dict[str, StoredFundamentalScore] = {}

        for record in self._read().values():
            symbol = str(record.get("symbol", "")).upper()
            if not symbol:
                continue
            if requested is not None and symbol not in requested:
                continue

            try:
                period_end = date.fromisoformat(
                    str(record["period_end"])
                )
                calculated_at = datetime.fromisoformat(
                    str(record["calculated_at"])
                )
                score = _score_from_record(record["score"])
                stored = StoredFundamentalScore(
                    symbol=symbol,
                    period_key=str(record["period_key"]),
                    period_end=period_end,
                    data_identity=str(record["data_identity"]),
                    score=score,
                    calculated_at=calculated_at,
                )
            except Exception as exc:
                raise FundamentalScoreStoreError(
                    "Temel skor karşılaştırmasında geçersiz kayıt bulundu."
                ) from exc

            age_days = (reference - period_end).days
            if age_days < 0 or age_days > maximum_age_days:
                continue
            if score.locked or score.total_score is None:
                continue

            current = latest.get(symbol)
            if current is None or period_end > current.period_end:
                latest[symbol] = stored

        if not latest:
            return ()

        newest_period = max(
            item.period_end for item in latest.values()
        )

        comparable = tuple(
            item
            for item in latest.values()
            if item.period_end == newest_period
        )

        return tuple(
            sorted(
                comparable,
                key=lambda item: (
                    -(item.score.total_score or 0),
                    item.symbol,
                ),
            )
        )


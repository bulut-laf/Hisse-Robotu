from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Iterable

from .contracts import DataQualityState


class PortfolioSnapshotStoreError(RuntimeError):
    pass


class PositionChangeKind(str, Enum):
    NEW_ENTRY = "NEW_ENTRY"
    INCREASED = "INCREASED"
    REDUCED = "REDUCED"
    FULL_EXIT = "FULL_EXIT"
    UNCHANGED = "UNCHANGED"
    UNKNOWN = "UNKNOWN"


class PositionChangeConfidence(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class WeightChangeDirection(str, Enum):
    INCREASED = "INCREASED"
    REDUCED = "REDUCED"
    UNCHANGED = "UNCHANGED"
    UNKNOWN = "UNKNOWN"


def _non_negative(value: Decimal | None, name: str) -> None:
    if value is not None and (not value.is_finite() or value < 0):
        raise ValueError(f"{name} negatif veya sonlu olmayan değer olamaz.")


def _ratio(value: Decimal | None, name: str) -> None:
    if value is None:
        return
    if not value.is_finite() or value < 0 or value > 1:
        raise ValueError(f"{name} 0-1 aralığında olmalıdır.")


def _aware(value: datetime, name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} timezone-aware olmalıdır.")


def _clean_symbol(value: str) -> str:
    clean = value.strip().upper()
    if not clean:
        raise ValueError("symbol boş olamaz.")
    return clean


@dataclass(frozen=True, slots=True)
class FundPortfolioPosition:
    canonical_fund_id: str
    portfolio_date: date
    symbol: str
    asset_type: str
    asset_name: str | None = None
    shares_held: Decimal | None = None
    market_value: Decimal | None = None
    portfolio_weight: Decimal | None = None

    def __post_init__(self) -> None:
        fund_id = self.canonical_fund_id.strip()
        if not fund_id:
            raise ValueError("canonical_fund_id boş olamaz.")
        object.__setattr__(self, "canonical_fund_id", fund_id)
        object.__setattr__(self, "symbol", _clean_symbol(self.symbol))
        asset_type = self.asset_type.strip().upper()
        if not asset_type:
            raise ValueError("asset_type boş olamaz.")
        object.__setattr__(self, "asset_type", asset_type)
        _non_negative(self.shares_held, "shares_held")
        _non_negative(self.market_value, "market_value")
        _ratio(self.portfolio_weight, "portfolio_weight")


@dataclass(frozen=True, slots=True)
class FundPortfolioSnapshot:
    canonical_fund_id: str
    portfolio_date: date
    publication_date: date
    ingested_at: datetime
    provider: str
    positions: tuple[FundPortfolioPosition, ...]
    data_quality_state: DataQualityState = DataQualityState.VALID
    source_reference: str | None = None

    def __post_init__(self) -> None:
        fund_id = self.canonical_fund_id.strip()
        provider = self.provider.strip().upper()
        if not fund_id or not provider:
            raise ValueError("Fon ve provider kimliği zorunludur.")
        _aware(self.ingested_at, "ingested_at")
        if self.publication_date < self.portfolio_date:
            raise ValueError("publication_date portfolio_date öncesinde olamaz.")
        seen: set[str] = set()
        ordered: list[FundPortfolioPosition] = []
        for item in sorted(self.positions, key=lambda row: (row.asset_type, row.symbol)):
            if item.canonical_fund_id != fund_id or item.portfolio_date != self.portfolio_date:
                raise ValueError("Snapshot pozisyon kimliği snapshot ile eşleşmiyor.")
            key = f"{item.asset_type}|{item.symbol}"
            if key in seen:
                raise ValueError(f"DUPLICATE_PORTFOLIO_POSITION:{key}")
            seen.add(key)
            ordered.append(item)
        object.__setattr__(self, "canonical_fund_id", fund_id)
        object.__setattr__(self, "provider", provider)
        object.__setattr__(self, "positions", tuple(ordered))

    @property
    def snapshot_id(self) -> str:
        raw = f"{self.canonical_fund_id}|{self.portfolio_date.isoformat()}|{self.provider}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class PortfolioPositionChange:
    canonical_fund_id: str
    symbol: str
    previous_portfolio_date: date
    current_portfolio_date: date
    kind: PositionChangeKind
    confidence: PositionChangeConfidence
    previous_shares: Decimal | None
    current_shares: Decimal | None
    share_change: Decimal | None
    previous_market_value: Decimal | None
    current_market_value: Decimal | None
    market_value_change: Decimal | None
    previous_weight: Decimal | None
    current_weight: Decimal | None
    weight_change_percentage_points: Decimal | None
    weight_direction: WeightChangeDirection
    reason: str


@dataclass(frozen=True, slots=True)
class FundPortfolioChangeSet:
    canonical_fund_id: str
    previous_portfolio_date: date
    current_portfolio_date: date
    previous_publication_date: date
    current_publication_date: date
    changes: tuple[PortfolioPositionChange, ...]


@dataclass(frozen=True, slots=True)
class StockFundActivity:
    symbol: str
    current_fund_count: int
    comparable_fund_count: int
    new_fund_count: int
    exited_fund_count: int
    increasing_fund_count: int
    decreasing_fund_count: int
    unchanged_fund_count: int
    unknown_fund_count: int
    accumulation_breadth: Decimal | None
    distribution_breadth: Decimal | None


@dataclass(frozen=True, slots=True)
class PortfolioSnapshotStoreResult:
    inserted: int
    unchanged: int
    total_records: int


def _snapshot_complete(snapshot: FundPortfolioSnapshot) -> bool:
    return snapshot.data_quality_state is DataQualityState.VALID


def _weight_direction(previous: Decimal | None, current: Decimal | None) -> tuple[WeightChangeDirection, Decimal | None]:
    if previous is None or current is None:
        return WeightChangeDirection.UNKNOWN, None
    delta_pp = (current - previous) * Decimal("100")
    if delta_pp > 0:
        return WeightChangeDirection.INCREASED, delta_pp
    if delta_pp < 0:
        return WeightChangeDirection.REDUCED, delta_pp
    return WeightChangeDirection.UNCHANGED, delta_pp


def _decimal_delta(previous: Decimal | None, current: Decimal | None) -> Decimal | None:
    if previous is None or current is None:
        return None
    return current - previous


def compare_portfolio_snapshots(
    previous: FundPortfolioSnapshot,
    current: FundPortfolioSnapshot,
) -> FundPortfolioChangeSet:
    if previous.canonical_fund_id != current.canonical_fund_id:
        raise ValueError("PORTFOLIO_COMPARE_FUND_MISMATCH")
    if current.portfolio_date <= previous.portfolio_date:
        raise ValueError("PORTFOLIO_COMPARE_DATE_ORDER")

    prev = {item.symbol: item for item in previous.positions if item.asset_type == "EQUITY"}
    curr = {item.symbol: item for item in current.positions if item.asset_type == "EQUITY"}
    output: list[PortfolioPositionChange] = []

    for symbol in sorted(set(prev) | set(curr)):
        before = prev.get(symbol)
        after = curr.get(symbol)
        complete = _snapshot_complete(previous) and _snapshot_complete(current)

        previous_weight = before.portfolio_weight if before else None
        current_weight = after.portfolio_weight if after else None
        weight_direction, weight_delta = _weight_direction(previous_weight, current_weight)

        if before is None and after is not None:
            if complete:
                kind = PositionChangeKind.NEW_ENTRY
                confidence = PositionChangeConfidence.HIGH
                reason = "CURRENT_PRESENT_PREVIOUS_ABSENT_COMPLETE_SNAPSHOTS"
            else:
                kind = PositionChangeKind.UNKNOWN
                confidence = PositionChangeConfidence.LOW
                reason = "PRESENCE_CHANGE_WITH_PARTIAL_SNAPSHOT"
        elif before is not None and after is None:
            if complete:
                kind = PositionChangeKind.FULL_EXIT
                confidence = PositionChangeConfidence.HIGH
                reason = "PREVIOUS_PRESENT_CURRENT_ABSENT_COMPLETE_SNAPSHOTS"
            else:
                kind = PositionChangeKind.UNKNOWN
                confidence = PositionChangeConfidence.LOW
                reason = "ABSENCE_CANNOT_PROVE_EXIT_WITH_PARTIAL_SNAPSHOT"
        elif before is not None and after is not None:
            if before.shares_held is not None and after.shares_held is not None:
                share_delta = after.shares_held - before.shares_held
                if share_delta > 0:
                    kind = PositionChangeKind.INCREASED
                elif share_delta < 0:
                    kind = PositionChangeKind.REDUCED
                else:
                    kind = PositionChangeKind.UNCHANGED
                confidence = PositionChangeConfidence.HIGH
                reason = "SHARE_COUNT_COMPARISON"
            else:
                kind = PositionChangeKind.UNKNOWN
                confidence = (
                    PositionChangeConfidence.MEDIUM
                    if before.market_value is not None and after.market_value is not None
                    else PositionChangeConfidence.LOW
                )
                reason = "WEIGHT_OR_VALUE_CHANGE_ONLY_NOT_CONFIRMED_TRADE"
        else:  # pragma: no cover - union guarantees one side exists.
            continue

        previous_shares = before.shares_held if before else None
        current_shares = after.shares_held if after else None
        previous_value = before.market_value if before else None
        current_value = after.market_value if after else None

        output.append(
            PortfolioPositionChange(
                canonical_fund_id=current.canonical_fund_id,
                symbol=symbol,
                previous_portfolio_date=previous.portfolio_date,
                current_portfolio_date=current.portfolio_date,
                kind=kind,
                confidence=confidence,
                previous_shares=previous_shares,
                current_shares=current_shares,
                share_change=_decimal_delta(previous_shares, current_shares),
                previous_market_value=previous_value,
                current_market_value=current_value,
                market_value_change=_decimal_delta(previous_value, current_value),
                previous_weight=previous_weight,
                current_weight=current_weight,
                weight_change_percentage_points=weight_delta,
                weight_direction=weight_direction,
                reason=reason,
            )
        )

    return FundPortfolioChangeSet(
        canonical_fund_id=current.canonical_fund_id,
        previous_portfolio_date=previous.portfolio_date,
        current_portfolio_date=current.portfolio_date,
        previous_publication_date=previous.publication_date,
        current_publication_date=current.publication_date,
        changes=tuple(output),
    )


def aggregate_stock_fund_activity(
    change_sets: Iterable[FundPortfolioChangeSet],
) -> tuple[StockFundActivity, ...]:
    by_symbol: dict[str, list[PortfolioPositionChange]] = {}
    for change_set in change_sets:
        for change in change_set.changes:
            by_symbol.setdefault(change.symbol, []).append(change)

    output: list[StockFundActivity] = []
    for symbol in sorted(by_symbol):
        rows = by_symbol[symbol]
        new_count = sum(item.kind is PositionChangeKind.NEW_ENTRY for item in rows)
        exit_count = sum(item.kind is PositionChangeKind.FULL_EXIT for item in rows)
        increase_count = sum(item.kind is PositionChangeKind.INCREASED for item in rows)
        decrease_count = sum(item.kind is PositionChangeKind.REDUCED for item in rows)
        unchanged_count = sum(item.kind is PositionChangeKind.UNCHANGED for item in rows)
        unknown_count = sum(item.kind is PositionChangeKind.UNKNOWN for item in rows)
        comparable = new_count + exit_count + increase_count + decrease_count + unchanged_count
        current_fund_count = sum(
            item.kind not in (PositionChangeKind.FULL_EXIT, PositionChangeKind.UNKNOWN)
            or item.current_shares is not None
            or item.current_weight is not None
            for item in rows
        )
        accumulation = None
        distribution = None
        if comparable:
            denominator = Decimal(comparable)
            accumulation = Decimal(new_count + increase_count) / denominator
            distribution = Decimal(exit_count + decrease_count) / denominator

        output.append(
            StockFundActivity(
                symbol=symbol,
                current_fund_count=current_fund_count,
                comparable_fund_count=comparable,
                new_fund_count=new_count,
                exited_fund_count=exit_count,
                increasing_fund_count=increase_count,
                decreasing_fund_count=decrease_count,
                unchanged_fund_count=unchanged_count,
                unknown_fund_count=unknown_count,
                accumulation_breadth=accumulation,
                distribution_breadth=distribution,
            )
        )
    return tuple(output)


def _snapshot_to_primitive(snapshot: FundPortfolioSnapshot) -> dict[str, object]:
    return {
        "record_type": "FundPortfolioSnapshot",
        "snapshot_id": snapshot.snapshot_id,
        "canonical_fund_id": snapshot.canonical_fund_id,
        "portfolio_date": snapshot.portfolio_date.isoformat(),
        "publication_date": snapshot.publication_date.isoformat(),
        "ingested_at": snapshot.ingested_at.isoformat(),
        "provider": snapshot.provider,
        "data_quality_state": snapshot.data_quality_state.value,
        "source_reference": snapshot.source_reference,
        "positions": [
            {
                "canonical_fund_id": item.canonical_fund_id,
                "portfolio_date": item.portfolio_date.isoformat(),
                "symbol": item.symbol,
                "asset_type": item.asset_type,
                "asset_name": item.asset_name,
                "shares_held": None if item.shares_held is None else str(item.shares_held),
                "market_value": None if item.market_value is None else str(item.market_value),
                "portfolio_weight": None if item.portfolio_weight is None else str(item.portfolio_weight),
            }
            for item in snapshot.positions
        ],
    }


class FundPortfolioSnapshotJsonStore:
    """Append-only tarihli fon portföy snapshot deposu.

    Aynı fon/tarih/provider kimliği farklı içerikle yeniden gelirse sessizce
    overwrite etmez; conflict üretir. Böylece tarihsel değişim kanıtı korunur.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def _read(self) -> dict[str, dict[str, object]]:
        if not self.path.exists():
            return {}
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise PortfolioSnapshotStoreError("Fon portföy snapshot deposu okunamadı.") from exc
        if not isinstance(payload, dict):
            raise PortfolioSnapshotStoreError("Fon portföy snapshot deposu nesne biçiminde olmalıdır.")
        return payload

    @staticmethod
    def _key(snapshot: FundPortfolioSnapshot) -> str:
        return f"{snapshot.canonical_fund_id}|{snapshot.portfolio_date.isoformat()}|{snapshot.provider}"

    def append(self, snapshots: Iterable[FundPortfolioSnapshot]) -> PortfolioSnapshotStoreResult:
        existing = self._read()
        inserted = unchanged = 0
        for snapshot in sorted(snapshots, key=self._key):
            key = self._key(snapshot)
            record = _snapshot_to_primitive(snapshot)
            digest = hashlib.sha256(
                json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest()
            stored = existing.get(key)
            if stored is None:
                existing[key] = {**record, "_digest": digest}
                inserted += 1
                continue
            if stored.get("_digest") == digest:
                unchanged += 1
                continue
            raise PortfolioSnapshotStoreError(f"PORTFOLIO_SNAPSHOT_CONFLICT:{key}")

        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(self.path.suffix + ".tmp")
        temp.write_text(json.dumps(existing, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        temp.replace(self.path)
        return PortfolioSnapshotStoreResult(inserted, unchanged, len(existing))

    def list_records(self) -> tuple[dict[str, object], ...]:
        payload = self._read()
        return tuple(payload[key] for key in sorted(payload))

    def list_snapshots(self) -> tuple[FundPortfolioSnapshot, ...]:
        """Persisted kayıtları typed read model olarak döndürür; store üzerinde mutation yapmaz."""
        snapshots: list[FundPortfolioSnapshot] = []
        for record in self.list_records():
            try:
                portfolio_date = date.fromisoformat(str(record["portfolio_date"]))
                positions_raw = record.get("positions", ())
                if not isinstance(positions_raw, list):
                    raise ValueError("positions liste biçiminde olmalıdır.")
                positions = tuple(
                    FundPortfolioPosition(
                        canonical_fund_id=str(item["canonical_fund_id"]),
                        portfolio_date=date.fromisoformat(str(item["portfolio_date"])),
                        symbol=str(item["symbol"]),
                        asset_type=str(item["asset_type"]),
                        asset_name=None if item.get("asset_name") is None else str(item.get("asset_name")),
                        shares_held=None if item.get("shares_held") is None else Decimal(str(item.get("shares_held"))),
                        market_value=None if item.get("market_value") is None else Decimal(str(item.get("market_value"))),
                        portfolio_weight=None if item.get("portfolio_weight") is None else Decimal(str(item.get("portfolio_weight"))),
                    )
                    for item in positions_raw
                    if isinstance(item, dict)
                )
                snapshots.append(
                    FundPortfolioSnapshot(
                        canonical_fund_id=str(record["canonical_fund_id"]),
                        portfolio_date=portfolio_date,
                        publication_date=date.fromisoformat(str(record["publication_date"])),
                        ingested_at=datetime.fromisoformat(str(record["ingested_at"])),
                        provider=str(record["provider"]),
                        positions=positions,
                        data_quality_state=DataQualityState(str(record["data_quality_state"])),
                        source_reference=None if record.get("source_reference") is None else str(record.get("source_reference")),
                    )
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise PortfolioSnapshotStoreError("Fon portföy snapshot kaydı çözümlenemedi.") from exc
        return tuple(
            sorted(
                snapshots,
                key=lambda item: (item.canonical_fund_id, item.provider, item.portfolio_date, item.publication_date, item.ingested_at),
            )
        )


DEFAULT_FUND_PORTFOLIO_SNAPSHOT_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "funds" / "portfolio_snapshots.json"
)


def fund_portfolio_snapshot_store(path: str | Path | None = None) -> FundPortfolioSnapshotJsonStore:
    return FundPortfolioSnapshotJsonStore(
        DEFAULT_FUND_PORTFOLIO_SNAPSHOT_PATH if path is None else path
    )

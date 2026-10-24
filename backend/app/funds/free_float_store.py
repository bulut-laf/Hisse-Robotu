from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from io import StringIO
import csv
import json
from pathlib import Path
from typing import Iterable, Mapping


DEFAULT_MAX_AGE_DAYS = 45


class FreeFloatSourceError(RuntimeError):
    """Canonical fiili dolaşım veri sözleşmesi hatası."""


@dataclass(frozen=True, slots=True)
class FreeFloatRecord:
    symbol: str
    free_float_shares: Decimal
    as_of: date
    source: str
    source_ref: str
    ingested_at: datetime

    def __post_init__(self) -> None:
        symbol = self.symbol.strip().upper()
        if symbol.endswith(".IS"):
            symbol = symbol[:-3]
        if not symbol:
            raise ValueError("FREE_FLOAT_SYMBOL_MISSING")
        shares = Decimal(str(self.free_float_shares))
        if not shares.is_finite() or shares <= 0:
            raise ValueError("FREE_FLOAT_SHARES_INVALID")
        source = self.source.strip().upper()
        if source not in {"KAP", "MKK"}:
            raise ValueError("FREE_FLOAT_SOURCE_NOT_CANONICAL")
        ref = self.source_ref.strip()
        if not ref:
            raise ValueError("FREE_FLOAT_SOURCE_REF_MISSING")
        object.__setattr__(self, "symbol", symbol)
        object.__setattr__(self, "free_float_shares", shares)
        object.__setattr__(self, "source", source)
        object.__setattr__(self, "source_ref", ref)


@dataclass(frozen=True, slots=True)
class FreeFloatStoreResult:
    inserted: int
    unchanged: int
    total_records: int


@dataclass(frozen=True, slots=True)
class FreeFloatReadResult:
    shares_by_symbol: Mapping[str, Decimal]
    stale_symbols: tuple[str, ...]
    source_state: str


class FreeFloatJsonStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def _load(self) -> list[FreeFloatRecord]:
        if not self.path.exists():
            return []
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError) as exc:
            raise FreeFloatSourceError("FREE_FLOAT_STORE_READ_FAILED") from exc
        if not isinstance(raw, list):
            raise FreeFloatSourceError("FREE_FLOAT_STORE_FORMAT_INVALID")
        out: list[FreeFloatRecord] = []
        for item in raw:
            try:
                out.append(
                    FreeFloatRecord(
                        symbol=str(item["symbol"]),
                        free_float_shares=Decimal(str(item["free_float_shares"])),
                        as_of=date.fromisoformat(str(item["as_of"])),
                        source=str(item["source"]),
                        source_ref=str(item["source_ref"]),
                        ingested_at=datetime.fromisoformat(str(item["ingested_at"])),
                    )
                )
            except (KeyError, ValueError, TypeError, InvalidOperation) as exc:
                raise FreeFloatSourceError("FREE_FLOAT_STORE_RECORD_INVALID") from exc
        return out

    def list_records(self) -> tuple[FreeFloatRecord, ...]:
        return tuple(self._load())

    def upsert(self, records: Iterable[FreeFloatRecord]) -> FreeFloatStoreResult:
        existing = self._load()
        by_key = {
            (item.symbol, item.as_of.isoformat(), item.source, item.source_ref): item
            for item in existing
        }
        inserted = unchanged = 0
        for item in records:
            key = (item.symbol, item.as_of.isoformat(), item.source, item.source_ref)
            previous = by_key.get(key)
            if previous is not None and previous.free_float_shares == item.free_float_shares:
                unchanged += 1
                continue
            by_key[key] = item
            inserted += 1
        ordered = sorted(
            by_key.values(),
            key=lambda item: (item.symbol, item.as_of, item.source, item.source_ref),
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = [
            {
                "symbol": item.symbol,
                "free_float_shares": str(item.free_float_shares),
                "as_of": item.as_of.isoformat(),
                "source": item.source,
                "source_ref": item.source_ref,
                "ingested_at": item.ingested_at.isoformat(),
            }
            for item in ordered
        ]
        self.path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return FreeFloatStoreResult(inserted, unchanged, len(ordered))


def default_free_float_store(path: str | Path | None = None) -> FreeFloatJsonStore:
    if path is not None:
        return FreeFloatJsonStore(path)
    root = Path(__file__).resolve().parents[2]
    return FreeFloatJsonStore(root / "data" / "funds" / "free_float_snapshots.json")


def read_canonical_free_float(
    store: FreeFloatJsonStore,
    *,
    as_of: date | None = None,
    max_age_days: int = DEFAULT_MAX_AGE_DAYS,
) -> FreeFloatReadResult:
    today = as_of or date.today()
    latest: dict[str, FreeFloatRecord] = {}
    for item in store.list_records():
        current = latest.get(item.symbol)
        if current is None or item.as_of > current.as_of:
            latest[item.symbol] = item

    shares: dict[str, Decimal] = {}
    stale: list[str] = []
    for symbol, item in sorted(latest.items()):
        age = (today - item.as_of).days
        if age < 0 or age > max_age_days:
            stale.append(symbol)
            continue
        shares[symbol] = item.free_float_shares

    if shares:
        state = "READY" if not stale else "PARTIAL"
    elif latest:
        state = "STALE"
    else:
        state = "UNAVAILABLE"
    return FreeFloatReadResult(shares, tuple(stale), state)


def _first(record: Mapping[str, object], *names: str) -> object | None:
    lowered = {str(k).strip().lower(): v for k, v in record.items()}
    for name in names:
        value = lowered.get(name.lower())
        if value not in (None, ""):
            return value
    return None


def _decimal(value: object) -> Decimal:
    raw = str(value).strip().replace(" ", "")
    if "," in raw and "." in raw:
        if raw.rfind(",") > raw.rfind("."):
            raw = raw.replace(".", "").replace(",", ".")
        else:
            raw = raw.replace(",", "")
    elif "," in raw:
        raw = raw.replace(",", ".")
    return Decimal(raw)


def free_float_records_from_bytes(
    data: bytes,
    *,
    suffix: str,
    ingested_at: datetime | None = None,
) -> tuple[FreeFloatRecord, ...]:
    suffix = suffix.strip().lower()
    if suffix == ".csv":
        records = list(csv.DictReader(StringIO(data.decode("utf-8-sig"))))
    elif suffix == ".json":
        payload = json.loads(data.decode("utf-8-sig"))
        if isinstance(payload, list):
            records = payload
        elif isinstance(payload, Mapping):
            source = payload.get("records", payload.get("data", [payload]))
            records = source if isinstance(source, list) else [payload]
        else:
            records = []
    else:
        raise FreeFloatSourceError("FREE_FLOAT_IMPORT_FORMAT_UNSUPPORTED")

    now = ingested_at or datetime.now(timezone.utc)
    out: list[FreeFloatRecord] = []
    for record in records:
        if not isinstance(record, Mapping):
            continue
        symbol = _first(record, "symbol", "sembol", "hisse", "borsa_kodu")
        shares = _first(
            record,
            "free_float_shares",
            "free_float_lot",
            "fiili_dolasim_lot",
            "fiili_dolasimdaki_pay_tutari",
        )
        as_of_raw = _first(record, "as_of", "date", "tarih", "source_date")
        source = _first(record, "source", "kaynak")
        source_ref = _first(record, "source_ref", "source_url", "kaynak_ref", "url")
        if None in (symbol, shares, as_of_raw, source, source_ref):
            continue
        try:
            out.append(
                FreeFloatRecord(
                    symbol=str(symbol),
                    free_float_shares=_decimal(shares),
                    as_of=date.fromisoformat(str(as_of_raw)[:10]),
                    source=str(source),
                    source_ref=str(source_ref),
                    ingested_at=now,
                )
            )
        except (ValueError, InvalidOperation):
            continue
    if not out:
        raise FreeFloatSourceError("FREE_FLOAT_IMPORT_NO_VALID_CANONICAL_RECORD")
    return tuple(out)

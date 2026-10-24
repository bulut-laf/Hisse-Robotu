from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import date, datetime, timedelta, timezone
import csv
import io
import json
import math
from pathlib import Path
from typing import Callable, Iterable

import pandas as pd
import yfinance as yf

from .signal_outcome_tracking import SignalOutcome, SignalSnapshot


class ShadowPortfolioError(ValueError):
    """Gölge portföy işlemi tamamlanamadı."""


OPEN_STATUS = "Açık"
CLOSED_STATUS = "Kapalı"


@dataclass(frozen=True)
class ShadowPosition:
    symbol: str
    entry_date: date
    entry_price: float
    quantity: int
    capital_at_entry: float
    stop_loss: float | None = None
    target_1: float | None = None
    target_2: float | None = None
    signal_record_id: str = ""
    signal_class: str = ""
    quality_score: int | None = None
    market_regime: str = ""
    sector: str = ""
    rationale: str = ""
    status: str = OPEN_STATUS
    last_price: float | None = None
    last_price_date: date | None = None
    exit_date: date | None = None
    exit_price: float | None = None
    close_reason: str = ""
    mfe_percent: float | None = None
    mae_percent: float | None = None
    target_1_hit: bool = False
    target_2_hit: bool = False
    stop_hit: bool = False
    fees: float = 0.0
    record_id: str = ""
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self) -> None:
        symbol = self.symbol.strip().upper().removeprefix("﻿")
        if not symbol:
            raise ShadowPortfolioError("Sembol boş olamaz.")
        if not symbol.endswith(".IS"):
            symbol += ".IS"
        object.__setattr__(self, "symbol", symbol)

        if self.status not in (OPEN_STATUS, CLOSED_STATUS):
            raise ShadowPortfolioError("Pozisyon durumu Açık veya Kapalı olmalıdır.")
        if not math.isfinite(self.entry_price) or self.entry_price <= 0:
            raise ShadowPortfolioError("Giriş fiyatı sıfırdan büyük olmalıdır.")
        if self.quantity < 1:
            raise ShadowPortfolioError("Lot sayısı en az 1 olmalıdır.")
        if not math.isfinite(self.capital_at_entry) or self.capital_at_entry <= 0:
            raise ShadowPortfolioError("Sermaye sıfırdan büyük olmalıdır.")
        if not math.isfinite(self.fees) or self.fees < 0:
            raise ShadowPortfolioError("Masraf negatif olamaz.")
        if self.quality_score is not None and not 0 <= self.quality_score <= 100:
            raise ShadowPortfolioError("Kalite skoru 0–100 arasında olmalıdır.")

        for name, value in (
            ("Stop", self.stop_loss),
            ("Hedef 1", self.target_1),
            ("Hedef 2", self.target_2),
            ("Son fiyat", self.last_price),
            ("Çıkış fiyatı", self.exit_price),
        ):
            if value is not None and (
                not math.isfinite(value) or value <= 0
            ):
                raise ShadowPortfolioError(
                    f"{name} sıfırdan büyük olmalıdır."
                )

        if self.status == CLOSED_STATUS:
            if self.exit_date is None or self.exit_price is None:
                raise ShadowPortfolioError(
                    "Kapalı pozisyonda çıkış tarihi ve fiyatı zorunludur."
                )
            if self.exit_date < self.entry_date:
                raise ShadowPortfolioError(
                    "Çıkış tarihi giriş tarihinden önce olamaz."
                )

        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        object.__setattr__(self, "created_at", self.created_at or now)
        object.__setattr__(self, "updated_at", self.updated_at or now)

        if not self.record_id:
            import hashlib
            raw = "|".join(
                (
                    symbol,
                    self.entry_date.isoformat(),
                    f"{self.entry_price:.8f}",
                    str(self.quantity),
                    self.signal_record_id,
                )
            )
            object.__setattr__(
                self,
                "record_id",
                hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16],
            )

    @property
    def position_amount(self) -> float:
        return self.entry_price * self.quantity

    @property
    def current_price(self) -> float:
        if self.status == CLOSED_STATUS and self.exit_price is not None:
            return self.exit_price
        return self.last_price or self.entry_price

    @property
    def unrealized_pnl(self) -> float:
        if self.status == CLOSED_STATUS:
            return 0.0
        return (self.current_price - self.entry_price) * self.quantity

    @property
    def realized_pnl(self) -> float:
        if self.status != CLOSED_STATUS or self.exit_price is None:
            return 0.0
        return (
            (self.exit_price - self.entry_price) * self.quantity
            - self.fees
        )

    @property
    def return_percent(self) -> float:
        pnl = (
            self.realized_pnl
            if self.status == CLOSED_STATUS
            else self.unrealized_pnl
        )
        return pnl / self.position_amount * 100.0

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        for field_name in ("entry_date", "last_price_date", "exit_date"):
            value = data[field_name]
            data[field_name] = value.isoformat() if value else None
        return data

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "ShadowPosition":
        values = dict(data)
        for field_name in ("entry_date", "last_price_date", "exit_date"):
            value = values.get(field_name)
            if value:
                values[field_name] = date.fromisoformat(str(value))
            else:
                values[field_name] = None
        return cls(**values)


class ShadowPortfolioStore:
    def __init__(self, file_path: str | Path | None = None) -> None:
        self.file_path = (
            Path(file_path).expanduser()
            if file_path is not None
            else Path.home() / ".hisse_robotu" / "golge_portfoy.json"
        )

    def list(self) -> tuple[ShadowPosition, ...]:
        if not self.file_path.exists():
            return ()
        try:
            raw = json.loads(
                self.file_path.read_text(encoding="utf-8-sig")
            )
            if not isinstance(raw, list):
                raise ShadowPortfolioError(
                    "Gölge portföy liste biçiminde değil."
                )
            records = tuple(
                ShadowPosition.from_dict(item)
                for item in raw
            )
            return tuple(
                sorted(
                    records,
                    key=lambda item: (
                        item.status != OPEN_STATUS,
                        item.entry_date,
                        item.record_id,
                    ),
                    reverse=True,
                )
            )
        except (
            OSError,
            TypeError,
            ValueError,
            json.JSONDecodeError,
        ) as error:
            if isinstance(error, ShadowPortfolioError):
                raise
            raise ShadowPortfolioError(
                f"Gölge portföy okunamadı: {error}"
            ) from error

    def save(self, position: ShadowPosition) -> ShadowPosition:
        records = {
            item.record_id: item
            for item in self.list()
        }
        records[position.record_id] = position
        self._write(records.values())
        return position

    def delete(self, record_id: str) -> bool:
        records = list(self.list())
        filtered = [
            item for item in records
            if item.record_id != record_id
        ]
        if len(filtered) == len(records):
            return False
        self._write(filtered)
        return True

    def find_open(self, symbol: str) -> ShadowPosition | None:
        normalized = symbol.strip().upper()
        if not normalized.endswith(".IS"):
            normalized += ".IS"
        return next(
            (
                item
                for item in self.list()
                if item.symbol == normalized
                and item.status == OPEN_STATUS
            ),
            None,
        )

    def _write(self, records: Iterable[ShadowPosition]) -> None:
        try:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            temp = self.file_path.with_suffix(
                self.file_path.suffix + ".tmp"
            )
            temp.write_text(
                json.dumps(
                    [item.to_dict() for item in records],
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            temp.replace(self.file_path)
        except OSError as error:
            raise ShadowPortfolioError(
                f"Gölge portföy yazılamadı: {error}"
            ) from error


def open_shadow_position(
    *,
    store: ShadowPortfolioStore,
    symbol: str,
    entry_date: date,
    entry_price: float,
    quantity: int,
    capital_at_entry: float,
    stop_loss: float | None = None,
    target_1: float | None = None,
    target_2: float | None = None,
    signal_record_id: str = "",
    signal_class: str = "",
    quality_score: int | None = None,
    market_regime: str = "",
    sector: str = "",
    rationale: str = "",
) -> ShadowPosition:
    existing = store.find_open(symbol)
    if existing is not None:
        raise ShadowPortfolioError(
            f"{existing.symbol} için açık gölge pozisyon zaten var."
        )

    position = ShadowPosition(
        symbol=symbol,
        entry_date=entry_date,
        entry_price=entry_price,
        quantity=quantity,
        capital_at_entry=capital_at_entry,
        stop_loss=stop_loss,
        target_1=target_1,
        target_2=target_2,
        signal_record_id=signal_record_id,
        signal_class=signal_class,
        quality_score=quality_score,
        market_regime=market_regime,
        sector=sector,
        rationale=rationale,
        last_price=entry_price,
        last_price_date=entry_date,
    )
    return store.save(position)


def open_from_signal(
    outcome: SignalOutcome,
    *,
    store: ShadowPortfolioStore,
    quantity: int,
    capital_at_entry: float,
    rationale: str = "",
) -> ShadowPosition:
    snapshot = outcome.snapshot
    return open_shadow_position(
        store=store,
        symbol=snapshot.symbol,
        entry_date=snapshot.signal_date,
        entry_price=snapshot.reference_price,
        quantity=quantity,
        capital_at_entry=capital_at_entry,
        stop_loss=snapshot.stop_loss,
        target_1=snapshot.target_1,
        target_2=snapshot.target_2,
        signal_record_id=snapshot.record_id,
        signal_class=snapshot.decision_class,
        quality_score=snapshot.quality_score,
        market_regime=snapshot.market_regime,
        sector=snapshot.sector,
        rationale=rationale,
    )


def close_shadow_position(
    position: ShadowPosition,
    *,
    store: ShadowPortfolioStore,
    exit_date: date,
    exit_price: float,
    close_reason: str,
    fees: float = 0.0,
) -> ShadowPosition:
    if position.status != OPEN_STATUS:
        raise ShadowPortfolioError("Pozisyon zaten kapalıdır.")

    updated = replace(
        position,
        status=CLOSED_STATUS,
        exit_date=exit_date,
        exit_price=exit_price,
        last_price=exit_price,
        last_price_date=exit_date,
        close_reason=close_reason.strip(),
        fees=fees,
        updated_at=datetime.now(timezone.utc).isoformat(
            timespec="seconds"
        ),
    )
    return store.save(updated)


def _normalize_history(frame: pd.DataFrame) -> pd.DataFrame:
    if frame is None or frame.empty:
        raise ShadowPortfolioError("Fiyat verisi bulunamadı.")
    normalized = frame.copy()
    if isinstance(normalized.columns, pd.MultiIndex):
        normalized.columns = normalized.columns.get_level_values(0)
    required = {"Close", "High", "Low"}
    missing = required - set(normalized.columns)
    if missing:
        raise ShadowPortfolioError(
            "Eksik fiyat sütunları: " + ", ".join(sorted(missing))
        )
    normalized = normalized.loc[:, ["Close", "High", "Low"]].copy()
    normalized.index = pd.to_datetime(
        normalized.index
    ).tz_localize(None)
    for column in normalized.columns:
        normalized[column] = pd.to_numeric(
            normalized[column],
            errors="coerce",
        )
    normalized = normalized.dropna().sort_index()
    if normalized.empty:
        raise ShadowPortfolioError(
            "Fiyat verisi kullanılabilir kayıt içermiyor."
        )
    return normalized


def refresh_position(
    position: ShadowPosition,
    frame: pd.DataFrame,
    *,
    store: ShadowPortfolioStore,
) -> ShadowPosition:
    if position.status != OPEN_STATUS:
        return position
    normalized = _normalize_history(frame)
    relevant = normalized.loc[
        normalized.index.date >= position.entry_date
    ]
    if relevant.empty:
        raise ShadowPortfolioError(
            "Pozisyon tarihinden sonraki fiyat verisi bulunamadı."
        )

    last = relevant.iloc[-1]
    last_date = relevant.index[-1].date()
    mfe = (
        float(relevant["High"].max()) / position.entry_price - 1.0
    ) * 100.0
    mae = (
        float(relevant["Low"].min()) / position.entry_price - 1.0
    ) * 100.0

    updated = replace(
        position,
        last_price=float(last["Close"]),
        last_price_date=last_date,
        mfe_percent=round(mfe, 4),
        mae_percent=round(mae, 4),
        target_1_hit=(
            position.target_1 is not None
            and float(relevant["High"].max()) >= position.target_1
        ),
        target_2_hit=(
            position.target_2 is not None
            and float(relevant["High"].max()) >= position.target_2
        ),
        stop_hit=(
            position.stop_loss is not None
            and float(relevant["Low"].min()) <= position.stop_loss
        ),
        updated_at=datetime.now(timezone.utc).isoformat(
            timespec="seconds"
        ),
    )
    return store.save(updated)


def refresh_all_open_positions(
    *,
    store: ShadowPortfolioStore,
    downloader: Callable[..., pd.DataFrame] = yf.download,
    today: date | None = None,
) -> tuple[int, int, tuple[str, ...]]:
    updated = 0
    failed = 0
    errors: list[str] = []
    end_date = today or date.today()

    for position in store.list():
        if position.status != OPEN_STATUS:
            continue
        try:
            raw = downloader(
                tickers=position.symbol,
                start=position.entry_date.isoformat(),
                end=(end_date + timedelta(days=1)).isoformat(),
                interval="1d",
                auto_adjust=True,
                progress=False,
                threads=False,
                timeout=30,
            )
            refresh_position(position, raw, store=store)
            updated += 1
        except (
            ShadowPortfolioError,
            OSError,
            ValueError,
            TypeError,
        ) as error:
            failed += 1
            errors.append(f"{position.symbol}: {error}")

    return updated, failed, tuple(errors)


def position_rows(
    positions: Iterable[ShadowPosition],
) -> list[dict[str, object]]:
    return [
        {
            "Durum": item.status,
            "Sembol": item.symbol,
            "Giriş tarihi": item.entry_date.isoformat(),
            "Giriş fiyatı": item.entry_price,
            "Son/çıkış fiyatı": item.current_price,
            "Lot": item.quantity,
            "Pozisyon tutarı": item.position_amount,
            "Gerçekleşmemiş K/Z": item.unrealized_pnl,
            "Gerçekleşen K/Z": item.realized_pnl,
            "Getiri (%)": item.return_percent,
            "MFE (%)": item.mfe_percent,
            "MAE (%)": item.mae_percent,
            "Hedef 1": item.target_1_hit,
            "Hedef 2": item.target_2_hit,
            "Stop": item.stop_hit,
            "Sinyal sınıfı": item.signal_class,
            "Kalite": item.quality_score,
            "Rejim": item.market_regime,
            "Sektör": item.sector,
            "Kapanış nedeni": item.close_reason,
            "Kayıt": item.record_id,
        }
        for item in positions
    ]


def positions_to_csv(
    positions: Iterable[ShadowPosition],
) -> bytes:
    rows = position_rows(positions)
    output = io.StringIO()
    fieldnames = list(rows[0]) if rows else [
        "Durum",
        "Sembol",
        "Giriş tarihi",
        "Giriş fiyatı",
        "Son/çıkış fiyatı",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    return ("\ufeff" + output.getvalue()).encode("utf-8")

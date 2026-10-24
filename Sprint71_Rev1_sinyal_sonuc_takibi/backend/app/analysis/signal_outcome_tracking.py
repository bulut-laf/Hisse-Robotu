from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
import csv
import io
import json
import math
from pathlib import Path
from typing import Iterable

import pandas as pd


HORIZONS = (5, 10, 20)


class SignalOutcomeError(ValueError):
    """Sinyal sonuç takibi üretilemedi."""


@dataclass(frozen=True)
class SignalSnapshot:
    symbol: str
    signal_date: date
    reference_price: float
    decision_class: str
    quality_score: int
    daily_direction: str
    weekly_direction: str
    divergence_type: str = ""
    market_regime: str = ""
    sector: str = ""
    stop_loss: float | None = None
    target_1: float | None = None
    target_2: float | None = None
    record_id: str = ""
    created_at: str = ""

    def __post_init__(self) -> None:
        symbol = self.symbol.strip().upper().removeprefix("﻿")
        if not symbol:
            raise SignalOutcomeError("Sembol boş olamaz.")
        if not symbol.endswith(".IS"):
            symbol += ".IS"
        object.__setattr__(self, "symbol", symbol)

        if not math.isfinite(self.reference_price) or self.reference_price <= 0:
            raise SignalOutcomeError(
                "Referans fiyat sıfırdan büyük olmalıdır."
            )
        if not 0 <= self.quality_score <= 100:
            raise SignalOutcomeError("Kalite skoru 0–100 arasında olmalıdır.")

        for name, value in (
            ("Stop", self.stop_loss),
            ("Hedef 1", self.target_1),
            ("Hedef 2", self.target_2),
        ):
            if value is not None and (
                not math.isfinite(value) or value <= 0
            ):
                raise SignalOutcomeError(
                    f"{name} sıfırdan büyük olmalıdır."
                )

        if not self.record_id:
            raw = "|".join(
                (
                    symbol,
                    self.signal_date.isoformat(),
                    f"{self.reference_price:.8f}",
                    self.decision_class.strip(),
                    str(self.quality_score),
                    self.daily_direction.strip(),
                    self.weekly_direction.strip(),
                )
            )
            import hashlib
            object.__setattr__(
                self,
                "record_id",
                hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16],
            )

        if not self.created_at:
            object.__setattr__(
                self,
                "created_at",
                datetime.now(timezone.utc).isoformat(timespec="seconds"),
            )


@dataclass(frozen=True)
class HorizonOutcome:
    horizon: int
    available: bool
    end_date: date | None
    close_return_percent: float | None
    maximum_favorable_excursion_percent: float | None
    maximum_adverse_excursion_percent: float | None
    target_1_hit: bool | None
    target_2_hit: bool | None
    stop_hit: bool | None


@dataclass(frozen=True)
class SignalOutcome:
    snapshot: SignalSnapshot
    horizons: tuple[HorizonOutcome, ...]
    evaluated_at: str

    @property
    def completed_horizons(self) -> int:
        return sum(item.available for item in self.horizons)


def _normalize_price_frame(frame: pd.DataFrame) -> pd.DataFrame:
    required = {"Close", "High", "Low"}
    missing = required - set(frame.columns)
    if missing:
        raise SignalOutcomeError(
            "Performans ölçümü için eksik sütunlar: "
            + ", ".join(sorted(missing))
        )

    normalized = frame.loc[:, ["Close", "High", "Low"]].copy()
    normalized.index = pd.to_datetime(normalized.index)
    normalized = normalized.sort_index()

    if normalized.index.has_duplicates:
        raise SignalOutcomeError(
            "Fiyat verisinde tekrarlanan tarih var."
        )
    if normalized.empty:
        raise SignalOutcomeError("Fiyat verisi boş.")

    return normalized.astype(float)


def evaluate_signal(
    snapshot: SignalSnapshot,
    price_frame: pd.DataFrame,
) -> SignalOutcome:
    """
    Sinyal tarihinden sonraki barları yalnızca performans ölçümünde kullanır.
    Aday veya sinyal üretimi yapmaz.
    """
    frame = _normalize_price_frame(price_frame)
    signal_ts = pd.Timestamp(snapshot.signal_date)

    future = frame.loc[frame.index > signal_ts]
    outcomes: list[HorizonOutcome] = []

    for horizon in HORIZONS:
        if len(future) < horizon:
            outcomes.append(
                HorizonOutcome(
                    horizon=horizon,
                    available=False,
                    end_date=None,
                    close_return_percent=None,
                    maximum_favorable_excursion_percent=None,
                    maximum_adverse_excursion_percent=None,
                    target_1_hit=None,
                    target_2_hit=None,
                    stop_hit=None,
                )
            )
            continue

        window = future.iloc[:horizon]
        end_close = float(window["Close"].iloc[-1])
        highest = float(window["High"].max())
        lowest = float(window["Low"].min())
        reference = snapshot.reference_price

        outcomes.append(
            HorizonOutcome(
                horizon=horizon,
                available=True,
                end_date=pd.Timestamp(window.index[-1]).date(),
                close_return_percent=round(
                    (end_close / reference - 1.0) * 100.0,
                    4,
                ),
                maximum_favorable_excursion_percent=round(
                    (highest / reference - 1.0) * 100.0,
                    4,
                ),
                maximum_adverse_excursion_percent=round(
                    (lowest / reference - 1.0) * 100.0,
                    4,
                ),
                target_1_hit=(
                    None
                    if snapshot.target_1 is None
                    else highest >= snapshot.target_1
                ),
                target_2_hit=(
                    None
                    if snapshot.target_2 is None
                    else highest >= snapshot.target_2
                ),
                stop_hit=(
                    None
                    if snapshot.stop_loss is None
                    else lowest <= snapshot.stop_loss
                ),
            )
        )

    return SignalOutcome(
        snapshot=snapshot,
        horizons=tuple(outcomes),
        evaluated_at=datetime.now(timezone.utc).isoformat(
            timespec="seconds"
        ),
    )


class SignalOutcomeJsonStore:
    def __init__(self, root: str | Path | None = None) -> None:
        self.root = (
            Path(root).expanduser()
            if root is not None
            else Path.home() / ".hisse_robotu" / "sinyal_sonuclari"
        )

    def save(
        self,
        outcome: SignalOutcome,
    ) -> Path:
        self.root.mkdir(parents=True, exist_ok=True)
        path = self.root / f"{outcome.snapshot.record_id}.json"
        path.write_text(
            json.dumps(
                {
                    "snapshot": asdict(outcome.snapshot),
                    "horizons": [
                        asdict(item) for item in outcome.horizons
                    ],
                    "evaluated_at": outcome.evaluated_at,
                },
                ensure_ascii=False,
                indent=2,
                default=str,
            ),
            encoding="utf-8",
        )
        return path

    def list(self) -> tuple[SignalOutcome, ...]:
        if not self.root.exists():
            return ()

        records: list[SignalOutcome] = []
        for path in sorted(self.root.glob("*.json"), reverse=True):
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
                snapshot_raw = dict(raw["snapshot"])
                snapshot_raw["signal_date"] = date.fromisoformat(
                    snapshot_raw["signal_date"]
                )
                snapshot = SignalSnapshot(**snapshot_raw)

                horizons = []
                for item in raw["horizons"]:
                    item = dict(item)
                    if item.get("end_date"):
                        item["end_date"] = date.fromisoformat(
                            item["end_date"]
                        )
                    horizons.append(HorizonOutcome(**item))

                records.append(
                    SignalOutcome(
                        snapshot=snapshot,
                        horizons=tuple(horizons),
                        evaluated_at=str(raw["evaluated_at"]),
                    )
                )
            except (KeyError, TypeError, ValueError, json.JSONDecodeError):
                continue

        return tuple(records)


def outcome_rows(
    outcomes: Iterable[SignalOutcome],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for outcome in outcomes:
        base = {
            "Kayıt": outcome.snapshot.record_id,
            "Sembol": outcome.snapshot.symbol,
            "Sinyal tarihi": outcome.snapshot.signal_date,
            "Referans fiyat": outcome.snapshot.reference_price,
            "Karar sınıfı": outcome.snapshot.decision_class,
            "Kalite skoru": outcome.snapshot.quality_score,
            "Günlük yön": outcome.snapshot.daily_direction,
            "Haftalık yön": outcome.snapshot.weekly_direction,
            "Uyumsuzluk": outcome.snapshot.divergence_type or "—",
            "Piyasa rejimi": outcome.snapshot.market_regime or "—",
            "Sektör": outcome.snapshot.sector or "—",
        }
        for item in outcome.horizons:
            row = dict(base)
            row.update(
                {
                    "Ufuk": f"{item.horizon} işlem günü",
                    "Tamamlandı": "Evet" if item.available else "Hayır",
                    "Bitiş tarihi": item.end_date,
                    "Kapanış getirisi (%)": item.close_return_percent,
                    "MFE (%)": item.maximum_favorable_excursion_percent,
                    "MAE (%)": item.maximum_adverse_excursion_percent,
                    "Hedef 1": (
                        "—"
                        if item.target_1_hit is None
                        else "Ulaştı"
                        if item.target_1_hit
                        else "Ulaşmadı"
                    ),
                    "Hedef 2": (
                        "—"
                        if item.target_2_hit is None
                        else "Ulaştı"
                        if item.target_2_hit
                        else "Ulaşmadı"
                    ),
                    "Stop": (
                        "—"
                        if item.stop_hit is None
                        else "Çalıştı"
                        if item.stop_hit
                        else "Çalışmadı"
                    ),
                }
            )
            rows.append(row)
    return rows


def success_summary(
    outcomes: Iterable[SignalOutcome],
    *,
    horizon: int,
) -> dict[str, object]:
    selected = []
    for outcome in outcomes:
        item = next(
            (
                candidate
                for candidate in outcome.horizons
                if candidate.horizon == horizon
            ),
            None,
        )
        if item is not None and item.available:
            selected.append((outcome, item))

    if not selected:
        return {
            "Ufuk": horizon,
            "Tamamlanan kayıt": 0,
            "Pozitif kapanış oranı (%)": None,
            "Ortalama getiri (%)": None,
            "Ortalama MFE (%)": None,
            "Ortalama MAE (%)": None,
        }

    returns = [item.close_return_percent for _, item in selected]
    mfes = [
        item.maximum_favorable_excursion_percent
        for _, item in selected
    ]
    maes = [
        item.maximum_adverse_excursion_percent
        for _, item in selected
    ]

    return {
        "Ufuk": horizon,
        "Tamamlanan kayıt": len(selected),
        "Pozitif kapanış oranı (%)": round(
            sum(value > 0 for value in returns) / len(returns) * 100,
            2,
        ),
        "Ortalama getiri (%)": round(sum(returns) / len(returns), 2),
        "Ortalama MFE (%)": round(sum(mfes) / len(mfes), 2),
        "Ortalama MAE (%)": round(sum(maes) / len(maes), 2),
    }


def outcomes_to_csv(outcomes: Iterable[SignalOutcome]) -> bytes:
    rows = outcome_rows(outcomes)
    output = io.StringIO()
    fieldnames = list(rows[0]) if rows else [
        "Kayıt",
        "Sembol",
        "Sinyal tarihi",
        "Ufuk",
        "Tamamlandı",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    return ("\ufeff" + output.getvalue()).encode("utf-8")

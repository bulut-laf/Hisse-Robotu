from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Iterable, Mapping

from ..models.fundamental_models import FinancialPeriod


REQUIRED_COLUMNS = (
    "symbol",
    "period_end",
    "fiscal_year",
    "fiscal_quarter",
    "currency",
    "revenue",
    "gross_profit",
    "operating_profit",
    "ebitda",
    "net_income",
    "total_assets",
    "total_equity",
    "total_debt",
    "cash_and_equivalents",
    "current_assets",
    "current_liabilities",
    "operating_cash_flow",
    "capital_expenditure",
    "shares_outstanding",
)

CURRENT = "Güncel"
STALE = "Eski bilanço"
MISSING = "Veri yok"
FUTURE = "Gelecek tarihli bilanço"


class FundamentalDataError(ValueError):
    """Bilanço verisi okuma veya doğrulama hatası."""


@dataclass(frozen=True)
class FundamentalFreshnessPolicy:
    maximum_age_days: int = 190
    future_tolerance_days: int = 2

    def __post_init__(self) -> None:
        if self.maximum_age_days < 1:
            raise ValueError(
                "Azami bilanço yaşı en az 1 gün olmalıdır."
            )
        if self.future_tolerance_days < 0:
            raise ValueError(
                "Gelecek tarih toleransı negatif olamaz."
            )


@dataclass(frozen=True)
class FundamentalFreshnessResult:
    status: str
    latest_period_end: date | None
    age_days: int | None
    locked: bool
    explanation: str


def _parse_date(value: object, field_name: str) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value).strip())
    except Exception as exc:
        raise FundamentalDataError(
            f"{field_name} YYYY-MM-DD biçiminde olmalıdır."
        ) from exc


def _period_from_mapping(
    record: Mapping[str, object],
) -> FinancialPeriod:
    missing = [
        key
        for key in REQUIRED_COLUMNS
        if key not in record
    ]
    if missing:
        raise FundamentalDataError(
            "Eksik bilanço alanları: " + ", ".join(missing)
        )

    published_raw = record.get("published_at")
    return FinancialPeriod(
        symbol=str(record["symbol"]),
        period_end=_parse_date(
            record["period_end"],
            "period_end",
        ),
        fiscal_year=int(record["fiscal_year"]),
        fiscal_quarter=int(record["fiscal_quarter"]),
        currency=str(record["currency"]),
        revenue=Decimal(str(record["revenue"])),
        gross_profit=Decimal(str(record["gross_profit"])),
        operating_profit=Decimal(
            str(record["operating_profit"])
        ),
        ebitda=Decimal(str(record["ebitda"])),
        net_income=Decimal(str(record["net_income"])),
        total_assets=Decimal(str(record["total_assets"])),
        total_equity=Decimal(str(record["total_equity"])),
        total_debt=Decimal(str(record["total_debt"])),
        cash_and_equivalents=Decimal(
            str(record["cash_and_equivalents"])
        ),
        current_assets=Decimal(
            str(record["current_assets"])
        ),
        current_liabilities=Decimal(
            str(record["current_liabilities"])
        ),
        operating_cash_flow=Decimal(
            str(record["operating_cash_flow"])
        ),
        capital_expenditure=Decimal(
            str(record["capital_expenditure"])
        ),
        shares_outstanding=Decimal(
            str(record["shares_outstanding"])
        ),
        source=str(record.get("source", "manual")),
        published_at=(
            _parse_date(published_raw, "published_at")
            if published_raw not in (None, "")
            else None
        ),
    )


def periods_from_records(
    records: Iterable[Mapping[str, object]],
) -> list[FinancialPeriod]:
    periods = [_period_from_mapping(record) for record in records]
    seen: set[tuple[str, int, int]] = set()
    for period in periods:
        key = (
            period.symbol,
            period.fiscal_year,
            period.fiscal_quarter,
        )
        if key in seen:
            raise FundamentalDataError(
                f"Tekrarlanan finansal dönem: "
                f"{period.symbol} {period.period_key}"
            )
        seen.add(key)
    return periods


def periods_from_csv_bytes(
    payload: bytes,
) -> list[FinancialPeriod]:
    try:
        text = payload.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise FundamentalDataError(
            "Bilanço CSV dosyası UTF-8 olmalıdır."
        ) from exc
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise FundamentalDataError(
            "Bilanço CSV başlığı bulunamadı."
        )
    return periods_from_records(reader)


def periods_from_json_bytes(
    payload: bytes,
) -> list[FinancialPeriod]:
    try:
        raw = json.loads(payload.decode("utf-8"))
    except Exception as exc:
        raise FundamentalDataError(
            "Bilanço JSON dosyası okunamadı."
        ) from exc
    if not isinstance(raw, list):
        raise FundamentalDataError(
            "Bilanço JSON kök değeri liste olmalıdır."
        )
    if not all(isinstance(item, dict) for item in raw):
        raise FundamentalDataError(
            "Bilanço JSON kayıtları nesne olmalıdır."
        )
    return periods_from_records(raw)


def load_fundamental_file(
    path: str | Path,
) -> list[FinancialPeriod]:
    file_path = Path(path)
    if not file_path.exists():
        raise FundamentalDataError(
            f"Bilanço dosyası bulunamadı: {file_path}"
        )
    suffix = file_path.suffix.lower()
    payload = file_path.read_bytes()
    if suffix == ".csv":
        return periods_from_csv_bytes(payload)
    if suffix == ".json":
        return periods_from_json_bytes(payload)
    raise FundamentalDataError(
        "Bilanço dosyası CSV veya JSON olmalıdır."
    )


def evaluate_fundamental_freshness(
    periods: Iterable[FinancialPeriod],
    *,
    today: date | None = None,
    policy: FundamentalFreshnessPolicy = (
        FundamentalFreshnessPolicy()
    ),
) -> FundamentalFreshnessResult:
    items = list(periods)
    reference = today or date.today()

    if not items:
        return FundamentalFreshnessResult(
            status=MISSING,
            latest_period_end=None,
            age_days=None,
            locked=True,
            explanation=(
                "Doğrulanabilir finansal dönem bulunmadı; "
                "temel analiz durduruldu."
            ),
        )

    latest = max(item.period_end for item in items)
    if latest > reference + timedelta(
        days=policy.future_tolerance_days
    ):
        return FundamentalFreshnessResult(
            status=FUTURE,
            latest_period_end=latest,
            age_days=(reference - latest).days,
            locked=True,
            explanation=(
                f"Son bilanço dönemi {latest}; bugün {reference}. "
                "Gelecek tarihli veya hatalı dönem algılandı."
            ),
        )

    age_days = max(0, (reference - latest).days)
    if age_days > policy.maximum_age_days:
        return FundamentalFreshnessResult(
            status=STALE,
            latest_period_end=latest,
            age_days=age_days,
            locked=True,
            explanation=(
                f"Son bilanço dönemi {latest}; veri "
                f"{age_days} günlük. Temel analiz için "
                "güncel finansal tablo gereklidir."
            ),
        )

    return FundamentalFreshnessResult(
        status=CURRENT,
        latest_period_end=latest,
        age_days=age_days,
        locked=False,
        explanation=(
            f"Son bilanço dönemi {latest}; temel analiz "
            "tazelik politikasını geçiyor."
        ),
    )

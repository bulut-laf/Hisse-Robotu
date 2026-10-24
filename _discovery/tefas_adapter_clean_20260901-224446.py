from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Iterable, Mapping

from backend.app.news_center.official_source_http import fetch_official_source_bytes

from .contracts import DataQualityState, FundDailyObservation, FundIdentity
from .normalization import normalize_fund_code, normalize_text, parse_decimal_tr


class TefasProviderError(RuntimeError):
    pass


def canonical_tefas_fund_id(provider_fund_id: object) -> str:
    return f"fund:tefas:{normalize_fund_code(provider_fund_id)}"


def fetch_tefas_bytes(url: str, timeout_seconds: int = 10) -> bytes:
    response = fetch_official_source_bytes(
        url, timeout_seconds, user_agent="Hisse-Robotu/Fund-Research-V1",
        error_type=TefasProviderError, source_label="TEFAS",
    )
    return response.body


def map_tefas_rows(
    rows: Iterable[Mapping[str, object]], *, requested_at: datetime,
    fetched_at: datetime, source_as_of: datetime,
) -> tuple[FundIdentity | FundDailyObservation, ...]:
    """Doğrulanmış adapter sınırı. Canlı payload alanları doğrulanana dek fixture mapping."""
    result: list[FundIdentity | FundDailyObservation] = []
    seen: set[tuple[str, date]] = set()
    for row in sorted(rows, key=lambda x: normalize_fund_code(x.get("fund_code"))):
        code = normalize_fund_code(row.get("fund_code"))
        observed = date.fromisoformat(str(row["observation_date"]))
        key = (code, observed)
        if key in seen:
            raise TefasProviderError(f"DUPLICATE_FUND_OBSERVATION:{code}:{observed}")
        seen.add(key)
        canonical_id = canonical_tefas_fund_id(row.get("provider_fund_id", code))
        category_id = normalize_text(row.get("category_id")) or None
        category_name = normalize_text(row.get("category_name")) or None
        quality = DataQualityState.PARTIAL if any(
            row.get(name) in (None, "") for name in ("unit_price", "fund_size", "investor_count")
        ) else DataQualityState.VALID
        result.append(FundIdentity(
            fund_code=code, fund_name=normalize_text(row.get("fund_name")),
            canonical_fund_id=canonical_id, category_id=category_id,
            category_name=category_name, provider="TEFAS",
            provider_fund_id=normalize_fund_code(row.get("provider_fund_id", code)),
            currency=normalize_fund_code(row.get("currency", "TRY")),
            is_active=bool(row.get("is_active", True)), as_of_date=observed,
        ))
        investor_raw = parse_decimal_tr(row.get("investor_count"))
        result.append(FundDailyObservation(
            canonical_fund_id=canonical_id, observation_date=observed,
            unit_price=parse_decimal_tr(row.get("unit_price")),
            fund_size=parse_decimal_tr(row.get("fund_size")),
            investor_count=int(investor_raw) if investor_raw is not None else None,
            shares_outstanding=parse_decimal_tr(row.get("shares_outstanding")),
            daily_return=parse_decimal_tr(row.get("daily_return"), percent=True),
            provider="TEFAS", fetched_at=fetched_at, source_as_of=source_as_of,
            data_quality_state=quality,
        ))
    return tuple(result)

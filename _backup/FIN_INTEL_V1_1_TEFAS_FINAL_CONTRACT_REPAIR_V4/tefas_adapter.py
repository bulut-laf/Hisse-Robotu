from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from typing import Iterable, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from backend.app.news_center.official_source_http import (
    OFFICIAL_SOURCE_MAX_RESPONSE_BYTES,
    fetch_official_source_bytes,
    validate_official_source_timeout,
)

from .contracts import DataQualityState, FundDailyObservation, FundIdentity
from .normalization import normalize_fund_code, normalize_text, parse_decimal_tr


class TefasProviderError(RuntimeError):
    pass


TEFAS_API_BASE = "https://www.tefas.gov.tr/api/funds"

TEFAS_ALLOWED_ENDPOINTS = frozenset(
    {
        "fonGetiriBazliBilgiGetir",
        "fonBilgiGetir",
        "fonFiyatBilgiGetir",
    }
)


def _tefas_api_url(endpoint: str) -> str:
    if endpoint not in TEFAS_ALLOWED_ENDPOINTS:
        raise TefasProviderError(
            f"TEFAS_ENDPOINT_NOT_ALLOWED:{endpoint}"
        )
    return f"{TEFAS_API_BASE}/{endpoint}"


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

def _post_tefas_json(
    endpoint: str,
    payload: Mapping[str, object],
    *,
    timeout_seconds: int = 10,
) -> Mapping[str, object]:
    validate_official_source_timeout(timeout_seconds)
    url = _tefas_api_url(endpoint)

    try:
        request_body = json.dumps(
            dict(payload),
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise TefasProviderError(
            "TEFAS_REQUEST_JSON_INVALID"
        ) from exc

    request = Request(
        url,
        data=request_body,
        headers={
            "User-Agent": "Hisse-Robotu/Fund-Research-V1",
            "Accept": "application/json",
            "Content-Type": "application/json; charset=utf-8",
            "Origin": "https://www.tefas.gov.tr",
            "Referer": "https://www.tefas.gov.tr/tr/fon-verileri",
        },
        method="POST",
    )

    try:
        with urlopen(
            request,
            timeout=timeout_seconds,
        ) as response:
            final_url = response.geturl()
            body = response.read(
                OFFICIAL_SOURCE_MAX_RESPONSE_BYTES + 1
            )
    except HTTPError as exc:
        raise TefasProviderError(
            f"TEFAS HTTP hatası: {exc.code}"
        ) from exc
    except URLError as exc:
        raise TefasProviderError(
            f"TEFAS bağlantı hatası: {exc.reason}"
        ) from exc
    except TimeoutError as exc:
        raise TefasProviderError(
            "TEFAS bağlantısı zaman aşımına uğradı."
        ) from exc

    parsed_url = urlparse(final_url)

    if (
        parsed_url.scheme != "https"
        or parsed_url.hostname != "www.tefas.gov.tr"
        or not parsed_url.path.startswith("/api/funds/")
    ):
        raise TefasProviderError(
            f"TEFAS_UNEXPECTED_REDIRECT:{final_url}"
        )

    if len(body) > OFFICIAL_SOURCE_MAX_RESPONSE_BYTES:
        raise TefasProviderError(
            "TEFAS yanıtı güvenlik boyutu sınırını aşıyor."
        )

    try:
        result = json.loads(body.decode("utf-8"))
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as exc:
        raise TefasProviderError(
            "TEFAS_RESPONSE_JSON_INVALID"
        ) from exc

    if not isinstance(result, dict):
        raise TefasProviderError(
            "TEFAS_RESPONSE_ROOT_NOT_OBJECT"
        )

    error_code = result.get("errorCode")

    if error_code not in (None, "", 0, "0"):
        raise TefasProviderError(
            f"TEFAS_API_ERROR:{error_code}:"
            f"{result.get('errorMessage')}"
        )

    if not isinstance(result.get("resultList"), list):
        raise TefasProviderError(
            "TEFAS_RESULT_LIST_MISSING"
        )

    return result


def fetch_tefas_result_list(
    endpoint: str,
    payload: Mapping[str, object],
    *,
    timeout_seconds: int = 10,
) -> tuple[Mapping[str, object], ...]:
    response = _post_tefas_json(
        endpoint,
        payload,
        timeout_seconds=timeout_seconds,
    )

    rows: list[Mapping[str, object]] = []

    for row in response["resultList"]:
        if not isinstance(row, dict):
            raise TefasProviderError(
                "TEFAS_RESULT_ROW_NOT_OBJECT"
            )
        rows.append(row)

    return tuple(rows)


def fetch_tefas_universe_rows(
    *,
    timeout_seconds: int = 10,
) -> tuple[Mapping[str, object], ...]:
    return fetch_tefas_result_list(
        "fonGetiriBazliBilgiGetir",
        {
            "fonTipi": "YAT",
            "dil": "TR",
            "calismaTipi": 2,
            "donemGetiri1a": "1",
            "donemGetiri3a": "1",
            "donemGetiri6a": "1",
            "donemGetiriyb": "1",
            "donemGetiri1y": "1",
            "donemGetiri3y": "1",
            "donemGetiri5y": "1",
        },
        timeout_seconds=timeout_seconds,
    )


def fetch_tefas_fund_detail_rows(
    fund_code: object,
    *,
    timeout_seconds: int = 10,
) -> tuple[Mapping[str, object], ...]:
    code = normalize_fund_code(fund_code)
    if not code:
        raise ValueError("fund_code boş olamaz.")

    validate_official_source_timeout(timeout_seconds)

    from urllib.request import Request, urlopen

    request_body = json.dumps(
        {"fonKodu": code, "dil": "TR"},
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")

    request = Request(
        "https://www.tefas.gov.tr/api/funds/fonBilgiGetir",
        data=request_body,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/plain, */*",
            "Origin": "https://www.tefas.gov.tr",
            "Referer": f"https://www.tefas.gov.tr/tr/fon-detayli-analiz/{code}",
            "User-Agent": "Mozilla/5.0",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8-sig"))
    except Exception as exc:
        raise TefasProviderError(
            f"TEFAS_FUND_DETAIL_FAILED:{exc.__class__.__name__}:{exc}"
        ) from exc

    rows = payload.get("resultList")
    if not isinstance(rows, list):
        raise TefasProviderError("TEFAS_FUND_DETAIL_RESULT_LIST_INVALID")

    return tuple(
        row
        for row in rows
        if isinstance(row, Mapping)
        and normalize_fund_code(row.get("fonKodu")) == code
    )



def fetch_tefas_fund_history_rows(
    fund_code: object,
    *,
    period: int = 12,
    timeout_seconds: int = 10,
) -> tuple[Mapping[str, object], ...]:
    code = normalize_fund_code(fund_code)
    if not code:
        raise ValueError("fund_code boЕџ olamaz.")
    if period <= 0:
        raise ValueError("period pozitif olmalД±dД±r.")

    validate_official_source_timeout(timeout_seconds)

    from urllib.request import Request, urlopen

    request_body = json.dumps(
        {"fonKodu": code, "dil": "TR", "periyod": int(period)},
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")

    request = Request(
        "https://www.tefas.gov.tr/api/funds/fonFiyatBilgiGetir",
        data=request_body,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/plain, */*",
            "Origin": "https://www.tefas.gov.tr",
            "Referer": f"https://www.tefas.gov.tr/tr/fon-detayli-analiz/{code}",
            "User-Agent": "Mozilla/5.0",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            response_payload = json.loads(response.read().decode("utf-8-sig"))
    except Exception as exc:
        raise TefasProviderError(
            f"TEFAS_FUND_HISTORY_FAILED:{exc.__class__.__name__}:{exc}"
        ) from exc

    rows = response_payload.get("resultList")
    if not isinstance(rows, list):
        raise TefasProviderError("TEFAS_FUND_HISTORY_RESULT_LIST_INVALID")

    return tuple(
        row
        for row in rows
        if isinstance(row, Mapping)
        and normalize_fund_code(row.get("fonKodu")) == code
    )



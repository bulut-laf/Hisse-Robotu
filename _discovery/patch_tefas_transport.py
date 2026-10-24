from pathlib import Path

p = Path(r".\backend\app\funds\tefas_adapter.py")
s = p.read_text(encoding="utf-8")

if "_post_tefas_json" in s:
    raise SystemExit("ALREADY_PATCHED")

s = s.replace(
    "from __future__ import annotations\n\n",
    "from __future__ import annotations\n\nimport json\n"
)

s = s.replace(
    "from urllib",
    "from urllib"
) if "from urllib" in s else s

s = s.replace(
    "from typing import Iterable, Mapping\n",
    "from typing import Iterable, Mapping\n"
    "from urllib.error import HTTPError, URLError\n"
    "from urllib.parse import urlparse\n"
    "from urllib.request import Request, urlopen\n"
)

s = s.replace(
    "from backend.app.news_center.official_source_http import fetch_official_source_bytes\n",
    "from backend.app.news_center.official_source_http import (\n"
    "    OFFICIAL_SOURCE_MAX_RESPONSE_BYTES,\n"
    "    fetch_official_source_bytes,\n"
    "    validate_official_source_timeout,\n"
    ")\n"
)

addition = r'''

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
        raise TefasProviderError("TEFAS_REQUEST_JSON_INVALID") from exc

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
        with urlopen(request, timeout=timeout_seconds) as response:
            final_url = response.geturl()
            body = response.read(OFFICIAL_SOURCE_MAX_RESPONSE_BYTES + 1)
    except HTTPError as exc:
        raise TefasProviderError(f"TEFAS HTTP hatası: {exc.code}") from exc
    except URLError as exc:
        raise TefasProviderError(
            f"TEFAS bağlantı hatası: {exc.reason}"
        ) from exc
    except TimeoutError as exc:
        raise TefasProviderError(
            "TEFAS bağlantısı zaman aşımına uğradı."
        ) from exc

    parsed_url = urlparse(final_url)
    if parsed_url.scheme != "https" or parsed_url.hostname != "www.tefas.gov.tr":
        raise TefasProviderError(
            f"TEFAS_UNEXPECTED_REDIRECT:{final_url}"
        )

    if len(body) > OFFICIAL_SOURCE_MAX_RESPONSE_BYTES:
        raise TefasProviderError(
            "TEFAS yanıtı güvenlik boyutu sınırını aşıyor."
        )

    try:
        result = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TefasProviderError("TEFAS_RESPONSE_JSON_INVALID") from exc

    if not isinstance(result, dict):
        raise TefasProviderError("TEFAS_RESPONSE_ROOT_NOT_OBJECT")

    error_code = result.get("errorCode")
    if error_code not in (None, "", 0, "0"):
        raise TefasProviderError(
            f"TEFAS_API_ERROR:{error_code}:{result.get('errorMessage')}"
        )

    if not isinstance(result.get("resultList"), list):
        raise TefasProviderError("TEFAS_RESULT_LIST_MISSING")

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
            raise TefasProviderError("TEFAS_RESULT_ROW_NOT_OBJECT")
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

    return fetch_tefas_result_list(
        "fonBilgiGetir",
        {"fonKodu": code},
        timeout_seconds=timeout_seconds,
    )


def fetch_tefas_fund_history_rows(
    fund_code: object,
    *,
    period: int = 1,
    timeout_seconds: int = 10,
) -> tuple[Mapping[str, object], ...]:
    code = normalize_fund_code(fund_code)
    if not code:
        raise ValueError("fund_code boş olamaz.")

    if period != 1:
        raise ValueError(
            "Yalnız canlı sözleşmede doğrulanan period=1 desteklenir."
        )

    return fetch_tefas_result_list(
        "fonFiyatBilgiGetir",
        {
            "fonKodu": code,
            "dil": "TR",
            "periyod": 1,
        },
        timeout_seconds=timeout_seconds,
    )
'''

p.write_text(s.rstrip() + addition + "\n", encoding="utf-8")
print("PATCH_OK")

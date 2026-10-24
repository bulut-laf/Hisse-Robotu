from __future__ import annotations

from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


OFFICIAL_SOURCE_MAX_RESPONSE_BYTES = 2_000_000
OFFICIAL_SOURCE_DEFAULT_TIMEOUT_SECONDS = 10
OFFICIAL_SOURCE_MIN_TIMEOUT_SECONDS = 1
OFFICIAL_SOURCE_MAX_TIMEOUT_SECONDS = 30


@dataclass(frozen=True, slots=True)
class OfficialSourceHttpResponse:
    body: bytes
    final_url: str
    content_type: str


def validate_official_source_timeout(timeout_seconds: int) -> int:
    if (
        not isinstance(timeout_seconds, int)
        or not OFFICIAL_SOURCE_MIN_TIMEOUT_SECONDS
        <= timeout_seconds
        <= OFFICIAL_SOURCE_MAX_TIMEOUT_SECONDS
    ):
        raise ValueError("timeout_seconds 1-30 aralığında tam sayı olmalıdır.")
    return timeout_seconds


def fetch_official_source_bytes(
    url: str,
    timeout_seconds: int,
    *,
    user_agent: str,
    error_type: type[RuntimeError],
    source_label: str,
    max_response_bytes: int = OFFICIAL_SOURCE_MAX_RESPONSE_BYTES,
) -> OfficialSourceHttpResponse:
    validate_official_source_timeout(timeout_seconds)
    request = Request(
        url,
        headers={"User-Agent": user_agent},
        method="GET",
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            final_url = response.geturl()
            content_type = response.headers.get("Content-Type", "")
            body = response.read(max_response_bytes + 1)
    except HTTPError as exc:
        raise error_type(f"{source_label} HTTP hatası: {exc.code}") from exc
    except URLError as exc:
        raise error_type(
            f"{source_label} bağlantı hatası: {exc.reason}"
        ) from exc
    except TimeoutError as exc:
        raise error_type(
            f"{source_label} bağlantısı zaman aşımına uğradı."
        ) from exc

    if len(body) > max_response_bytes:
        raise error_type(
            f"{source_label} yanıtı güvenlik boyutu sınırını aşıyor."
        )

    return OfficialSourceHttpResponse(
        body=body,
        final_url=final_url,
        content_type=content_type,
    )


def validate_official_source_html_payload(
    body: bytes,
    content_type: str,
    *,
    error_type: type[RuntimeError],
    source_label: str,
    max_response_bytes: int = OFFICIAL_SOURCE_MAX_RESPONSE_BYTES,
) -> None:
    if "text/html" not in str(content_type or "").lower():
        raise error_type(f"{source_label} yanıtı HTML değil.")
    if len(body) > max_response_bytes:
        raise error_type(
            f"{source_label} yanıtı güvenlik boyutu sınırını aşıyor."
        )


def decode_official_source_html(
    body: bytes,
    *,
    error_type: type[RuntimeError],
    source_label: str,
) -> str:
    try:
        return body.decode("utf-8")
    except UnicodeDecodeError:
        try:
            return body.decode("iso-8859-9")
        except UnicodeDecodeError as exc:
            raise error_type(
                f"{source_label} HTML karakter kodlaması çözülemedi."
            ) from exc

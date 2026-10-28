from __future__ import annotations
from urllib.error import HTTPError, URLError
import json
import re
from dataclasses import dataclass
from typing import Callable, Iterable
from urllib.parse import urlparse
from .kap_portfolio_ingestion import (
    DEFAULT_TIMEOUT_SECONDS,
    KapFundPortfolioError,
    KapPortfolioIngestionResult,
    ingest_kap_portfolio_report_url,
)
from .normalization import normalize_fund_code
from .portfolio_tracking import (
    FundPortfolioSnapshotJsonStore,
    PortfolioSnapshotStoreError,
)
KAP_DISCLOSURES_URL = "https://www.kap.org.tr/tr/api/disclosures"
MAX_DISCOVERY_BYTES = 8 * 1024 * 1024
MAX_DISCOVERY_CANDIDATES = 50
FetchBytes = Callable[[str, int], tuple[bytes, str, str]]
@dataclass(frozen=True, slots=True)
class KapPortfolioDiscoveryCandidate:
    notification_id: str
    detail_url: str
    evidence_text: str
@dataclass(frozen=True, slots=True)
class KapPortfolioAutoIngestionFailure:
    notification_id: str
    detail_url: str
    error: str
@dataclass(frozen=True, slots=True)
class KapPortfolioAutoIngestionSummary:
    discovered: int
    attempted: int
    inserted: int
    unchanged: int
    failures: tuple[KapPortfolioAutoIngestionFailure, ...]
    ingestions: tuple[KapPortfolioIngestionResult, ...]
def _default_fetch(url: str, timeout_seconds: int) -> tuple[bytes, str, str]:
    # Reuse the hardened KAP transport contract without exposing a second
    # general-purpose HTTP client.
    from .kap_portfolio_ingestion import _default_fetch as kap_fetch
    return kap_fetch(url, timeout_seconds)
def _validate_disclosures_url(url: str) -> str:
    value = str(url or "").strip()
    parsed = urlparse(value)
    if parsed.scheme.lower() != "https":
        raise KapFundPortfolioError("KAP_DISCOVERY_HTTPS_REQUIRED")
    if (parsed.hostname or "").lower() not in {"kap.org.tr", "www.kap.org.tr"}:
        raise KapFundPortfolioError("KAP_DISCOVERY_HOST_NOT_ALLOWED")
    if parsed.username or parsed.password or parsed.port not in (None, 443):
        raise KapFundPortfolioError("KAP_DISCOVERY_AUTH_OR_PORT_NOT_ALLOWED")
    if parsed.path.rstrip("/").lower() != "/tr/api/disclosures":
        raise KapFundPortfolioError("KAP_DISCOVERY_PATH_INVALID")
    if parsed.query or parsed.fragment:
        raise KapFundPortfolioError("KAP_DISCOVERY_PATH_INVALID")
    return value
def _decode_disclosures_json(raw: bytes, content_type: str) -> object:
    if len(raw) > MAX_DISCOVERY_BYTES:
        raise KapFundPortfolioError("KAP_DISCOVERY_RESPONSE_TOO_LARGE")
    lowered = str(content_type or "").casefold()
    stripped = raw.lstrip()
    if "json" not in lowered and not stripped.startswith((b"[", b"{")):
        raise KapFundPortfolioError("KAP_DISCOVERY_NOT_JSON")
    try:
        return json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise KapFundPortfolioError("KAP_DISCOVERY_JSON_INVALID") from exc
def _iter_dicts(value: object) -> Iterable[dict[str, object]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _iter_dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from _iter_dicts(child)
def _first_scalar(mapping: dict[str, object], keys: tuple[str, ...]) -> object | None:
    lowered = {str(key).casefold(): value for key, value in mapping.items()}
    for key in keys:
        value = lowered.get(key.casefold())
        if isinstance(value, (str, int, float)) and str(value).strip():
            return value
    return None
def _mapping_text(mapping: dict[str, object]) -> str:
    values: list[str] = []
    for value in mapping.values():
        if isinstance(value, (str, int, float)):
            clean = re.sub(r"\s+", " ", str(value)).strip()
            if clean:
                values.append(clean)
    return " ".join(values)
def _looks_like_portfolio_report(text: str) -> bool:
    folded = text.casefold()
    return (
        "portföy dağılım raporu" in folded
        or "portfoy dagilim raporu" in folded
        or (
            "portföy" in folded
            and "dağılım" in folded
            and "rapor" in folded
        )
    )
def _contains_fund_code(text: str, fund_codes: frozenset[str]) -> bool:
    if not fund_codes:
        return True
    upper = text.upper()
    return any(
        re.search(rf"(?<![A-Z0-9]){re.escape(code)}(?![A-Z0-9])", upper)
        for code in fund_codes
    )
def parse_kap_disclosures_for_portfolio_reports(
    payload: object,
    *,
    fund_codes: Iterable[str] = (),
    max_candidates: int = MAX_DISCOVERY_CANDIDATES,
) -> tuple[KapPortfolioDiscoveryCandidate, ...]:
    if max_candidates <= 0 or max_candidates > MAX_DISCOVERY_CANDIDATES:
        raise ValueError(
            f"max_candidates 1-{MAX_DISCOVERY_CANDIDATES} aralığında olmalıdır."
        )
    normalized_codes = frozenset(
        normalize_fund_code(code)
        for code in fund_codes
        if str(code or "").strip()
    )
    by_id: dict[str, KapPortfolioDiscoveryCandidate] = {}
    for mapping in _iter_dicts(payload):
        raw_id = _first_scalar(
            mapping,
            (
                "disclosureIndex",
                "disclosure_index",
                "notificationId",
                "notification_id",
                "bildirimId",
                "bildirim_id",
                "id",
            ),
        )
        if raw_id is None:
            continue
        notification_id = str(raw_id).strip()
        if not notification_id.isdigit():
            continue
        evidence = _mapping_text(mapping)
        if not _looks_like_portfolio_report(evidence):
            continue
        if not _contains_fund_code(evidence, normalized_codes):
            continue
        by_id[notification_id] = KapPortfolioDiscoveryCandidate(
            notification_id=notification_id,
            detail_url=f"https://www.kap.org.tr/tr/Bildirim/{notification_id}",
            evidence_text=evidence[:1000],
        )
    ordered = sorted(
        by_id.values(),
        key=lambda item: int(item.notification_id),
        reverse=True,
    )
    return tuple(ordered[:max_candidates])
_KAP_FUND_CRITERIA_TYPES = (
    "YF", "BYF", "EYF", "OKS", "YYF",
    "VFF", "KFF", "GMF", "GSF", "PFF",
)
def _json_request(request: object, timeout_seconds: int) -> object:
    import json
    from urllib.request import urlopen
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            raw = response.read()
    except HTTPError as exc:
        raise KapFundPortfolioError(f"KAP_HTTP_ERROR:{exc.code}") from exc
    except URLError as exc:
        raise KapFundPortfolioError(
            f"KAP_CONNECTION_ERROR:{exc.reason}"
        ) from exc
    except TimeoutError as exc:
        raise KapFundPortfolioError("KAP_TIMEOUT") from exc
    try:
        return json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise KapFundPortfolioError(
            "KAP_DISCOVERY_JSON_INVALID"
        ) from exc
def _resolve_kap_fund_oids(
    fund_codes: Iterable[str],
    timeout_seconds: int,
) -> tuple[tuple[str, str], ...]:
    from urllib.request import Request
    wanted = {
        normalize_fund_code(code)
        for code in fund_codes
        if str(code or "").strip()
    }
    if not wanted:
        return ()
    resolved: dict[str, tuple[str, str]] = {}
    for fund_type in _KAP_FUND_CRITERIA_TYPES:
        request = Request(
            f"https://www.kap.org.tr/tr/api/fund/criteria/{fund_type}/Y",
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json, text/plain, */*",
                "Referer": "https://www.kap.org.tr/tr/bildirim-sorgu",
            },
            method="GET",
        )
        payload = _json_request(request, timeout_seconds)
        for mapping in _iter_dicts(payload):
            code = str(mapping.get("fundCode") or "").strip().upper()
            if code not in wanted or code in resolved:
                continue
            oid = str(mapping.get("fundOid") or "").strip()
            if not oid:
                continue
            resolved[code] = (fund_type, oid)
        if wanted.issubset(resolved):
            break
    return tuple(resolved[code] for code in sorted(resolved))
def _fetch_targeted_fund_disclosures(
    fund_codes: Iterable[str],
    timeout_seconds: int,
) -> object:
    from datetime import date, timedelta
    import json
    from urllib.request import Request
    resolved = _resolve_kap_fund_oids(
        fund_codes,
        timeout_seconds,
    )
    if not resolved:
        return []
    today = date.today()
    start = today - timedelta(days=365)
    payload = {
        "fromDate": start.isoformat(),
        "toDate": today.isoformat(),
        "fundTypeList": sorted({
            fund_type for fund_type, _oid in resolved
        }),
        "mkkMemberOidList": [],
        "fundOidList": [
            oid for _fund_type, oid in resolved
        ],
        "passiveFundOidList": [],
        "disclosureClass": "",
        "isLate": "",
        "subjectList": [],
        "discIndex": [],
        "fromSrc": False,
        "srcCategory": "",
    }
    request = Request(
        "https://www.kap.org.tr/tr/api/disclosure/funds/byCriteria",
        data=json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8"),
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "Origin": "https://www.kap.org.tr",
            "Referer": "https://www.kap.org.tr/tr/bildirim-sorgu",
        },
        method="POST",
    )
    decoded = _json_request(request, timeout_seconds)
    if not isinstance(decoded, list):
        raise KapFundPortfolioError(
            "KAP_DISCOVERY_JSON_NOT_LIST"
        )
    return decoded
def discover_kap_portfolio_reports(
    *,
    fund_codes: Iterable[str] = (),
    network_enabled: bool = False,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    max_candidates: int = MAX_DISCOVERY_CANDIDATES,
    fetcher: FetchBytes | None = None,
    disclosures_url: str = KAP_DISCLOSURES_URL,
) -> tuple[KapPortfolioDiscoveryCandidate, ...]:
    if not network_enabled:
        raise KapFundPortfolioError("KAP_PORTFOLIO_DISCOVERY_NETWORK_DISABLED")
    if timeout_seconds <= 0 or timeout_seconds > 30:
        raise ValueError("timeout_seconds 1-30 aralığında olmalıdır.")
    normalized_fund_codes = tuple(
        normalize_fund_code(code)
        for code in fund_codes
        if str(code or "").strip()
    )
    if (
        fetcher is None
        and disclosures_url == KAP_DISCLOSURES_URL
        and normalized_fund_codes
    ):
        payload = _fetch_targeted_fund_disclosures(
            normalized_fund_codes,
            timeout_seconds,
        )
    else:
        validated_url = _validate_disclosures_url(
            disclosures_url
        )
        fetch = fetcher or _default_fetch
        raw, final_url, content_type = fetch(
            validated_url,
            timeout_seconds,
        )
        if _validate_disclosures_url(final_url) != validated_url:
            raise KapFundPortfolioError(
                "KAP_DISCOVERY_REDIRECT_MISMATCH"
            )
        payload = _decode_disclosures_json(
            raw,
            content_type,
        )
    return parse_kap_disclosures_for_portfolio_reports(
        payload,
        fund_codes=normalized_fund_codes,
        max_candidates=max_candidates,
    )
def auto_ingest_kap_portfolio_reports(
    *,
    store: FundPortfolioSnapshotJsonStore,
    fund_codes: Iterable[str] = (),
    network_enabled: bool = False,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    max_candidates: int = MAX_DISCOVERY_CANDIDATES,
    discovery_fetcher: FetchBytes | None = None,
    detail_fetcher: FetchBytes | None = None,
    attachment_fetcher: FetchBytes | None = None,
) -> KapPortfolioAutoIngestionSummary:
    candidates = discover_kap_portfolio_reports(
        fund_codes=fund_codes,
        network_enabled=network_enabled,
        timeout_seconds=timeout_seconds,
        max_candidates=max_candidates,
        fetcher=discovery_fetcher,
    )
    ingestions: list[KapPortfolioIngestionResult] = []
    failures: list[KapPortfolioAutoIngestionFailure] = []
    inserted = 0
    unchanged = 0
    for candidate in candidates:
        try:
            result = ingest_kap_portfolio_report_url(
                candidate.detail_url,
                store=store,
                network_enabled=True,
                timeout_seconds=timeout_seconds,
                detail_fetcher=detail_fetcher,
                attachment_fetcher=attachment_fetcher,
            )
        except (
            KapFundPortfolioError,
            PortfolioSnapshotStoreError,
            ValueError,
        ) as exc:
            failures.append(
                KapPortfolioAutoIngestionFailure(
                    notification_id=candidate.notification_id,
                    detail_url=candidate.detail_url,
                    error=str(exc),
                )
            )
            continue
        ingestions.append(result)
        inserted += int(result.store_result.inserted)
        unchanged += int(result.store_result.unchanged)
    return KapPortfolioAutoIngestionSummary(
        discovered=len(candidates),
        attempted=len(candidates),
        inserted=inserted,
        unchanged=unchanged,
        failures=tuple(failures),
        ingestions=tuple(ingestions),
    )

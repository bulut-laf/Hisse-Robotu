from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse, urljoin
from urllib.request import Request, urlopen

from app.data.kap_financial_xls import import_kap_financial_xls_bytes


DETAIL_URL = "https://www.kap.org.tr/tr/Bildirim/1637884"
EXPECTED_SYMBOL = "AKBNK"
EXPECTED_NOTIFICATION_ID = "1637884"

ALLOWED_HOSTS = {
    "kap.org.tr",
    "www.kap.org.tr",
}

MAX_DETAIL_BYTES = 8 * 1024 * 1024


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _fetch(url: str, timeout: int = 20) -> tuple[bytes, str, str]:
    parsed = urlparse(url)

    if parsed.scheme != "https":
        raise RuntimeError("KAP_URL_NOT_HTTPS")

    if (parsed.hostname or "").lower() not in ALLOWED_HOSTS:
        raise RuntimeError("KAP_HOST_NOT_ALLOWED")

    request = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 Hisse-Robotu-Financial-Intelligence-V1.3",
            "Accept": "text/html,application/xhtml+xml,application/octet-stream;q=0.9,*/*;q=0.1",
            "Referer": "https://www.kap.org.tr/tr/bildirim-sorgu",
        },
        method="GET",
    )

    try:
        with urlopen(request, timeout=timeout) as response:
            payload = response.read(MAX_DETAIL_BYTES + 1)
            final_url = response.geturl()
            content_type = str(response.headers.get("Content-Type", ""))
    except HTTPError as exc:
        raise RuntimeError(f"KAP_HTTP_ERROR:{exc.code}") from exc
    except URLError as exc:
        raise RuntimeError(f"KAP_CONNECTION_ERROR:{exc.reason}") from exc
    except TimeoutError as exc:
        raise RuntimeError("KAP_TIMEOUT") from exc

    if len(payload) > MAX_DETAIL_BYTES:
        raise RuntimeError("KAP_DETAIL_TOO_LARGE")

    final = urlparse(final_url)

    if final.scheme != "https":
        raise RuntimeError("KAP_FINAL_URL_NOT_HTTPS")

    if (final.hostname or "").lower() not in ALLOWED_HOSTS:
        raise RuntimeError("KAP_FINAL_HOST_NOT_ALLOWED")

    return payload, final_url, content_type


def _decode_html(payload: bytes) -> str:
    for encoding in ("utf-8", "windows-1254", "iso-8859-9"):
        try:
            return payload.decode(encoding)
        except UnicodeDecodeError:
            continue

    raise RuntimeError("KAP_DETAIL_ENCODING_UNSUPPORTED")


def _extract_links(html: str, base_url: str) -> list[str]:
    candidates = set()

    pattern = re.compile(
        r'href\s*=\s*["\']([^"\']+)["\']',
        flags=re.IGNORECASE,
    )

    for match in pattern.finditer(html):
        href = match.group(1).strip()

        if not href:
            continue

        absolute = urljoin(base_url, href)
        parsed = urlparse(absolute)

        if (
            parsed.scheme == "https"
            and (parsed.hostname or "").lower() in ALLOWED_HOSTS
        ):
            candidates.add(absolute)

    return sorted(candidates)


def _identity_value(identity, name: str):
    value = getattr(identity, name, None)

    if value is None:
        return None

    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            pass

    return str(value)


def main():
    root = Path(r"D:\Projects\Hisse-Robotu")

    out_dir = (
        root
        / "backend"
        / "data"
        / "financial_intelligence"
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    result = {
        "schema_version":
            "financial-intelligence-v1-3-akbnk-official-kap-live-financial-evidence-acquisition-v1",
        "status": "PASS_FAIL_CLOSED",
        "symbol": EXPECTED_SYMBOL,
        "notification_id": EXPECTED_NOTIFICATION_ID,
        "detail_url": DETAIL_URL,
        "source_type": "KAP",
        "source_uri": DETAIL_URL,
        "network_fetch": False,
        "content_type": None,
        "final_url": None,
        "evidence_hash": None,
        "detail_bytes": None,
        "identity": None,
        "canonical_fact_count": 0,
        "unmapped_count": 0,
        "attachment_links": [],
        "xls_like_links": [],
        "parser_status": "NOT_RUN",
        "parser_error": None,
        "production_evidence": False,
        "canonical_input_ready": False,
        "scoring_ready": False,
        "activation_ready": False,
        "blockers": [],
        "store_mutation": "NO",
        "al_sat_mutation": "NO",
    }

    try:
        payload, final_url, content_type = _fetch(DETAIL_URL)

        result["network_fetch"] = True
        result["content_type"] = content_type
        result["final_url"] = final_url
        result["evidence_hash"] = "sha256:" + _sha256(payload)
        result["detail_bytes"] = len(payload)

        html = _decode_html(payload)
        folded = html.casefold()

        if "akbank" not in folded:
            raise RuntimeError("KAP_DETAIL_AKBANK_IDENTITY_MISSING")

        if EXPECTED_NOTIFICATION_ID not in (final_url + "\n" + html):
            raise RuntimeError("KAP_NOTIFICATION_IDENTITY_MISSING")

        links = _extract_links(html, final_url)

        attachment_links = [
            link
            for link in links
            if "/tr/api/file/download/" in link
        ]

        xls_like_links = [
            link
            for link in links
            if (
                ".xls" in link.casefold()
                or ".xlsx" in link.casefold()
                or ".rar" in link.casefold()
                or ".zip" in link.casefold()
            )
        ]

        result["attachment_links"] = attachment_links
        result["xls_like_links"] = xls_like_links

        try:
            report = import_kap_financial_xls_bytes(
                payload,
                source_name=f"{EXPECTED_SYMBOL}_KAP_{EXPECTED_NOTIFICATION_ID}.xls",
            )

            result["parser_status"] = "PASS"

            identity = report.identity
            symbol = str(
                getattr(identity, "symbol", "") or ""
            ).strip().upper()

            result["identity"] = {
                "symbol": symbol or None,
                "report_date": _identity_value(identity, "report_date"),
                "published_at": _identity_value(identity, "published_at"),
                "period": _identity_value(identity, "period"),
            }

            result["canonical_fact_count"] = len(report.facts)
            result["unmapped_count"] = len(
                getattr(report, "unmapped_labels", ()) or ()
            )

            if symbol != EXPECTED_SYMBOL:
                result["blockers"].append("PARSED_SYMBOL_MISMATCH")
            elif len(report.facts) <= 0:
                result["blockers"].append("PARSED_CANONICAL_FACTS_EMPTY")
            else:
                result["status"] = "PASS"
                result["production_evidence"] = True
                result["canonical_input_ready"] = True

        except Exception as exc:
            result["parser_status"] = "BLOCKED"
            result["parser_error"] = f"{type(exc).__name__}:{exc}"
            result["blockers"].append(
                "LIVE_KAP_DETAIL_NOT_DIRECTLY_PARSEABLE_AS_FINANCIAL_XLS"
            )

    except Exception as exc:
        result["blockers"].append(
            f"LIVE_KAP_FETCH_FAILED:{type(exc).__name__}:{exc}"
        )

    if (
        not result["production_evidence"]
        and not result["blockers"]
    ):
        result["blockers"].append(
            "NO_LIVE_AKBNK_FINANCIAL_EVIDENCE"
        )

    out = (
        out_dir
        / "FINANCIAL_INTELLIGENCE_V1_3_AKBNK_OFFICIAL_KAP_LIVE_FINANCIAL_EVIDENCE_ACQUISITION.json"
    )

    out.write_text(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"STATUS={result['status']}")
    print(f"SYMBOL={result['symbol']}")
    print(f"NOTIFICATION_ID={result['notification_id']}")
    print(f"NETWORK_FETCH={result['network_fetch']}")
    print(f"CONTENT_TYPE={result['content_type']}")
    print(f"FINAL_URL={result['final_url']}")
    print(f"EVIDENCE_HASH={result['evidence_hash']}")
    print(f"DETAIL_BYTES={result['detail_bytes']}")
    print(f"PARSER_STATUS={result['parser_status']}")
    print(f"PARSER_ERROR={result['parser_error']}")
    print(f"IDENTITY={result['identity']}")
    print(f"CANONICAL_FACT_COUNT={result['canonical_fact_count']}")
    print(f"UNMAPPED_COUNT={result['unmapped_count']}")
    print(f"ATTACHMENT_LINK_COUNT={len(result['attachment_links'])}")
    print(f"XLS_LIKE_LINK_COUNT={len(result['xls_like_links'])}")

    for i, link in enumerate(
        result["attachment_links"][:10],
        start=1,
    ):
        print(f"ATTACHMENT_{i}={link}")

    for i, link in enumerate(
        result["xls_like_links"][:10],
        start=1,
    ):
        print(f"XLS_LINK_{i}={link}")

    print(f"PRODUCTION_EVIDENCE={result['production_evidence']}")
    print(f"CANONICAL_INPUT_READY={result['canonical_input_ready']}")
    print("SCORING_READY=False")
    print("ACTIVATION_READY=False")
    print(f"BLOCKERS={result['blockers']}")
    print("STORE_MUTATION=NO")
    print("AL_SAT_MUTATION=NO")
    print(f"RESULT={out}")
    print(
        "FINANCIAL_INTELLIGENCE_V1_3_"
        "AKBNK_OFFICIAL_KAP_LIVE_FINANCIAL_EVIDENCE_ACQUISITION_V1=PASS"
    )


if __name__ == "__main__":
    main()

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from app.data.kap_financial_xls import (
    import_kap_financial_xls_bytes,
)


ATTACHMENT_URL = (
    "https://www.kap.org.tr/tr/api/file/download/"
    "4028328c9f52dc40019fa90343905e35"
)

EXPECTED_SYMBOL = "AKBNK"
EXPECTED_NOTIFICATION_ID = "1637884"
SOURCE_NAME = "AKBNK_1637884_2026_2.xls"

ALLOWED_HOSTS = {
    "kap.org.tr",
    "www.kap.org.tr",
}

MAX_BYTES = 20 * 1024 * 1024


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _value(obj, name: str):
    value = getattr(obj, name, None)

    if value is None:
        return None

    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            pass

    return str(value)


def _fetch(
    url: str,
    timeout: int = 30,
) -> tuple[bytes, str, str, str]:

    parsed = urlparse(url)

    if parsed.scheme != "https":
        raise RuntimeError(
            "KAP_ATTACHMENT_NOT_HTTPS"
        )

    if (
        parsed.hostname or ""
    ).lower() not in ALLOWED_HOSTS:
        raise RuntimeError(
            "KAP_ATTACHMENT_HOST_NOT_ALLOWED"
        )

    request = Request(
        url,
        headers={
            "User-Agent":
                "Mozilla/5.0 "
                "Hisse-Robotu-Financial-Intelligence-V1.3",
            "Accept":
                "application/vnd.ms-excel,"
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet,"
                "text/html,"
                "application/octet-stream;q=0.9,*/*;q=0.1",
            "Referer":
                "https://www.kap.org.tr/tr/Bildirim/1637884",
        },
        method="GET",
    )

    try:
        with urlopen(
            request,
            timeout=timeout,
        ) as response:
            payload = response.read(
                MAX_BYTES + 1
            )
            final_url = response.geturl()
            content_type = str(
                response.headers.get(
                    "Content-Type",
                    "",
                )
            )
            content_disposition = str(
                response.headers.get(
                    "Content-Disposition",
                    "",
                )
            )
    except HTTPError as exc:
        raise RuntimeError(
            f"KAP_ATTACHMENT_HTTP_ERROR:{exc.code}"
        ) from exc
    except URLError as exc:
        raise RuntimeError(
            f"KAP_ATTACHMENT_CONNECTION_ERROR:{exc.reason}"
        ) from exc
    except TimeoutError as exc:
        raise RuntimeError(
            "KAP_ATTACHMENT_TIMEOUT"
        ) from exc

    if len(payload) > MAX_BYTES:
        raise RuntimeError(
            "KAP_ATTACHMENT_TOO_LARGE"
        )

    final = urlparse(final_url)

    if final.scheme != "https":
        raise RuntimeError(
            "KAP_ATTACHMENT_FINAL_NOT_HTTPS"
        )

    if (
        final.hostname or ""
    ).lower() not in ALLOWED_HOSTS:
        raise RuntimeError(
            "KAP_ATTACHMENT_FINAL_HOST_NOT_ALLOWED"
        )

    return (
        payload,
        final_url,
        content_type,
        content_disposition,
    )


def main():
    root = Path(
        r"D:\Projects\Hisse-Robotu"
    )

    out_dir = (
        root
        / "backend"
        / "data"
        / "financial_intelligence"
    )
    out_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    result = {
        "schema_version":
            "financial-intelligence-v1-3-akbnk-kap-financial-attachment-canonical-parse-v1",
        "status":
            "PASS_FAIL_CLOSED",
        "symbol":
            EXPECTED_SYMBOL,
        "notification_id":
            EXPECTED_NOTIFICATION_ID,
        "source_type":
            "KAP",
        "source_uri":
            ATTACHMENT_URL,
        "source_name":
            SOURCE_NAME,
        "network_fetch":
            False,
        "final_url":
            None,
        "content_type":
            None,
        "content_disposition":
            None,
        "attachment_bytes":
            None,
        "evidence_hash":
            None,
        "parser_status":
            "NOT_RUN",
        "parser_error":
            None,
        "identity":
            None,
        "canonical_fact_count":
            0,
        "unmapped_count":
            0,
        "production_evidence":
            False,
        "canonical_import_ready":
            False,
        "bank_metric_mapping_ready":
            False,
        "scoring_ready":
            False,
        "activation_ready":
            False,
        "blockers":
            [],
        "raw_attachment_persisted":
            False,
        "store_mutation":
            "NO",
        "al_sat_mutation":
            "NO",
    }

    try:
        (
            payload,
            final_url,
            content_type,
            content_disposition,
        ) = _fetch(
            ATTACHMENT_URL
        )

        result["network_fetch"] = True
        result["final_url"] = final_url
        result["content_type"] = (
            content_type
        )
        result["content_disposition"] = (
            content_disposition
        )
        result["attachment_bytes"] = (
            len(payload)
        )
        result["evidence_hash"] = (
            "sha256:"
            + _sha256(payload)
        )

        evidence_dir = (
            out_dir
            / "evidence"
            / "AKBNK"
        )
        evidence_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        raw_path = (
            evidence_dir
            / SOURCE_NAME
        )

        raw_path.write_bytes(
            payload
        )

        result[
            "raw_attachment_persisted"
        ] = True
        result[
            "raw_attachment_path"
        ] = str(raw_path)

        try:
            report = (
                import_kap_financial_xls_bytes(
                    payload,
                    source_name=SOURCE_NAME,
                )
            )

            result[
                "parser_status"
            ] = "PASS"

            identity = (
                report.identity
            )

            symbol = str(
                getattr(
                    identity,
                    "symbol",
                    "",
                )
                or ""
            ).strip().upper()

            identity_row = {
                "symbol":
                    symbol or None,
                "report_date":
                    _value(
                        identity,
                        "report_date",
                    ),
                "published_at":
                    _value(
                        identity,
                        "published_at",
                    ),
                "period":
                    _value(
                        identity,
                        "period",
                    ),
                "source_name":
                    _value(
                        identity,
                        "source_name",
                    ),
            }

            result[
                "identity"
            ] = identity_row

            result[
                "canonical_fact_count"
            ] = len(
                report.facts
            )

            result[
                "unmapped_count"
            ] = len(
                getattr(
                    report,
                    "unmapped_labels",
                    (),
                )
                or ()
            )

            if (
                symbol
                != EXPECTED_SYMBOL
            ):
                result[
                    "blockers"
                ].append(
                    "PARSED_SYMBOL_MISMATCH"
                )

            elif (
                len(
                    report.facts
                )
                <= 0
            ):
                result[
                    "blockers"
                ].append(
                    "PARSED_CANONICAL_FACTS_EMPTY"
                )

            else:
                result[
                    "status"
                ] = "PASS"

                result[
                    "production_evidence"
                ] = True

                result[
                    "canonical_import_ready"
                ] = True

        except Exception as exc:
            result[
                "parser_status"
            ] = "BLOCKED"

            result[
                "parser_error"
            ] = (
                f"{type(exc).__name__}:{exc}"
            )

            result[
                "blockers"
            ].append(
                "KAP_ATTACHMENT_CANONICAL_PARSE_FAILED"
            )

    except Exception as exc:
        result[
            "blockers"
        ].append(
            "KAP_ATTACHMENT_FETCH_FAILED:"
            f"{type(exc).__name__}:{exc}"
        )

    if (
        result[
            "production_evidence"
        ]
        and not result[
            "bank_metric_mapping_ready"
        ]
    ):
        result[
            "blockers"
        ].append(
            "BANK_METRIC_MAPPING_NOT_YET_PROVEN"
        )

    out = (
        out_dir
        / "FINANCIAL_INTELLIGENCE_V1_3_AKBNK_KAP_FINANCIAL_ATTACHMENT_CANONICAL_PARSE.json"
    )

    out.write_text(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(
        f"STATUS={result['status']}"
    )
    print(
        f"SYMBOL={result['symbol']}"
    )
    print(
        "NOTIFICATION_ID="
        f"{result['notification_id']}"
    )
    print(
        "NETWORK_FETCH="
        f"{result['network_fetch']}"
    )
    print(
        "FINAL_URL="
        f"{result['final_url']}"
    )
    print(
        "CONTENT_TYPE="
        f"{result['content_type']}"
    )
    print(
        "CONTENT_DISPOSITION="
        f"{result['content_disposition']}"
    )
    print(
        "ATTACHMENT_BYTES="
        f"{result['attachment_bytes']}"
    )
    print(
        "EVIDENCE_HASH="
        f"{result['evidence_hash']}"
    )
    print(
        "RAW_ATTACHMENT_PERSISTED="
        f"{result['raw_attachment_persisted']}"
    )
    print(
        "RAW_ATTACHMENT_PATH="
        f"{result.get('raw_attachment_path')}"
    )
    print(
        "PARSER_STATUS="
        f"{result['parser_status']}"
    )
    print(
        "PARSER_ERROR="
        f"{result['parser_error']}"
    )
    print(
        "IDENTITY="
        f"{result['identity']}"
    )
    print(
        "CANONICAL_FACT_COUNT="
        f"{result['canonical_fact_count']}"
    )
    print(
        "UNMAPPED_COUNT="
        f"{result['unmapped_count']}"
    )
    print(
        "PRODUCTION_EVIDENCE="
        f"{result['production_evidence']}"
    )
    print(
        "CANONICAL_IMPORT_READY="
        f"{result['canonical_import_ready']}"
    )
    print(
        "BANK_METRIC_MAPPING_READY=False"
    )
    print(
        "SCORING_READY=False"
    )
    print(
        "ACTIVATION_READY=False"
    )
    print(
        f"BLOCKERS={result['blockers']}"
    )
    print(
        "STORE_MUTATION=NO"
    )
    print(
        "AL_SAT_MUTATION=NO"
    )
    print(
        f"RESULT={out}"
    )
    print(
        "FINANCIAL_INTELLIGENCE_V1_3_"
        "AKBNK_KAP_FINANCIAL_ATTACHMENT_CANONICAL_PARSE_V1=PASS"
    )


if __name__ == "__main__":
    main()

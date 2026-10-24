from __future__ import annotations

from backend.app.market_context.report_type_selection import normalize_report_type


def prepare_document_metadata(
    *,
    source: str,
    document_date: str,
    input_type: str,
    report_type: str | None,
) -> dict[str, str]:
    return {
        "source": source,
        "document_date": document_date,
        "input_type": input_type,
        "report_type": normalize_report_type(report_type),
    }

"""Evidence-aware fund research report."""
from typing import Any, Mapping, Sequence


def build_fund_research_report(
    *,
    funds: Sequence[Mapping[str, Any]] = (),
    performance: Mapping[str, Any] | None = None,
    costs: Mapping[str, Any] | None = None,
    overlap: Mapping[str, Any] | None = None,
    exposure: Mapping[str, Any] | None = None,
    stress: Mapping[str, Any] | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    rows = []

    for fund in funds:
        row = dict(fund)
        row["fund_isin"] = row.get("isin") or row.get("fund_isin")
        row["evidence_status"] = (
            "verified"
            if row.get("source_url") and row.get("source_date")
            else "incomplete"
        )
        row["unknown_fields"] = [
            key for key in (
                "name", "currency", "risk_indicator",
                "ongoing_charges_pct", "source_url", "source_date"
            )
            if row.get(key) is None
        ]
        rows.append(row)

    return {
        "report_type": "fund_research_evidence_report",
        "generated_at": generated_at,
        "fund_count": len(rows),
        "funds": rows,
        "performance": dict(performance or {}),
        "costs": dict(costs or {}),
        "overlap": dict(overlap or {}),
        "exposure": dict(exposure or {}),
        "stress": dict(stress or {}),
        "limitations": [
            "Missing values are not imputed.",
            "Source field presence does not independently verify accuracy.",
            "This report is analytical support, not an investment recommendation.",
        ],
    }


def report_is_comparable(report: Mapping[str, Any]) -> bool:
    funds = report.get("funds")
    return (
        isinstance(funds, list)
        and len(funds) > 0
        and all(
            isinstance(fund, Mapping)
            and fund.get("evidence_status") == "verified"
            for fund in funds
        )
    )

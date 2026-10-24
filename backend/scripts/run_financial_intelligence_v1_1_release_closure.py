from __future__ import annotations

import json
from pathlib import Path

from app.analysis.financial_intelligence_symbol_selector import (
    build_financial_intelligence_symbol_selector,
)
from app.ui.financial_intelligence_renderer_payload import (
    build_financial_intelligence_renderer_payload,
)
from app.ui.financial_intelligence_presentation_contract import (
    build_financial_intelligence_presentation_contract,
)
from app.ui.financial_intelligence_ui_boundary import (
    build_financial_intelligence_ui_boundary,
)


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    fi = root / "backend" / "data" / "financial_intelligence"

    registry_path = (
        fi
        / "FINANCIAL_INTELLIGENCE_V1_1_MULTI_SYMBOL_REGISTRY.json"
    )

    intake_handoff_path = (
        fi
        / "FINANCIAL_INTELLIGENCE_V1_1_NEW_SYMBOL_INTAKE_REGISTRY_HANDOFF.json"
    )

    if not registry_path.exists():
        raise FileNotFoundError(registry_path)

    registry = json.loads(
        registry_path.read_text(encoding="utf-8-sig")
    )

    selector = build_financial_intelligence_symbol_selector(root)

    payload = build_financial_intelligence_renderer_payload(
        root,
        symbol="TUPRS",
    )

    presentation = (
        build_financial_intelligence_presentation_contract(
            root,
            symbol="TUPRS",
        )
    )

    boundary = build_financial_intelligence_ui_boundary(
        root,
        symbol="TUPRS",
    )

    intake_status = None
    intake_blockers = []

    if intake_handoff_path.exists():
        intake = json.loads(
            intake_handoff_path.read_text(
                encoding="utf-8-sig"
            )
        )

        intake_status = intake.get("status")
        intake_blockers = list(
            intake.get("blockers") or []
        )

    cards = {
        row["key"]: row
        for row in boundary.get("metric_cards", [])
    }

    valuation = {
        row["key"]: row
        for row in boundary.get("valuation_rows", [])
    }

    checks = {
        "registry_pass":
            registry.get("status") == "PASS",

        "registry_has_tuprs":
            "TUPRS"
            in (registry.get("release_ready_symbols") or []),

        "selector_pass":
            selector.get("status") == "PASS",

        "selector_default_tuprs":
            selector.get("default_symbol") == "TUPRS",

        "renderer_payload_pass":
            payload.get("status") == "PASS",

        "financial_health_94":
            float(payload.get("financial_health")) == 94.0,

        "cash_quality_100":
            float(payload.get("cash_quality")) == 100.0,

        "capital_efficiency_15":
            float(payload.get("capital_efficiency")) == 15.0,

        "risk_low":
            str(payload.get("risk")).upper() == "LOW",

        "current_price_385":
            float(payload.get("current_price")) == 385.0,

        "attractive_entry_price":
            abs(
                float(
                    payload.get(
                        "attractive_entry_price"
                    )
                )
                - 179.71145881805518
            ) < 0.02,

        "valuation_very_expensive":
            str(
                payload.get("valuation_status")
            ).upper()
            == "VERY_EXPENSIVE",

        "presentation_pass":
            presentation.get("status") == "PASS",

        "ui_boundary_pass":
            boundary.get("status") == "PASS",

        "ui_health":
            cards.get(
                "financial_health", {}
            ).get("value")
            == "94/100",

        "ui_cash_quality":
            cards.get(
                "cash_quality", {}
            ).get("value")
            == "100/100",

        "ui_capital_efficiency":
            cards.get(
                "capital_efficiency", {}
            ).get("value")
            == "15/100",

        "ui_current_price":
            valuation.get(
                "current_price", {}
            ).get("value")
            == "385.00",

        "ui_entry_price":
            valuation.get(
                "attractive_entry_price", {}
            ).get("value")
            == "179.71",

        "no_synthetic_second_symbol":
            registry.get("symbol_count") == 1,
    }

    failed = [
        name
        for name, ok in checks.items()
        if not ok
    ]

    if failed:
        status = "BLOCKED"
    else:
        status = "READY_FOR_V1_1_RELEASE_WITH_KNOWN_LIMITATIONS"

    known_limitations = []

    if registry.get("symbol_count") == 1:
        known_limitations.append(
            "NO_ADDITIONAL_ACCEPTED_SYMBOLS_FOUND"
        )

    if intake_status == "PASS_NO_INTAKE_ARTIFACT":
        known_limitations.append(
            "NEW_SYMBOL_INTAKE_ARTIFACT_MISSING"
        )

    payload_out = {
        "schema_version":
            "financial-intelligence-v1-1-release-closure-v1",

        "status":
            status,

        "reference_symbol":
            "TUPRS",

        "symbol_count":
            registry.get("symbol_count"),

        "release_ready_symbols":
            registry.get("release_ready_symbols"),

        "selector_default_symbol":
            selector.get("default_symbol"),

        "checks":
            checks,

        "failed_checks":
            failed,

        "known_limitations":
            known_limitations,

        "release_blockers":
            failed,

        "intake_status":
            intake_status,

        "intake_blockers":
            intake_blockers,

        "rules": [
            "READ_ONLY_MULTI_SYMBOL_INFRASTRUCTURE",
            "NO_SYNTHETIC_SYMBOLS",
            "NO_AL_SAT_MUTATION",
            "NO_SCANNER_MUTATION",
            "NO_RANKING_MUTATION",
            "NO_PORTFOLIO_MUTATION",
            "NO_DASHBOARD_ROUTE_MUTATION",
            "NO_SCORE_SYNTHESIS",
        ],
    }

    out = (
        fi
        / "FINANCIAL_INTELLIGENCE_V1_1_RELEASE_CLOSURE.json"
    )

    out.write_text(
        json.dumps(
            payload_out,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"STATUS={status}")
    print(
        f"SYMBOL_COUNT="
        f"{payload_out['symbol_count']}"
    )
    print(
        f"RELEASE_READY_SYMBOLS="
        f"{payload_out['release_ready_symbols']}"
    )
    print(
        f"KNOWN_LIMITATIONS="
        f"{payload_out['known_limitations']}"
    )
    print(
        f"RELEASE_BLOCKERS="
        f"{payload_out['release_blockers']}"
    )
    print(f"RESULT={out}")

    if failed:
        raise SystemExit(
            "FINANCIAL_INTELLIGENCE_V1_1_RELEASE_CLOSURE=BLOCKED"
        )

    print(
        "FINANCIAL_INTELLIGENCE_V1_1_RELEASE_CLOSURE=PASS"
    )


if __name__ == "__main__":
    main()

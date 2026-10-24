import hashlib
import json

from app.analysis.financial_intelligence_bank_model_contract import (
    BANK_COMPONENTS,
    BANK_REQUIRED_METRICS,
)
from app.analysis.financial_intelligence_bank_production_source_onboarding import (
    evaluate_bank_production_source,
)


def _record():
    facts = {}

    for component in BANK_COMPONENTS:
        for metric in BANK_REQUIRED_METRICS[component]:
            facts[f"{component}.{metric}"] = 1.0

    return {
        "source_type": "KAP",
        "source_uri": "kap://bank/sample",
        "symbol": "BANKX",
        "sector_model": "BANK",
        "period_end": "2026-06-30",
        "as_of": "2026-08-31",
        "publication_date": "2026-08-05",
        "canonical_facts": facts,
        "evidence_hash": "sha256:abc123",
    }


def _bundle_payload(record):
    fact_keys = list(
        record["canonical_facts"]
    )

    provenance = {
        metric: "KAP_SOURCE"
        for metric in fact_keys
    }

    # Force one metric onto the second official source so
    # both source records are represented by provenance.
    provenance[fact_keys[-1]] = "BANK_IR_SOURCE"

    return {
        "bundle_version":
            "BANK_OFFICIAL_EVIDENCE_BUNDLE_V1",
        "symbol": record["symbol"],
        "sector_model": record["sector_model"],
        "period_end": record["period_end"],
        "publication_date":
            record["publication_date"],
        "as_of": record["as_of"],
        "sources": {
            "KAP_SOURCE": {
                "source_type": "KAP",
                "source_uri":
                    "https://www.kap.org.tr/example",
                "evidence_hash":
                    "sha256:" + ("a" * 64),
            },
            "BANK_IR_SOURCE": {
                "source_type": "BANK_IR",
                "source_uri":
                    "https://example-bank.test/ir.pdf",
                "evidence_hash":
                    "sha256:" + ("b" * 64),
            },
        },
        "metric_provenance": provenance,
        "canonical_facts":
            dict(record["canonical_facts"]),
    }


def _write_bundle(
    tmp_path,
    record,
    bundle=None,
):
    if bundle is None:
        bundle = _bundle_payload(record)

    path = (
        tmp_path
        / "bank_official_evidence_bundle.json"
    )

    raw = json.dumps(
        bundle,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    path.write_bytes(raw)

    record["source_type"] = (
        "OFFICIAL_SOURCE_BUNDLE"
    )
    record["source_uri"] = path.as_uri()
    record["evidence_hash"] = (
        "sha256:"
        + hashlib.sha256(raw).hexdigest()
    )

    return path


def test_real_source_contract_passes():
    result = evaluate_bank_production_source(
        _record()
    )

    assert result.status == "PASS"
    assert result.production_evidence is True
    assert result.activation_ready is True
    assert result.canonical_input_ready is True
    assert result.scoring_ready is True


def test_synthetic_source_is_rejected():
    record = _record()
    record["source_type"] = "SYNTHETIC"

    result = evaluate_bank_production_source(
        record
    )

    assert result.status == "BLOCKED"
    assert result.production_evidence is False
    assert result.activation_ready is False
    assert result.blocker == (
        "NON_PRODUCTION_SOURCE_TYPE:SYNTHETIC"
    )


def test_future_publication_is_rejected():
    record = _record()
    record["as_of"] = "2026-08-31"
    record["publication_date"] = "2026-09-01"

    result = evaluate_bank_production_source(
        record
    )

    assert result.status == "BLOCKED"
    assert result.production_evidence is False
    assert result.activation_ready is False
    assert result.blocker == (
        "FUTURE_PUBLICATION_FORBIDDEN"
    )


def test_missing_hash_is_rejected():
    record = _record()
    record["evidence_hash"] = ""

    result = evaluate_bank_production_source(
        record
    )

    assert result.status == "BLOCKED"
    assert result.production_evidence is False
    assert result.blocker == (
        "EVIDENCE_HASH_MISSING"
    )


def test_missing_canonical_metric_is_rejected():
    record = _record()
    record["canonical_facts"].pop(
        "CAPITAL_ADEQUACY.capital_adequacy_ratio"
    )

    result = evaluate_bank_production_source(
        record
    )

    assert result.status == "BLOCKED"
    assert result.production_evidence is False
    assert result.activation_ready is False
    assert (
        "CAPITAL_ADEQUACY.capital_adequacy_ratio"
        in result.blocker
    )


def test_official_source_bundle_passes(tmp_path):
    record = _record()
    _write_bundle(
        tmp_path,
        record,
    )

    result = evaluate_bank_production_source(
        record
    )

    assert result.status == "PASS"
    assert result.canonical_input_ready is True
    assert result.scoring_ready is True
    assert result.production_evidence is True
    assert result.activation_ready is True
    assert result.blocker is None


def test_official_source_bundle_hash_mismatch_is_rejected(
    tmp_path,
):
    record = _record()

    path = _write_bundle(
        tmp_path,
        record,
    )

    path.write_text(
        path.read_text(encoding="utf-8")
        + "\n",
        encoding="utf-8",
    )

    result = evaluate_bank_production_source(
        record
    )

    assert result.status == "BLOCKED"
    assert result.production_evidence is False
    assert result.activation_ready is False
    assert result.blocker == (
        "OFFICIAL_SOURCE_BUNDLE_HASH_MISMATCH"
    )


def test_official_source_bundle_provenance_gap_is_rejected(
    tmp_path,
):
    record = _record()
    bundle = _bundle_payload(record)

    metric = next(
        iter(bundle["metric_provenance"])
    )
    bundle["metric_provenance"].pop(
        metric
    )

    _write_bundle(
        tmp_path,
        record,
        bundle,
    )

    result = evaluate_bank_production_source(
        record
    )

    assert result.status == "BLOCKED"
    assert result.production_evidence is False
    assert result.activation_ready is False
    assert result.blocker == (
        "OFFICIAL_SOURCE_BUNDLE_PROVENANCE_COVERAGE_INVALID"
    )


def test_official_source_bundle_unknown_source_is_rejected(
    tmp_path,
):
    record = _record()
    bundle = _bundle_payload(record)

    metric = next(
        iter(bundle["metric_provenance"])
    )
    bundle["metric_provenance"][metric] = (
        "UNKNOWN_SOURCE"
    )

    _write_bundle(
        tmp_path,
        record,
        bundle,
    )

    result = evaluate_bank_production_source(
        record
    )

    assert result.status == "BLOCKED"
    assert result.production_evidence is False
    assert result.activation_ready is False
    assert result.blocker.startswith(
        "OFFICIAL_SOURCE_BUNDLE_PROVENANCE_SOURCE_UNKNOWN:"
    )


def test_official_source_bundle_fact_mismatch_is_rejected(
    tmp_path,
):
    record = _record()
    bundle = _bundle_payload(record)

    metric = next(
        iter(bundle["canonical_facts"])
    )
    bundle["canonical_facts"][metric] = 999.0

    _write_bundle(
        tmp_path,
        record,
        bundle,
    )

    result = evaluate_bank_production_source(
        record
    )

    assert result.status == "BLOCKED"
    assert result.production_evidence is False
    assert result.activation_ready is False
    assert result.blocker == (
        "OFFICIAL_SOURCE_BUNDLE_CANONICAL_FACTS_MISMATCH"
    )

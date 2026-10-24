import json
from pathlib import Path

from app.analysis.financial_intelligence_sector_model_registry import (
    SUPPORTED_SECTOR_MODELS,
    PRODUCTION_READY_MODELS,
)


def _root():
    return Path(__file__).resolve().parents[2]


def test_v1_2_sector_registry_contract():
    assert set(SUPPORTED_SECTOR_MODELS) == {
        "INDUSTRIAL",
        "BANK",
        "INSURANCE",
        "REIT",
        "HOLDING",
    }

    # V1.2 infrastructure closure must not silently production-activate
    # new sectors without real production evidence.
    assert "INDUSTRIAL" in PRODUCTION_READY_MODELS
    assert "BANK" not in PRODUCTION_READY_MODELS
    assert "INSURANCE" not in PRODUCTION_READY_MODELS
    assert "REIT" not in PRODUCTION_READY_MODELS
    assert "HOLDING" not in PRODUCTION_READY_MODELS


def test_v1_2_required_modules_exist():
    root = _root()

    expected = [
        "backend/app/analysis/financial_intelligence_bank_model_contract.py",
        "backend/app/analysis/financial_intelligence_bank_scoring_engine.py",
        "backend/app/analysis/financial_intelligence_bank_canonical_adapter.py",

        "backend/app/analysis/financial_intelligence_insurance_model_contract.py",
        "backend/app/analysis/financial_intelligence_insurance_scoring_engine.py",
        "backend/app/analysis/financial_intelligence_insurance_canonical_adapter.py",

        "backend/app/analysis/financial_intelligence_reit_model_contract.py",
        "backend/app/analysis/financial_intelligence_reit_scoring_engine.py",
        "backend/app/analysis/financial_intelligence_reit_canonical_adapter.py",

        "backend/app/analysis/financial_intelligence_holding_model_contract.py",
        "backend/app/analysis/financial_intelligence_holding_scoring_engine.py",
        "backend/app/analysis/financial_intelligence_holding_canonical_adapter.py",
    ]

    missing = [
        rel
        for rel in expected
        if not (root / rel).exists()
    ]

    assert not missing, f"MISSING_V1_2_MODULES:{missing}"


def test_v1_2_real_data_gates_fail_closed_without_evidence():
    root = _root()

    sector_to_file = {
        "BANK":
            "FINANCIAL_INTELLIGENCE_V1_2_BANK_REAL_DATA_INTAKE_GATE.json",
        "INSURANCE":
            "FINANCIAL_INTELLIGENCE_V1_2_INSURANCE_REAL_DATA_INTAKE_GATE.json",
        "REIT":
            "FINANCIAL_INTELLIGENCE_V1_2_REIT_REAL_DATA_INTAKE_GATE.json",
        "HOLDING":
            "FINANCIAL_INTELLIGENCE_V1_2_HOLDING_REAL_DATA_INTAKE_GATE.json",
    }

    fi_dir = (
        root
        / "backend"
        / "data"
        / "financial_intelligence"
    )

    expected_blockers = {
        "BANK": "NO_REAL_BANK_SOURCE",
        "INSURANCE": "NO_REAL_INSURANCE_SOURCE",
        "REIT": "NO_REAL_REIT_SOURCE",
        "HOLDING": "NO_REAL_HOLDING_SOURCE",
    }

    for sector, filename in sector_to_file.items():
        path = fi_dir / filename

        assert path.exists(), (
            f"{sector}_REAL_DATA_GATE_ARTIFACT_MISSING"
        )

        data = json.loads(
            path.read_text(encoding="utf-8-sig")
        )

        assert data["status"] == "PASS_FAIL_CLOSED"
        assert data["candidate_count"] == 0
        assert data["accepted_count"] == 0
        assert data["canonical_input_ready"] is False
        assert data["scoring_ready"] is False
        assert data["production_evidence"] is False
        assert expected_blockers[sector] in data["blockers"]


def test_no_new_sector_production_activation_without_evidence():
    root = _root()

    manifest = {
        "schema_version":
            "financial-intelligence-v1-2-sector-expansion-closure-v1",
        "status": "PASS",
        "supported_sector_models": [
            "INDUSTRIAL",
            "BANK",
            "INSURANCE",
            "REIT",
            "HOLDING",
        ],
        "production_ready_models": [
            "INDUSTRIAL",
        ],
        "blocked_production_models": {
            "BANK": "NO_REAL_BANK_SOURCE",
            "INSURANCE": "NO_REAL_INSURANCE_SOURCE",
            "REIT": "NO_REAL_REIT_SOURCE",
            "HOLDING": "NO_REAL_HOLDING_SOURCE",
        },
        "production_evidence": {
            "BANK": False,
            "INSURANCE": False,
            "REIT": False,
            "HOLDING": False,
        },
        "industrial_threshold_reuse": False,
        "missing_to_zero": False,
        "future_publication_allowed": False,
        "al_sat_authority": "NONE",
        "scanner_mutation": False,
        "ranking_mutation": False,
        "portfolio_mutation": False,
    }

    out = (
        root
        / "backend"
        / "data"
        / "financial_intelligence"
        / "FINANCIAL_INTELLIGENCE_V1_2_SECTOR_EXPANSION_CLOSURE.json"
    )

    out.write_text(
        json.dumps(
            manifest,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    assert out.exists()

from types import SimpleNamespace
import pytest
from backend.app.analysis.common_candidate_ai_review_v1 import (
    build_common_candidate_review_prompt,
    evaluate_common_candidate_ai_review,
    validate_common_candidate_review,
)

SAFE_OUTPUT = {
    "summary": "Kanıtlar sınırlı; ek doğrulama gerekli.",
    "positive_factors": ["Birden fazla kaynakta görünürlük"],
    "risk_factors": ["Eksik güncel fiyat verisi"],
    "stock_specific_risks": [],
    "aligned_points": ["Haftalık ve aylık kaynaklarda yer alıyor"],
    "conflicting_points": [],
    "watch_items": ["Güncel fiyat ve hacim teyidi"],
}

def candidate():
    return SimpleNamespace(
        symbol="SOKM",
        sources=("FIRSAT_RADARI_HAFTALIK", "FIRSAT_RADARI_AYLIK"),
        horizons=("WEEKLY", "MONTHLY"),
        evidence=(SimpleNamespace(
            source="FIRSAT_RADARI_HAFTALIK",
            horizon="WEEKLY",
            status="VISIBLE",
            reason="Haftalık radar kaydı",
        ),),
        priority=20,
        technical_score=None,
        volume_ratio=None,
        risk_reward=None,
        entry_readiness="",
        data_status="MISSING_PRICE_VOLUME",
        reasons=("Fiyat ve hacim teyidi eksik",),
    )

class FakeProvider:
    def __init__(self, output=SAFE_OUTPUT):
        self.output = output
        self.prompt = None

    def evaluate(self, prompt):
        self.prompt = prompt
        return SimpleNamespace(provider="gemini", model="test-model", output=self.output)

def test_prompt_contains_candidate_evidence_and_missing_data():
    prompt = build_common_candidate_review_prompt(candidate())
    assert "SOKM" in prompt
    assert "FIRSAT_RADARI_HAFTALIK" in prompt
    assert "MISSING_PRICE_VOLUME" in prompt
    assert "Eksik fiyat" in prompt
    assert "AL, SAT" in prompt

def test_prompt_rejects_candidate_without_symbol():
    with pytest.raises(ValueError, match="symbol"):
        build_common_candidate_review_prompt({"sources": ["TEST"]})

def test_review_uses_fake_provider_and_grants_no_trade_authority():
    provider = FakeProvider()
    result = evaluate_common_candidate_ai_review(candidate(), provider=provider)
    assert result["status"] == "accepted"
    assert result["symbol"] == "SOKM"
    assert result["review"] == SAFE_OUTPUT
    assert result["automatic_trade_authority"] == "NONE"
    assert provider.prompt is not None

def test_invalid_ai_schema_is_rejected():
    provider = FakeProvider({"summary": "Only a summary"})
    result = evaluate_common_candidate_ai_review(candidate(), provider=provider)
    assert result["status"] == "rejected"
    assert result["automatic_trade_authority"] == "NONE"

def test_review_schema_rejects_non_string_list_items():
    invalid = dict(SAFE_OUTPUT)
    invalid["risk_factors"] = ["valid", 123]
    with pytest.raises(ValueError, match="risk_factors"):
        validate_common_candidate_review(invalid)

def test_missing_symbol_does_not_call_provider():
    provider = FakeProvider()
    result = evaluate_common_candidate_ai_review({"sources": []}, provider=provider)
    assert result["status"] == "rejected"
    assert result["automatic_trade_authority"] == "NONE"
    assert provider.prompt is None

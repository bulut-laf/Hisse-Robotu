\
import pytest

from backend.app.market_context.models import MarketContextDocument


def _document(**overrides):
    payload = {
        "document_id": "doc-001",
        "source": "ICBC",
        "document_date": "2026-08-03",
        "imported_at": "2026-08-03T07:00:00Z",
        "input_type": "text",
        "raw_text": "BIST100 güne pozitif başlayabilir.",
        "content_hash": "abc123",
    }
    payload.update(overrides)
    return MarketContextDocument(**payload)


def test_market_context_document_round_trip():
    document = _document(
        index_outlook="Temkinli / Pozitif",
        supports=["13.200", "12.966"],
        resistances=["13.635-13.721", "13.872-14.085", "14.228"],
        external_market_outlook="Pozitif",
        futures_outlook="Pozitif",
    )

    restored = MarketContextDocument.from_dict(document.to_dict())

    assert restored.document_id == "doc-001"
    assert restored.index_outlook == "Temkinli / Pozitif"
    assert restored.supports == ["13.200", "12.966"]
    assert restored.ai_review_status == "not_reviewed"


@pytest.mark.parametrize("input_type", ["text", "txt", "pdf"])
def test_supported_input_types(input_type):
    document = _document(input_type=input_type)
    document.validate()


def test_invalid_input_type_is_rejected():
    with pytest.raises(ValueError):
        _document(input_type="docx").validate()


def test_model_does_not_contain_trading_score_fields():
    data = _document().to_dict()

    forbidden = {
        "score",
        "technical_score",
        "buy_signal",
        "sell_signal",
        "candidate_rank",
    }

    assert forbidden.isdisjoint(data)

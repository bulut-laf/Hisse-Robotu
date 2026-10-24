import pytest

from backend.app.market_context.ai_provider import AIProviderConfig, OUTPUT_SCHEMA
from backend.app.market_context.report_date_detection import detect_report_date
from backend.app.market_context.service import (
    MarketContextDateMismatchError,
    MarketContextService,
)
from backend.app.market_context.source_normalization import normalize_source_name

def test_source_normalization_aliases():
    assert normalize_source_name("icbc") == "ICBC"
    assert normalize_source_name("  yatırım   finansman ") == "Yatırım Finansman"
    assert normalize_source_name("YATIRIM FINANSMAN") == "Yatırım Finansman"
    assert normalize_source_name("KAP Haberleri") == "KAP"

def test_unknown_source_is_preserved():
    assert normalize_source_name("Erste Market") == "Erste Market"

def test_detect_numeric_report_date():
    assert detect_report_date("GÜNLÜK BÜLTEN 03.08.2026\nBIST100") == "2026-08-03"

def test_detect_turkish_report_date():
    assert detect_report_date("Tarih 3 Ağu 2026 Pzt 17:38") == "2026-08-03"

def test_service_rejects_date_mismatch(tmp_path):
    service = MarketContextService(data_root=tmp_path)
    with pytest.raises(MarketContextDateMismatchError) as exc:
        service.import_text(
            text="GÜNLÜK BÜLTEN 03.08.2026\nBIST100 pozitif.",
            source="icbc",
            document_date="2026-08-04",
        )
    assert exc.value.detected_date == "2026-08-03"

def test_service_normalizes_source(tmp_path):
    service = MarketContextService(data_root=tmp_path)
    document = service.import_text(
        text="BIST100 pozitif.",
        source="icbc",
        document_date="2026-08-03",
        document_id="source-normalized",
    )
    assert document.source == "ICBC"
    assert service.store.load_manifest("2026-08-03").sources == ["ICBC"]

def test_default_gemini_model(monkeypatch):
    monkeypatch.delenv("HISSE_ROBOTU_AI_PROVIDER", raising=False)
    monkeypatch.delenv("HISSE_ROBOTU_GEMINI_MODEL", raising=False)
    config = AIProviderConfig.from_environment()
    assert config.model == "gemini-3.5-flash-lite"

def test_ai_schema_has_stock_specific_risks():
    assert "stock_specific_risks" in OUTPUT_SCHEMA["properties"]
    assert "stock_specific_risks" in OUTPUT_SCHEMA["required"]

from pathlib import Path

from backend.app.market_context.service import MarketContextService


def test_market_context_service_module_has_no_technical_analysis_imports():
    source_path = Path("backend/app/market_context/service.py")
    source = source_path.read_text(encoding="utf-8").casefold()

    forbidden_import_fragments = (
        "backend.app.analysis",
        "backend.app.indicators",
        "backend.app.risk",
        "backend.app.prebreakout",
        "market_regime",
        "technical_score",
        "candidate_rank",
    )

    for fragment in forbidden_import_fragments:
        assert fragment not in source


def test_market_context_import_does_not_touch_unrelated_data_files(tmp_path):
    data_root = tmp_path / "data"
    data_root.mkdir()

    sentinel = data_root / "prebreakout_alarm_history.jsonl"
    sentinel.write_text("ORIGINAL", encoding="utf-8")

    service = MarketContextService(data_root=data_root)
    service.import_text(
        text="BIST100 pozitif.",
        source="ICBC",
        document_date="2026-08-03",
    )

    assert sentinel.read_text(encoding="utf-8") == "ORIGINAL"

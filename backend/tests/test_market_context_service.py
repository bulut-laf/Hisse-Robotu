import pytest

from backend.app.market_context.service import MarketContextService
from backend.app.market_context.store import DuplicateMarketContextError


SAMPLE = """
BIST100 endeksinin güne temkinli ancak pozitif bir başlangıç yapmasını bekliyoruz.
Ağustos vadeli BIST30 kontratı cuma akşam seansını 27 puan artıda tamamladı.
Asya piyasaları ve ABD vadeli endeksleri pozitif seyrediyor.
BIST100 için 13.200 ve 12.966 destek;
13.635–13.721, 13.872–14.085 ve 14.228 direnç olarak izleniyor.
"""


def test_service_import_text_runs_full_pipeline(tmp_path):
    service = MarketContextService(data_root=tmp_path)

    document = service.import_text(
        text=SAMPLE,
        source="ICBC",
        document_date="2026-08-03",
        document_id="doc-001",
    )

    assert document.document_id == "doc-001"
    assert document.source == "ICBC"
    assert document.index_outlook == "Temkinli / Pozitif"
    assert "13.200" in document.supports
    assert "14.228" in document.resistances
    assert document.archive_status == "archived"
    assert document.ai_review_status == "not_reviewed"

    assert (
        tmp_path
        / "market_context_raw"
        / "2026-08-03"
        / "doc-001.txt"
    ).exists()

    assert (
        tmp_path
        / "market_context_processed"
        / "2026-08-03"
        / "doc-001.json"
    ).exists()

    assert (
        tmp_path
        / "market_context_archive"
        / "2026-08-03"
        / "daily_manifest.json"
    ).exists()


def test_service_import_txt_runs_full_pipeline(tmp_path):
    txt_path = tmp_path / "bulten.txt"
    txt_path.write_text(
        "BIST100 pozitif. 13.200 destek, 14.228 direnç.",
        encoding="utf-8",
    )

    service = MarketContextService(data_root=tmp_path)
    document = service.import_txt(
        path=txt_path,
        source="Gedik",
        document_date="2026-08-03",
        document_id="doc-002",
    )

    assert document.input_type == "txt"
    assert document.source == "Gedik"
    assert document.archive_status == "archived"


def test_service_rejects_duplicate_content(tmp_path):
    service = MarketContextService(data_root=tmp_path)

    service.import_text(
        text="BIST100 pozitif.",
        source="ICBC",
        document_date="2026-08-03",
        document_id="doc-001",
    )

    with pytest.raises(
        DuplicateMarketContextError,
        match="daha önce yüklenmiş",
    ):
        service.import_text(
            text="BIST100 pozitif.",
            source="Başka Kaynak",
            document_date="2026-08-03",
            document_id="doc-999",
        )


def test_service_allows_multiple_distinct_reports_same_day(tmp_path):
    service = MarketContextService(data_root=tmp_path)

    service.import_text(
        text="ICBC: BIST100 pozitif.",
        source="ICBC",
        document_date="2026-08-03",
        document_id="doc-001",
    )
    service.import_text(
        text="Gedik: BIST100 temkinli.",
        source="Gedik",
        document_date="2026-08-03",
        document_id="doc-002",
    )

    manifest = service.store.load_manifest("2026-08-03")

    assert manifest.document_count == 2
    assert set(manifest.sources) == {"ICBC", "Gedik"}


def test_service_does_not_produce_trading_decision_fields(tmp_path):
    service = MarketContextService(data_root=tmp_path)

    document = service.import_text(
        text=SAMPLE,
        source="ICBC",
        document_date="2026-08-03",
    )

    payload = document.to_dict()

    assert "technical_score" not in payload
    assert "buy_signal" not in payload
    assert "sell_signal" not in payload
    assert "candidate_rank" not in payload

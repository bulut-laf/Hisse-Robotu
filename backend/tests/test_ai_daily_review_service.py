from __future__ import annotations

import json
from pathlib import Path

from backend.app.market_context.ai_daily_review_service import (
    DailyAIReviewService,
)
from backend.app.market_context.archive import (
    DailyArchiveDocumentRef,
    DailyArchiveManifest,
)


def _write_manifest_and_documents(tmp_path: Path, date: str = "2026-08-03"):
    data_root = tmp_path / "data"
    processed = data_root / "market_context_processed" / date
    archive = data_root / "market_context_archive" / date
    processed.mkdir(parents=True)
    archive.mkdir(parents=True)

    docs = [
        {
            "document_id": "doc-1",
            "source": "Kurum A",
            "document_date": date,
            "input_type": "text",
            "raw_text": "BIST 100 için temkinli pozitif görünüm.",
            "index_outlook": "Temkinli pozitif",
            "supports": ["10.500"],
            "resistances": ["10.800"],
            "macro_risks": ["Faiz"],
            "sector_impacts": [],
            "stock_news": [],
            "notes": [],
        },
        {
            "document_id": "doc-2",
            "source": "Kurum B",
            "document_date": date,
            "input_type": "pdf",
            "raw_text": "Küresel riskler nedeniyle temkinli görünüm.",
            "index_outlook": "Temkinli",
            "supports": [],
            "resistances": [],
            "macro_risks": ["Küresel risk"],
            "sector_impacts": [],
            "stock_news": [],
            "notes": [],
        },
    ]

    refs = []
    for doc in docs:
        path = processed / f"{doc['document_id']}.json"
        path.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
        refs.append(
            DailyArchiveDocumentRef(
                document_id=doc["document_id"],
                source=doc["source"],
                document_date=date,
                input_type=doc["input_type"],
                content_hash=f"hash-{doc['document_id']}",
                processed_path=str(path.relative_to(data_root)),
            )
        )

    manifest = DailyArchiveManifest(
        date=date,
        documents=refs,
        sources=["Kurum A", "Kurum B"],
        created_at="2026-08-03T10:00:00Z",
        updated_at="2026-08-03T10:00:00Z",
    )
    manifest.save(archive / "daily_manifest.json")

    return data_root


def test_build_daily_package_preserves_multi_report_traceability(tmp_path):
    data_root = _write_manifest_and_documents(tmp_path)
    service = DailyAIReviewService(data_root=data_root, evaluator=lambda _: {})

    package = service.build_daily_package("2026-08-03")

    assert package["date"] == "2026-08-03"
    assert package["report_count"] == 2
    assert package["sources"] == ["Kurum A", "Kurum B"]
    assert [item["document_id"] for item in package["reports"]] == ["doc-1", "doc-2"]
    assert package["reports"][0]["raw_text"].startswith("BIST 100")
    assert package["reports"][1]["structured_context"]["macro_risks"] == ["Küresel risk"]


def test_successful_review_is_archived_and_manifest_is_updated(tmp_path):
    data_root = _write_manifest_and_documents(tmp_path)

    def evaluator(package):
        assert package["report_count"] == 2
        return {
            "ok": True,
            "status": "accepted",
            "provider": "gemini",
            "model": "test-model",
            "elapsed_seconds": 0.25,
            "output": {
                "summary": "Temkinli görünüm.",
                "positive_factors": ["İç piyasa desteği"],
                "risk_factors": ["Faiz"],
                "aligned_points": ["Temkinlilik"],
                "conflicting_points": [],
                "watch_items": ["Faiz"],
            },
            "error": "",
        }

    service = DailyAIReviewService(data_root=data_root, evaluator=evaluator)
    result = service.run_daily_review("2026-08-03")

    assert result["ok"] is True
    assert result["status"] == "reviewed"
    assert result["record"]["provider"] == "gemini"
    assert result["record"]["report_count"] == 2

    manifest = service.store.load_manifest("2026-08-03")
    assert manifest.ai_review_status == "reviewed"
    assert manifest.ai_review_id == result["review_id"]

    loaded = service.load_latest_review("2026-08-03")
    assert loaded is not None
    assert loaded["review_id"] == result["review_id"]
    assert loaded["output"]["summary"] == "Temkinli görünüm."


def test_failed_provider_does_not_change_existing_manifest_state(tmp_path):
    data_root = _write_manifest_and_documents(tmp_path)

    def evaluator(_package):
        return {
            "ok": False,
            "status": "provider_error",
            "provider": "gemini",
            "model": "test-model",
            "output": {},
            "error": "Geçici sağlayıcı hatası",
        }

    service = DailyAIReviewService(data_root=data_root, evaluator=evaluator)
    result = service.run_daily_review("2026-08-03")

    assert result["ok"] is False
    assert result["status"] == "provider_error"

    manifest = service.store.load_manifest("2026-08-03")
    assert manifest.ai_review_status == "not_reviewed"
    assert manifest.ai_review_id is None

    evaluation_root = data_root / "market_context_ai_evaluations"
    assert not evaluation_root.exists()


def test_no_reports_returns_safe_status_without_provider_call(tmp_path):
    data_root = tmp_path / "data"
    calls = []

    def evaluator(package):
        calls.append(package)
        raise AssertionError("Provider çağrılmamalı.")

    service = DailyAIReviewService(data_root=data_root, evaluator=evaluator)
    result = service.run_daily_review("2026-08-03")

    assert result["ok"] is False
    assert result["status"] == "no_reports"
    assert calls == []

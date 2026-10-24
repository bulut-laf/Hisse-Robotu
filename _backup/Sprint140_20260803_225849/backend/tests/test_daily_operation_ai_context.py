from __future__ import annotations

import json

from backend.app.analysis.daily_operation_ai_context import (
    build_daily_ai_operation_context,
    load_daily_ai_operation_context,
)


def record(*, record_date, created_at, risks=None, positives=None, conflicts=None, watch=None):
    return {
        "date": record_date,
        "created_at": created_at,
        "provider": "gemini",
        "model": "test-model",
        "report_count": 2,
        "output": {
            "summary": f"{record_date} özeti",
            "positive_factors": positives or [],
            "risk_factors": risks or [],
            "aligned_points": [],
            "conflicting_points": conflicts or [],
            "watch_items": watch or [],
        },
    }


def test_latest_review_and_previous_review_are_compared():
    context = build_daily_ai_operation_context(
        [
            record(record_date="2026-08-02", created_at="2026-08-02T18:00:00Z",
                   risks=["Faiz", "Petrol"], positives=["Asya"]),
            record(record_date="2026-08-03", created_at="2026-08-03T19:00:00Z",
                   risks=["Faiz", "Kur"], positives=["Asya", "ABD vadeli"],
                   conflicts=["Kurum görüşleri ayrışıyor"], watch=["BIST100 destekleri"]),
        ],
        today="2026-08-03",
    )

    assert context.available
    assert context.current_day
    assert context.review_date == "2026-08-03"
    assert context.previous_date == "2026-08-02"
    assert context.added_risks == ("Kur",)
    assert context.resolved_risks == ("Petrol",)
    assert context.added_positive_factors == ("ABD vadeli",)
    assert context.removed_positive_factors == ()
    assert context.conflicting_points == ("Kurum görüşleri ayrışıyor",)
    assert context.watch_items == ("BIST100 destekleri",)


def test_latest_record_of_same_day_is_used():
    context = build_daily_ai_operation_context(
        [
            record(record_date="2026-08-03", created_at="2026-08-03T10:00:00Z", risks=["Eski risk"]),
            record(record_date="2026-08-03", created_at="2026-08-03T20:00:00Z", risks=["Yeni risk"]),
        ],
        today="2026-08-03",
    )
    assert context.risk_factors == ("Yeni risk",)


def test_no_archive_returns_safe_unavailable_context():
    context = build_daily_ai_operation_context([], today="2026-08-03")
    assert not context.available
    assert context.review_date is None


def test_stale_review_is_marked_as_not_current_day():
    context = build_daily_ai_operation_context(
        [record(record_date="2026-08-02", created_at="2026-08-02T20:00:00Z")],
        today="2026-08-03",
    )
    assert context.available
    assert not context.current_day


def test_loader_reads_sprint139c_archive_and_skips_broken_json(tmp_path):
    root = tmp_path / "market_context_ai_evaluations" / "2026-08-03"
    root.mkdir(parents=True)

    payload = record(
        record_date="2026-08-03",
        created_at="2026-08-03T20:00:00Z",
        risks=["Faiz"],
    )
    (root / "good.json").write_text(
        json.dumps(payload, ensure_ascii=False),
        encoding="utf-8",
    )
    (root / "broken.json").write_text("{", encoding="utf-8")

    context = load_daily_ai_operation_context(tmp_path, today="2026-08-03")
    assert context.available
    assert context.risk_factors == ("Faiz",)

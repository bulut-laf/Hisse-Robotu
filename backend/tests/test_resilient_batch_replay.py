from datetime import date

from backend.app.history.batch_historical_export import BatchReplayRequest
from backend.app.history.resilient_batch_replay import run_resilient_batch_replay


def test_progress_her_gun_started_completed():
    events = []

    result = run_resilient_batch_replay(
        BatchReplayRequest(date(2026, 7, 1), date(2026, 7, 2), "BIST100"),
        scan_day=lambda d, u: [{"Hisse": "AAA"}],
        on_progress=events.append,
    )

    assert result.batch.processed_days == 2
    assert result.failed_days == 0
    assert [e.status for e in events] == [
        "started", "completed", "started", "completed"
    ]


def test_hata_bir_sonraki_gunu_engellemez():
    def scan_day(cut_date, universe):
        if cut_date == date(2026, 7, 1):
            raise RuntimeError("veri yok")
        return [{"Hisse": "BBB"}]

    result = run_resilient_batch_replay(
        BatchReplayRequest(date(2026, 7, 1), date(2026, 7, 2), "BIST100"),
        scan_day=scan_day,
    )

    assert result.failed_days == 1
    assert result.batch.processed_days == 1
    assert result.batch.total_rows == 1
    assert result.batch.combined_rows[0]["Hisse"] == "BBB"


def test_hata_tarihi_kaydedilir():
    result = run_resilient_batch_replay(
        BatchReplayRequest(date(2026, 7, 1), date(2026, 7, 1), "BIST100"),
        scan_day=lambda d, u: (_ for _ in ()).throw(ValueError("bozuk")),
    )
    assert result.failures[0].cut_date == date(2026, 7, 1)
    assert "ValueError" in result.failures[0].error

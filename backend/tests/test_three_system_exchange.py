import json

from backend.app.integration.three_system_exchange import write_scan_row_opinion


def test_hisse_robotu_writer_uses_existing_scan_row_shape(tmp_path):
    path = write_scan_row_opinion(
        {
            "Sıra": 3,
            "Hisse": "ASTOR",
            "Skor": 83.93,
            "Durum": "Teknik aday",
        },
        as_of="2026-08-12",
        exchange_dir=tmp_path,
    )
    data = json.loads(path.read_text(encoding="utf-8"))
    assert path.name == "ASTOR__HISSE_ROBOTU.json"
    assert data["score"] == 83.93
    assert data["rank"] == 3

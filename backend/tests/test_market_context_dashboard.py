from datetime import date
from pathlib import Path

from backend.app.ui.market_context_dashboard import (
    _process_input,
    _render_daily_archive_summary,
)


class Uploaded:
    def __init__(self, data: bytes):
        self._data = data

    def getvalue(self):
        return self._data


class FakeMetricTarget:
    def __init__(self, parent):
        self.parent = parent

    def metric(self, label, value):
        self.parent.metrics.append((label, value))


class FakeSt:
    def __init__(self):
        self.metrics = []
        self.messages = []

    def metric(self, label, value):
        self.metrics.append((label, value))

    def subheader(self, value):
        self.messages.append(("subheader", value))

    def write(self, value):
        self.messages.append(("write", value))

    def caption(self, value):
        self.messages.append(("caption", value))

    def divider(self):
        self.messages.append(("divider", None))


def test_process_manual_text_uses_service_pipeline(tmp_path):
    from backend.app.market_context.service import MarketContextService

    service = MarketContextService(data_root=tmp_path / "data")

    saved = _process_input(
        service=service,
        input_mode="Metin Yapıştır",
        manual_text="BIST100 pozitif. 13.200 destek, 14.228 direnç.",
        uploaded_file=None,
        source="ICBC",
        document_date="2026-08-03",
        temp_root=tmp_path / "temp",
    )

    assert saved.source == "ICBC"
    assert saved.archive_status == "archived"
    assert (tmp_path / "data" / "market_context_archive" / "2026-08-03" / "daily_manifest.json").exists()


def test_process_txt_upload_uses_temp_file_and_cleans_it(tmp_path):
    from backend.app.market_context.service import MarketContextService

    service = MarketContextService(data_root=tmp_path / "data")
    temp_root = tmp_path / "temp"

    saved = _process_input(
        service=service,
        input_mode="TXT Yükle",
        manual_text="",
        uploaded_file=Uploaded("BIST100 pozitif.".encode("utf-8")),
        source="Gedik",
        document_date="2026-08-03",
        temp_root=temp_root,
    )

    assert saved.input_type == "txt"
    assert not (temp_root / "upload.txt").exists()


def test_process_requires_file_for_upload_modes(tmp_path):
    from backend.app.market_context.service import MarketContextService

    service = MarketContextService(data_root=tmp_path / "data")

    try:
        _process_input(
            service=service,
            input_mode="TXT Yükle",
            manual_text="",
            uploaded_file=None,
            source="ICBC",
            document_date="2026-08-03",
            temp_root=tmp_path / "temp",
        )
    except ValueError as exc:
        assert "Dosya seçilmelidir" in str(exc)
    else:
        raise AssertionError("ValueError bekleniyordu.")


def test_daily_archive_summary_shows_count_and_sources(tmp_path):
    from backend.app.market_context.service import MarketContextService

    service = MarketContextService(data_root=tmp_path / "data")
    service.import_text(
        text="ICBC: BIST100 pozitif.",
        source="ICBC",
        document_date="2026-08-03",
        document_id="doc-1",
    )
    service.import_text(
        text="Gedik: BIST100 temkinli.",
        source="Gedik",
        document_date="2026-08-03",
        document_id="doc-2",
    )

    st = FakeSt()
    _render_daily_archive_summary(
        st,
        service=service,
        document_date="2026-08-03",
    )

    assert ("Bu gün arşivlenen rapor", 2) in st.metrics
    assert any("Gedik" in str(item) and "ICBC" in str(item) for item in st.messages)


def test_ui_module_does_not_reference_trading_score_or_signal():
    source = Path("backend/app/ui/market_context_dashboard.py").read_text(encoding="utf-8").casefold()

    forbidden = (
        "technical_score",
        "candidate_rank",
        "buy_signal",
        "sell_signal",
        "prebreakout_score",
    )

    for token in forbidden:
        assert token not in source

from datetime import date

from backend.app.ui.batch_historical_export_ui import (
    execute_batch_export,
    render_batch_historical_export_panel,
)


class FakeStreamlit:
    def __init__(self, *, pressed=True, include_zip=False):
        self.pressed = pressed
        self.include_zip = include_zip
        self.calls = []

    def _add(self, name, *args):
        self.calls.append((name, args))

    def subheader(self, body): self._add("subheader", body)
    def caption(self, body): self._add("caption", body)
    def selectbox(self, label, options, **kwargs):
        self._add("selectbox", label, options)
        return options[0]
    def date_input(self, label, value=None, **kwargs):
        self._add("date_input", label, value)
        return value
    def checkbox(self, label, value=False, **kwargs):
        self._add("checkbox", label, value)
        return self.include_zip
    def button(self, label, **kwargs):
        self._add("button", label)
        return self.pressed
    def info(self, body): self._add("info", body)
    def success(self, body): self._add("success", body)
    def error(self, body): self._add("error", body)
    def metric(self, label, value, delta=None): self._add("metric", label, value, delta)
    def download_button(self, label, data, file_name, mime, **kwargs):
        self._add("download_button", label, file_name, mime)


def test_execute_batch_export_combined_csv():
    def scan_day(cut_date, universe):
        return [{"Hisse": "TRMET", "Sıra": 20}]

    out = execute_batch_export(
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 2),
        universe="BIST100",
        scan_day=scan_day,
    )
    assert out.processed_days == 2
    assert out.total_rows == 2
    assert "Kesim Tarihi" in out.combined_csv
    assert "TRMET" in out.combined_csv


def test_execute_batch_export_zip():
    def scan_day(cut_date, universe):
        return [{"Hisse": "AAA"}]

    out = execute_batch_export(
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 1),
        universe="BIST100",
        scan_day=scan_day,
        include_daily_zip=True,
    )
    assert out.daily_zip_bytes is not None
    assert out.daily_zip_filename is not None
    assert out.daily_zip_filename.endswith(".zip")


def test_render_button_basilmazsa_none():
    st = FakeStreamlit(pressed=False)
    result = render_batch_historical_export_panel(
        st,
        scan_day=lambda d, u: [],
        default_start_date=date(2026, 6, 29),
        default_end_date=date(2026, 7, 29),
    )
    assert result is None


def test_render_combined_download():
    st = FakeStreamlit()

    result = render_batch_historical_export_panel(
        st,
        scan_day=lambda d, u: [{"Hisse": "AAA"}],
        default_start_date=date(2026, 7, 1),
        default_end_date=date(2026, 7, 1),
    )

    assert result is not None
    names = [name for name, _ in st.calls]
    assert "success" in names
    assert "download_button" in names


def test_render_zip_download():
    st = FakeStreamlit(include_zip=True)

    render_batch_historical_export_panel(
        st,
        scan_day=lambda d, u: [{"Hisse": "AAA"}],
        default_start_date=date(2026, 7, 1),
        default_end_date=date(2026, 7, 1),
    )

    downloads = [args for name, args in st.calls if name == "download_button"]
    assert len(downloads) == 2


def test_render_bos_sonuc_info():
    st = FakeStreamlit()

    result = render_batch_historical_export_panel(
        st,
        scan_day=lambda d, u: [],
        default_start_date=date(2026, 7, 1),
        default_end_date=date(2026, 7, 1),
    )

    assert result is not None
    assert result.total_rows == 0
    assert any(name == "info" for name, _ in st.calls)

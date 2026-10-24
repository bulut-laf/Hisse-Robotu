from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Callable, Protocol

from backend.app.history.batch_historical_export import (
    BatchReplayRequest,
    default_combined_filename,
    default_zip_filename,
    run_batch_replay,
    rows_to_csv_text,
    write_daily_zip,
)


class StreamlitLike(Protocol):
    def subheader(self, body: str) -> Any: ...
    def caption(self, body: str) -> Any: ...
    def selectbox(self, label: str, options: list[str], **kwargs: Any) -> Any: ...
    def date_input(self, label: str, value: Any = None, **kwargs: Any) -> Any: ...
    def checkbox(self, label: str, value: bool = False, **kwargs: Any) -> Any: ...
    def button(self, label: str, **kwargs: Any) -> bool: ...
    def info(self, body: str) -> Any: ...
    def success(self, body: str) -> Any: ...
    def error(self, body: str) -> Any: ...
    def metric(self, label: str, value: Any, delta: Any | None = None) -> Any: ...
    def download_button(self, label: str, data: Any, file_name: str, mime: str, **kwargs: Any) -> Any: ...


ScanDay = Callable[[date, str], Any]


@dataclass(frozen=True)
class BatchHistoricalUiResult:
    processed_days: int
    total_rows: int
    combined_filename: str
    combined_csv: str
    daily_zip_filename: str | None = None
    daily_zip_bytes: bytes | None = None


def execute_batch_export(
    *,
    start_date: date,
    end_date: date,
    universe: str,
    scan_day: ScanDay,
    include_daily_zip: bool = False,
) -> BatchHistoricalUiResult:
    request = BatchReplayRequest(
        start_date=start_date,
        end_date=end_date,
        universe=universe,
    )
    result = run_batch_replay(request, scan_day=scan_day)
    combined_csv = "\ufeff" + rows_to_csv_text(result.combined_rows)

    zip_name = None
    zip_bytes = None

    if include_daily_zip:
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as temp_dir:
            path = write_daily_zip(
                result,
                Path(temp_dir) / default_zip_filename(request),
            )
            zip_name = path.name
            zip_bytes = path.read_bytes()

    return BatchHistoricalUiResult(
        processed_days=result.processed_days,
        total_rows=result.total_rows,
        combined_filename=default_combined_filename(request),
        combined_csv=combined_csv,
        daily_zip_filename=zip_name,
        daily_zip_bytes=zip_bytes,
    )


def render_batch_historical_export_panel(
    st: StreamlitLike,
    *,
    scan_day: ScanDay,
    default_start_date: date,
    default_end_date: date,
    universe_options: tuple[str, ...] = ("BIST100", "BIST Tüm"),
) -> BatchHistoricalUiResult | None:
    st.subheader("Toplu Tarihsel Tarama")
    st.caption(
        "Seçilen tarih aralığındaki işlem günlerini otomatik çalıştırır ve "
        "tüm kesimleri tek birleşik CSV olarak dışa aktarır."
    )

    universe = st.selectbox(
        "Toplu tarama evreni",
        options=list(universe_options),
    )
    start_date = st.date_input(
        "Başlangıç tarihi",
        value=default_start_date,
    )
    end_date = st.date_input(
        "Bitiş tarihi",
        value=default_end_date,
    )
    include_zip = st.checkbox(
        "Günlük CSV'leri ayrıca ZIP olarak hazırla",
        value=False,
    )

    if not st.button("Toplu tarihsel taramayı başlat"):
        return None

    if end_date < start_date:
        st.error("Bitiş tarihi başlangıç tarihinden önce olamaz.")
        return None

    try:
        output = execute_batch_export(
            start_date=start_date,
            end_date=end_date,
            universe=str(universe),
            scan_day=scan_day,
            include_daily_zip=include_zip,
        )
    except Exception as exc:
        st.error(f"Toplu tarihsel tarama tamamlanamadı: {exc}")
        return None

    st.success("Toplu tarihsel tarama tamamlandı.")
    st.metric("İşlenen gün", output.processed_days)
    st.metric("Toplam satır", output.total_rows)

    st.download_button(
        "Birleşik CSV indir",
        data=output.combined_csv,
        file_name=output.combined_filename,
        mime="text/csv",
    )

    if output.daily_zip_bytes is not None and output.daily_zip_filename is not None:
        st.download_button(
            "Günlük CSV ZIP indir",
            data=output.daily_zip_bytes,
            file_name=output.daily_zip_filename,
            mime="application/zip",
        )

    if output.total_rows == 0:
        st.info("Seçilen tarih aralığında export edilecek aday bulunamadı.")

    return output

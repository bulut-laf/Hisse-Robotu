from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from io import BytesIO
from pathlib import Path
import tempfile
import zipfile

from backend.app.history.batch_historical_export import (
    BatchReplayRequest,
    default_combined_filename,
    default_zip_filename,
    rows_to_csv_text,
    write_daily_zip,
)
from backend.app.history.resilient_batch_replay import (
    BatchProgress,
    ResilientBatchReplayResult,
    run_resilient_batch_replay,
)
from backend.app.ui.momentum_batch_history_integration import (
    ReusableMomentumBatchScanner,
)


@dataclass(frozen=True)
class Sprint136UiOutput:
    processed_days: int
    failed_days: int
    total_rows: int
    combined_filename: str
    combined_csv: str
    failure_csv: str | None
    daily_zip_filename: str | None
    daily_zip_bytes: bytes | None


def _failure_csv(result: ResilientBatchReplayResult) -> str | None:
    if not result.failures:
        return None
    lines = ["Kesim Tarihi,Hata"]
    for failure in result.failures:
        safe = failure.error.replace('"', '""')
        lines.append(f'{failure.cut_date.isoformat()},"{safe}"')
    return "\ufeff" + "\r\n".join(lines) + "\r\n"


def execute_resilient_batch_export(
    *,
    start_date: date,
    end_date: date,
    universe: str,
    scanner: ReusableMomentumBatchScanner,
    include_daily_zip: bool = False,
    on_progress=None,
) -> Sprint136UiOutput:
    request = BatchReplayRequest(
        start_date=start_date,
        end_date=end_date,
        universe=universe,
    )
    result = run_resilient_batch_replay(
        request,
        scan_day=scanner.scan_day,
        on_progress=on_progress,
        continue_on_error=True,
    )
    batch = result.batch
    combined_csv = "\ufeff" + rows_to_csv_text(batch.combined_rows)

    zip_name = None
    zip_bytes = None
    if include_daily_zip:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = write_daily_zip(
                batch,
                Path(temp_dir) / default_zip_filename(request),
            )
            zip_name = path.name
            zip_bytes = path.read_bytes()

    return Sprint136UiOutput(
        processed_days=batch.processed_days,
        failed_days=result.failed_days,
        total_rows=batch.total_rows,
        combined_filename=default_combined_filename(request),
        combined_csv=combined_csv,
        failure_csv=_failure_csv(result),
        daily_zip_filename=zip_name,
        daily_zip_bytes=zip_bytes,
    )


def render_sprint136_batch_panel(
    st,
    *,
    minimum_skor: int,
    maksimum_aday: int,
    ozel_semboller: tuple[str, ...],
    internetten_guncelle: bool,
    default_start_date: date,
    default_end_date: date,
):
    st.subheader("Toplu Tarihsel Tarama")
    st.caption(
        "Her işlem günü sırayla çalıştırılır. İlerleme, çalışan tarih ve "
        "günlük sonuç sayısı ekranda gösterilir."
    )

    universe = st.selectbox(
        "Toplu tarama evreni",
        options=["BIST100", "BIST Tüm"],
        key="s136_universe",
    )
    start_date = st.date_input(
        "Başlangıç tarihi",
        value=default_start_date,
        key="s136_start",
    )
    end_date = st.date_input(
        "Bitiş tarihi",
        value=default_end_date,
        key="s136_end",
    )
    include_zip = st.checkbox(
        "Günlük CSV'leri ayrıca ZIP olarak hazırla",
        value=False,
        key="s136_zip",
    )

    if not st.button(
        "Toplu tarihsel taramayı başlat",
        key="s136_start_button",
    ):
        return None

    if end_date < start_date:
        st.error("Bitiş tarihi başlangıç tarihinden önce olamaz.")
        return None

    progress_bar = st.progress(0.0)
    status = st.empty()
    detail = st.empty()

    def on_progress(progress: BatchProgress) -> None:
        if progress.status == "started":
            status.info(
                f"{progress.current_index}/{progress.total_days} · "
                f"{progress.cut_date.isoformat()} çalışıyor..."
            )
            return

        progress_bar.progress(progress.fraction)

        if progress.status == "completed":
            status.info(
                f"{progress.current_index}/{progress.total_days} · "
                f"{progress.cut_date.isoformat()} tamamlandı"
            )
            detail.caption(
                f"{progress.row_count} aday · "
                f"{progress.elapsed_seconds:.1f} sn"
            )
        elif progress.status == "failed":
            status.warning(
                f"{progress.current_index}/{progress.total_days} · "
                f"{progress.cut_date.isoformat()} hata verdi; sonraki güne geçiliyor"
            )
            detail.caption(progress.error or "Bilinmeyen hata")

    scanner = ReusableMomentumBatchScanner(
        minimum_skor=minimum_skor,
        maksimum_aday=maksimum_aday,
        ozel_semboller=ozel_semboller,
        internetten_guncelle=internetten_guncelle,
    )

    output = execute_resilient_batch_export(
        start_date=start_date,
        end_date=end_date,
        universe=str(universe),
        scanner=scanner,
        include_daily_zip=include_zip,
        on_progress=on_progress,
    )

    progress_bar.progress(1.0)
    st.success(
        f"Toplu tarama tamamlandı · {output.processed_days} gün başarılı · "
        f"{output.failed_days} gün hatalı · {output.total_rows} satır"
    )

    st.download_button(
        "Birleşik CSV indir",
        data=output.combined_csv,
        file_name=output.combined_filename,
        mime="text/csv",
        key="s136_combined_download",
    )

    if output.failure_csv is not None:
        st.download_button(
            "Hatalı günler CSV indir",
            data=output.failure_csv,
            file_name="tarihsel_toplu_hatalar.csv",
            mime="text/csv",
            key="s136_failure_download",
        )

    if output.daily_zip_bytes is not None and output.daily_zip_filename is not None:
        st.download_button(
            "Günlük CSV ZIP indir",
            data=output.daily_zip_bytes,
            file_name=output.daily_zip_filename,
            mime="application/zip",
            key="s136_zip_download",
        )

    return output

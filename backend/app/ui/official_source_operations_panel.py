from __future__ import annotations

from datetime import datetime, timedelta

from backend.app.news_center.official_source_operations import (
    OfficialSourceOperationError,
    OfficialSourceOperationKind,
    OfficialSourceOperationStore,
    summarize_official_source_operations,
)


_KIND_LABELS = {
    OfficialSourceOperationKind.PREVIEW_BLOCKED: "ONAY BEKLİYOR",
    OfficialSourceOperationKind.PREVIEW_SUCCESS: "BAŞARILI",
    OfficialSourceOperationKind.PREVIEW_ERROR: "HATA",
    OfficialSourceOperationKind.ARCHIVE_SUCCESS: "ARŞİVLENDİ",
    OfficialSourceOperationKind.ARCHIVE_DUPLICATE: "TEKRAR",
    OfficialSourceOperationKind.ARCHIVE_ERROR: "HATA",
}


def _fmt_datetime(value, timezone) -> str:
    if value is None:
        return "—"
    return value.astimezone(timezone).strftime("%Y-%m-%d %H:%M:%S")


def _kind_label(value) -> str:
    if value is None:
        return "—"
    return _KIND_LABELS.get(value, value.value)


def render_official_source_operations_panel(
    st,
    *,
    source_names,
    timezone,
    store: OfficialSourceOperationStore | None = None,
) -> None:
    store = store or OfficialSourceOperationStore()

    st.subheader("Kaynak operasyon geçmişi")
    st.caption(
        "Bu bölüm yalnız sizin Kaynak Besleme ekranındaki açık işlemlerin yerel "
        "audit geçmişidir. Kaynaklara ping/GET atmaz, otomatik sağlık testi yapmaz "
        "ve bir kaynağın şu anda internette erişilebilir olduğunu iddia etmez."
    )

    try:
        read_result = store.read(limit=500)
    except (OfficialSourceOperationError, OSError, ValueError) as exc:
        st.warning(f"Operasyon geçmişi okunamadı: {exc}")
        return

    records = read_result.records
    summaries = summarize_official_source_operations(records, source_names)

    now = datetime.now(timezone)
    since = now - timedelta(hours=24)
    last_24h = sum(
        record.occurred_at.astimezone(timezone) >= since
        for record in records
    )
    latest_success = next(
        (
            record
            for record in records
            if record.kind
            in {
                OfficialSourceOperationKind.PREVIEW_SUCCESS,
                OfficialSourceOperationKind.ARCHIVE_SUCCESS,
            }
        ),
        None,
    )

    metrics = st.columns(4)
    metrics[0].metric("Okunan operasyon", len(records))
    metrics[1].metric("Son 24 saat", last_24h)
    metrics[2].metric(
        "Son başarılı kullanım",
        _fmt_datetime(
            latest_success.occurred_at if latest_success else None,
            timezone,
        ),
    )
    metrics[3].metric("Geçersiz satır", read_result.invalid_lines)

    if read_result.invalid_lines:
        st.warning(
            "Operasyon günlüğünde okunamayan satırlar var; geçerli kayıtlar "
            "gösterilmeye devam ediyor."
        )

    st.dataframe(
        [
            {
                "Kaynak": summary.source_name,
                "Son önizleme": _fmt_datetime(
                    summary.last_preview_at,
                    timezone,
                ),
                "Önizleme sonucu": _kind_label(summary.last_preview_kind),
                "Son arşiv işlemi": _fmt_datetime(
                    summary.last_archive_at,
                    timezone,
                ),
                "Arşiv sonucu": _kind_label(summary.last_archive_kind),
                "Son başarılı kullanım": _fmt_datetime(
                    summary.last_success_at,
                    timezone,
                ),
            }
            for summary in summaries
        ],
        width="stretch",
        hide_index=True,
    )

    with st.expander("Son operasyon kayıtları", expanded=False):
        if not records:
            st.info("Henüz kaynak operasyon kaydı yok.")
        else:
            st.dataframe(
                [
                    {
                        "Zaman": _fmt_datetime(record.occurred_at, timezone),
                        "Kaynak": record.source_name,
                        "İşlem": _kind_label(record.kind),
                        "Referans": record.source_reference or "—",
                        "Not": record.detail or "—",
                    }
                    for record in records[:50]
                ],
                width="stretch",
                hide_index=True,
            )

    st.caption(f"Yerel audit günlüğü: {store.path}")

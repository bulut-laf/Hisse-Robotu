from __future__ import annotations

from datetime import datetime

from backend.app.analysis.shadow_portfolio import (
    OPEN_STATUS,
    ShadowPortfolioError,
    ShadowPortfolioStore,
)
from backend.app.news_center.archive import NewsArchiveError
from backend.app.news_center.daily_operations import (
    build_daily_news_operations_brief,
    daily_operations_event_rows,
    daily_operations_source_rows,
)
from backend.app.news_center.official_source_operations import (
    OfficialSourceOperationError,
    OfficialSourceOperationStore,
)


def _fmt(value, timezone) -> str:
    if value is None:
        return "—"
    return value.astimezone(timezone).strftime("%Y-%m-%d %H:%M:%S")


def render_daily_news_operations_panel(
    st,
    *,
    archive,
    source_names,
    timezone,
    operation_store: OfficialSourceOperationStore | None = None,
) -> None:
    st.caption(
        "Bu ekran mevcut Haber Merkezi kayıtlarını günlük çalışma masasında "
        "birleştirir. Yeni birleşik skor, fiyat yönü, AL/SAT veya AI yorumu "
        "üretmez; ayrıntılı inceleme için mevcut sekmeler kullanılmaya devam eder."
    )

    selected_date = st.date_input(
        "Operasyon günü",
        value=datetime.now(timezone).date(),
        key="news_center_daily_operations_date",
    )

    errors: list[str] = []
    try:
        events = archive.list_events(limit=5000)
        news = archive.list_news(limit=10000)
    except (NewsArchiveError, OSError, ValueError) as exc:
        st.error(f"Günlük operasyon görünümü arşivi okuyamadı: {exc}")
        return

    store = operation_store or OfficialSourceOperationStore()
    try:
        operations_result = store.read(limit=5000)
    except (OfficialSourceOperationError, OSError, ValueError) as exc:
        errors.append(f"Kaynak operasyon geçmişi: {exc}")
        operations = ()
        invalid_operation_lines = 0
    else:
        operations = operations_result.records
        invalid_operation_lines = operations_result.invalid_lines

    portfolio_symbols: tuple[str, ...] = ()
    try:
        positions = ShadowPortfolioStore().list()
    except ShadowPortfolioError as exc:
        errors.append(f"Gölge portföy: {exc}")
    else:
        portfolio_symbols = tuple(
            item.symbol
            for item in positions
            if item.status == OPEN_STATUS
        )

    try:
        brief = build_daily_news_operations_brief(
            events,
            news,
            operations,
            selected_date=selected_date,
            official_source_names=source_names,
            portfolio_symbols=portfolio_symbols,
            as_of=datetime.now(timezone),
            timezone=timezone,
        )
    except ValueError as exc:
        st.error(str(exc))
        return

    metrics_1 = st.columns(6)
    metrics_1[0].metric("Olay", brief.event_count)
    metrics_1[1].metric("Haber", brief.news_count)
    metrics_1[2].metric("Önem ≥80", brief.high_importance_event_count)
    metrics_1[3].metric("KAP olayı", brief.kap_event_count)
    metrics_1[4].metric("Hisse", brief.unique_symbol_count)
    metrics_1[5].metric("Portföy teması", len(brief.portfolio_touched_symbols))

    source_names_tuple = tuple(source_names)
    metrics_2 = st.columns(4)
    metrics_2[0].metric(
        "Kullanılan resmî kaynak",
        f"{brief.official_sources_used_count}/{len(source_names_tuple)}",
    )
    metrics_2[1].metric("Kaynak operasyonu", brief.source_operation_count)
    metrics_2[2].metric("Operasyon hatası", brief.source_operation_error_count)
    metrics_2[3].metric("Birincil haber", brief.tier1_news_count)

    st.caption(
        "En son arşivlenmiş yayın: "
        f"{_fmt(brief.latest_news_published_at, timezone)} · "
        "En son başarılı kaynak kullanımı: "
        f"{_fmt(brief.latest_source_success_at, timezone)}. "
        "Bu bilgiler dış dünyadaki gerçek zamanlı haber tazeliği garantisi değildir."
    )

    if brief.portfolio_touched_symbols:
        st.caption(
            "Gölge Portföy teması: "
            + ", ".join(brief.portfolio_touched_symbols)
            + ". Bu yalnız mevcut olay-hisse bağlantısının kesişimidir; yön tahmini değildir."
        )

    st.subheader("Günün öncelikli olayları")
    if brief.priority_events:
        st.dataframe(
            daily_operations_event_rows(brief, timezone=timezone),
            width="stretch",
            hide_index=True,
        )
    else:
        st.info("Seçilen gün için arşivlenmiş piyasa olayı bulunamadı.")

    st.subheader("Resmî kaynak günlük görünümü")
    st.dataframe(
        daily_operations_source_rows(brief, timezone=timezone),
        width="stretch",
        hide_index=True,
    )
    st.caption(
        "Kaynak satırları yalnız o gün arşivlenen haberler ve kullanıcının açıkça "
        "başlattığı kaynak operasyonlarından oluşur. Bu tablo kaynaklara yeni ağ "
        "isteği göndermez."
    )

    if invalid_operation_lines:
        st.warning(
            f"Operasyon günlüğünde {invalid_operation_lines} okunamayan satır var; "
            "geçerli kayıtlar kullanıldı."
        )

    for error in errors:
        st.caption(f"• {error}")

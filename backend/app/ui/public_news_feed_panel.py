from __future__ import annotations

from datetime import timezone

from backend.app.news_center.ai_news_summary import (
    AINewsSummaryError,
    NewsSummaryInput,
    summarize_public_news,
)
from backend.app.news_center.archive import NewsArchive
from backend.app.news_center.feed_ingestion import FeedIngestionError, FeedIngestionService
from backend.app.news_center.public_news_feed import (
    PUBLIC_NEWS_DEFAULT_TIMEOUT_SECONDS,
    PublicNewsFeedError,
    fetch_public_news_feed,
    public_news_feed_specs,
)


_PREVIEW_KEY = "news_center_public_feed_preview_v1"
_NETWORK_KEY = "news_center_public_feed_network_enabled_v1"
_TIMEOUT_KEY = "news_center_public_feed_timeout_v1"
_SUMMARY_KEY = "news_center_public_feed_ai_summary_v1"
_SUMMARY_SOURCE_ROWS_KEY = "news_center_public_feed_ai_summary_sources_v1"
_PREVIEW_RENDER_LIMIT = 20


def _preview_rows(previews, tz):
    rows = []
    for channel_name, preview in previews:
        item = preview.item
        rows.append(
            {
                "Yayın zamanı": item.published_at.astimezone(tz).strftime("%Y-%m-%d %H:%M"),
                "Kanal": channel_name,
                "Kaynak": preview.source.canonical_name,
                "Başlık": item.headline,
                "Tür": item.event_type.value,
                "Kapsam": item.market_scope.value,
                "Sektör": ", ".join(item.sectors) or "—",
                "Durum": (
                    "ARŞİVDE"
                    if preview.duplicate and preview.existing_news_id
                    else "AYNI AKIŞTA TEKRAR"
                    if preview.duplicate
                    else "YENİ"
                ),
            }
        )
    return rows


def _summary_inputs(previews):
    inputs = []
    source_rows = []
    for index, (channel_name, preview) in enumerate(
        ((channel_name, preview) for channel_name, preview in previews if not preview.duplicate),
        start=1,
    ):
        item = preview.item
        source_id = f"N{index:03d}"
        inputs.append(
            NewsSummaryInput(
                source_id=source_id,
                channel_name=channel_name,
                source_name=preview.source.canonical_name,
                published_at=item.published_at,
                headline=item.headline,
                body=item.body,
                event_type=item.event_type.value,
                market_scope=item.market_scope.value,
                sectors=item.sectors,
            )
        )
        source_rows.append(
            {
                "Kimlik": source_id,
                "Kanal": channel_name,
                "Kaynak": preview.source.canonical_name,
                "Başlık": item.headline,
            }
        )
    return tuple(inputs), source_rows


def _render_ai_summary(st, result, source_rows) -> None:
    output = result.output
    st.markdown("#### AI Toplu Haber Özeti")
    st.caption(
        f"Sağlayıcı: {result.provider} · Model: {result.model} · "
        f"Özetlenen yeni RSS kaydı: {result.input_count} · Süre: {result.elapsed_seconds:.1f} sn"
    )
    st.info(
        "Bu bölüm yalnız haber akışını özetler ve önceliklendirir. Teknik analiz skoru, "
        "AL/SAT, hedef, stop veya fiyat yönü üretmez."
    )
    st.write(output["market_summary"])

    developments = output.get("key_developments", [])
    if developments:
        st.markdown("**Öne çıkan gelişmeler**")
        used_ids = set()
        for index, item in enumerate(developments, start=1):
            importance = item["importance"]
            st.markdown(f"**{index}. [{importance}] {item['title']}**")
            st.write(item["summary"])
            st.caption(f"Neden önemli: {item['why_it_matters']}")
            source_ids = item.get("source_ids", [])
            used_ids.update(source_ids)
            st.caption("Kaynak kayıtları: " + ", ".join(source_ids))

        selected_rows = [row for row in source_rows if row["Kimlik"] in used_ids]
        if selected_rows:
            with st.expander("Özette kullanılan RSS kayıtları"):
                st.dataframe(selected_rows, width="stretch", hide_index=True)

    themes = output.get("themes", [])
    if themes:
        st.markdown("**Ana temalar**")
        for item in themes:
            st.markdown(f"- {item}")

    watch_items = output.get("watch_items", [])
    if watch_items:
        st.markdown("**İzlenecek teyit/veri başlıkları**")
        for item in watch_items:
            st.markdown(f"- {item}")


def render_public_news_feed_panel(st, archive: NewsArchive, timezone_info) -> None:
    st.subheader("Halka Açık Haber Akışı — V1.1")
    st.caption(
        "İlk kontrollü canlı akış: Anadolu Ajansı Ekonomi + TRT Haber Ekonomi + "
        "TRT Haber Son Dakika RSS. Yalnız RSS özetleri okunur; haber sayfaları topluca "
        "scrape edilmez. Yenileme kullanıcı tarafından başlatılır. Teknik skor, AL/SAT "
        "veya fiyat yönü üretilmez. Sprint-181 ile arşiv öncesinde yalnız kullanıcı "
        "başlatmalı toplu AI haber özeti üretilebilir."
    )

    specs = public_news_feed_specs()
    metrics = st.columns(4)
    metrics[0].metric("Halka açık kaynak", len({item.canonical_name for item in specs}))
    metrics[1].metric("RSS kanalı", len(specs))
    metrics[2].metric("Arka plan polling", "YOK")
    metrics[3].metric("Aktarım", "AÇIK ONAY")

    st.dataframe(
        [
            {
                "Kanal": item.channel_name,
                "Kaynak": item.canonical_name,
                "RSS": item.feed_url,
            }
            for item in specs
        ],
        width="stretch",
        hide_index=True,
    )

    network_enabled = st.checkbox(
        "Bu yenileme için halka açık RSS kaynaklarına bağlan",
        key=_NETWORK_KEY,
    )
    timeout_seconds = int(
        st.number_input(
            "RSS zaman aşımı (sn)",
            min_value=1,
            max_value=30,
            value=PUBLIC_NEWS_DEFAULT_TIMEOUT_SECONDS,
            step=1,
            key=_TIMEOUT_KEY,
        )
    )

    if st.button("Halka açık akışları önizle", key="news_center_public_feed_preview_button"):
        st.session_state[_SUMMARY_KEY] = None
        st.session_state[_SUMMARY_SOURCE_ROWS_KEY] = []
        if not network_enabled:
            st.warning("Halka açık RSS ağı kapalı. Bu yenileme için ağ onayını açın.")
        else:
            ingestion = FeedIngestionService(archive)
            previews = []
            fetched_pairs = []
            errors = []
            fetched_count = 0
            for spec in specs:
                try:
                    result = fetch_public_news_feed(
                        spec,
                        timeout_seconds=timeout_seconds,
                    )
                    fetched_count += len(result.items)
                    fetched_pairs.extend((spec.channel_name, item) for item in result.items)
                except (PublicNewsFeedError, FeedIngestionError, ValueError) as exc:
                    errors.append(f"{spec.channel_name}: {exc}")

            if fetched_pairs:
                try:
                    batch_previews = ingestion.preview_many(
                        [item for _, item in fetched_pairs]
                    )
                    previews = [
                        (channel_name, preview)
                        for (channel_name, _), preview in zip(fetched_pairs, batch_previews)
                    ]
                except (FeedIngestionError, ValueError) as exc:
                    errors.append(f"Haber arşivi önizlemesi: {exc}")

            previews.sort(
                key=lambda pair: pair[1].item.published_at,
                reverse=True,
            )
            st.session_state[_PREVIEW_KEY] = previews
            if previews:
                new_count = sum(not preview.duplicate for _, preview in previews)
                duplicate_count = len(previews) - new_count
                st.success(
                    f"RSS önizlemesi tamamlandı: {fetched_count} kayıt okundu, "
                    f"{new_count} yeni haber bulundu, {duplicate_count} tekrar/arşiv kaydı ayrıldı."
                )
            elif not errors:
                st.info("RSS kaynaklarında işlenebilir haber bulunamadı.")
            for error in errors:
                st.warning(error)

    previews = st.session_state.get(_PREVIEW_KEY, [])
    if previews:
        visible_previews = previews[:_PREVIEW_RENDER_LIMIT]
        st.dataframe(
            _preview_rows(visible_previews, timezone_info),
            width="stretch",
            hide_index=True,
        )
        if len(previews) > len(visible_previews):
            st.caption(
                f"Performans için tabloda yalnız en yeni {len(visible_previews)} kayıt gösteriliyor; "
                f"{len(previews)} kaydın tamamı aktarım ve AI özet hesabında korunuyor."
            )
        new_count = sum(not preview.duplicate for _, preview in previews)
        st.caption(
            f"Önizleme: {len(previews)} kayıt · {new_count} yeni · "
            f"{len(previews) - new_count} arşivde/tekrar."
        )

        summary_inputs, source_rows = _summary_inputs(previews)
        if st.button(
            "Yeni haberleri AI ile topluca özetle",
            key="news_center_public_feed_ai_summary_button",
            disabled=not summary_inputs,
        ):
            try:
                with st.spinner(f"{len(summary_inputs)} yeni RSS kaydı topluca özetleniyor..."):
                    summary_result = summarize_public_news(summary_inputs)
                st.session_state[_SUMMARY_KEY] = summary_result
                st.session_state[_SUMMARY_SOURCE_ROWS_KEY] = source_rows
            except (AINewsSummaryError, ValueError) as exc:
                st.session_state[_SUMMARY_KEY] = None
                st.session_state[_SUMMARY_SOURCE_ROWS_KEY] = []
                st.error(f"AI toplu haber özeti tamamlanamadı: {exc}")

        summary_result = st.session_state.get(_SUMMARY_KEY)
        if summary_result is not None:
            _render_ai_summary(
                st,
                summary_result,
                st.session_state.get(_SUMMARY_SOURCE_ROWS_KEY, []),
            )

        if st.button(
            "Yeni haberleri Haber Merkezi arşivine aktar",
            key="news_center_public_feed_import_button",
            disabled=new_count == 0,
        ):
            ingestion = FeedIngestionService(archive)
            archived = 0
            duplicate = 0
            errors = []
            for _, preview in previews:
                try:
                    result = ingestion.import_preview(preview)
                    if result.archived:
                        archived += 1
                    elif result.duplicate:
                        duplicate += 1
                except (FeedIngestionError, ValueError, RuntimeError) as exc:
                    errors.append(str(exc))

            if archived:
                st.success(
                    f"{archived} yeni halka açık haber arşive aktarıldı. "
                    "Son Dakika ve ilgili Haber Merkezi ekranlarında görüntülenebilir."
                )
            if duplicate:
                st.info(f"{duplicate} kayıt duplicate olduğu için yeniden yazılmadı.")
            for error in errors[:10]:
                st.warning(error)
            if len(errors) > 10:
                st.warning(f"Ek {len(errors) - 10} aktarım hatası daha oluştu.")
            st.session_state[_PREVIEW_KEY] = []
            st.session_state[_SUMMARY_KEY] = None
            st.session_state[_SUMMARY_SOURCE_ROWS_KEY] = []
            if archived and hasattr(st, "rerun"):
                st.rerun()

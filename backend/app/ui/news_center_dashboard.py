from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from backend.app.analysis.shadow_portfolio import (
    OPEN_STATUS,
    ShadowPortfolioError,
    ShadowPortfolioStore,
)
from backend.app.news_center.archive import (
    DuplicateNewsError,
    NewsArchive,
    NewsArchiveError,
)
from backend.app.news_center.classifier import classify_news
from backend.app.news_center.daily_developments import (
    build_daily_developments_brief,
    daily_development_rows,
)
from backend.app.news_center.day_end_summary import (
    build_day_end_summary,
    day_end_development_rows,
)
from backend.app.news_center.last_minute import (
    build_last_minute_feed,
    last_minute_available_sources,
    last_minute_available_symbols,
    last_minute_rows,
)
from backend.app.news_center.archive_view import (
    archive_available_sectors,
    archive_available_sources,
    archive_available_symbols,
    archive_news_rows,
    build_archive_news_view,
)
from backend.app.news_center.feed_ingestion import (
    FeedIngestionService,
    feed_source_statuses,
)
from backend.app.news_center.official_source_health import (
    diagnose_official_source_adapters,
    official_source_adapter_names,
)
from backend.app.news_center.economic_calendar import (
    CATEGORY_LABELS as CALENDAR_CATEGORY_LABELS,
    CalendarCategory,
    CalendarImportance,
    DuplicateCalendarEntryError,
    EconomicCalendarError,
    EconomicCalendarStore,
    IMPORTANCE_LABELS as CALENDAR_IMPORTANCE_LABELS,
    calendar_rows,
    create_calendar_entry,
    select_calendar_entries,
)
from backend.app.news_center.impact import assess_event_impact, impact_rows
from backend.app.news_center.kap_flow import (
    build_kap_flow,
    kap_available_symbols,
    kap_flow_rows,
)
from backend.app.news_center.symbol_news import (
    build_symbol_news_brief,
    symbol_news_available_symbols,
    symbol_news_rows,
)
from backend.app.news_center.portfolio_impact import (
    PortfolioMember,
    build_portfolio_impact_radar,
    portfolio_impact_rows,
    portfolio_symbol_summary_rows,
)
from backend.app.news_center.sector_impact import (
    build_sector_impact_map,
    sector_event_rows,
    sector_summary_rows,
)
from backend.app.news_center.models import (
    EventType,
    MarketScope,
    SourceTier,
)
from backend.app.news_center.service import (
    EventGroupingReviewRequired,
    ManualNewsRequest,
    NewsCenterService,
    NewsCenterServiceError,
    event_rows,
    news_rows,
)
from backend.app.news_center.v1_release import (
    NEWS_CENTER_V1_VERSION,
)
from backend.app.ui.official_source_feed_renderer import (
    render_official_source_feed_blocks,
)
from backend.app.ui.official_source_operations_panel import (
    render_official_source_operations_panel,
)
from backend.app.ui.daily_news_operations_panel import (
    render_daily_news_operations_panel,
)
from backend.app.ui.public_news_feed_panel import (
    render_public_news_feed_panel,
)


ISTANBUL = ZoneInfo("Europe/Istanbul")

SOURCE_TIER_LABELS = {
    "Birinci seviye — Resmî/birincil kaynak": SourceTier.TIER_1_OFFICIAL,
    "İkinci seviye — Büyük finans yayını": SourceTier.TIER_2_MAJOR_FINANCIAL,
    "Diğer doğrulanmış kaynak": SourceTier.OTHER_VERIFIED,
    "Manuel / sınıflandırılmamış": SourceTier.MANUAL,
}

EVENT_TYPE_LABELS = {
    "Para politikası": EventType.PARA_POLITIKASI,
    "Enflasyon": EventType.ENFLASYON,
    "Büyüme": EventType.BUYUME,
    "İstihdam": EventType.ISTIHDAM,
    "Faiz": EventType.FAIZ,
    "Döviz": EventType.DOVIZ,
    "Emtia": EventType.EMTIA,
    "Regülasyon": EventType.REGULASYON,
    "KAP açıklaması": EventType.KAP_ACIKLAMASI,
    "Finansal sonuçlar": EventType.FINANSAL_SONUCLAR,
    "Temettü": EventType.TEMETTU,
    "Sermaye işlemi": EventType.SERMAYE_ISLEMI,
    "Borçlanma / finansman": EventType.BORCLANMA_FINANSMAN,
    "Sektör": EventType.SEKTOR,
    "Jeopolitik": EventType.JEOPOLITIK,
    "Diğer": EventType.DIGER,
}

SCOPE_LABELS = {
    "Küresel": MarketScope.GLOBAL,
    "Türkiye makro": MarketScope.TURKEY_MACRO,
    "BIST geneli": MarketScope.BIST_WIDE,
    "Sektör": MarketScope.SECTOR,
    "Şirket": MarketScope.COMPANY,
    "Diğer": MarketScope.OTHER,
}


def _comma_values(value: str) -> tuple[str, ...]:
    return tuple(
        item.strip()
        for item in str(value or "").split(",")
        if item.strip()
    )


def _combine(local_date, local_time) -> datetime:
    return datetime.combine(
        local_date,
        local_time,
        tzinfo=ISTANBUL,
    )


def _importance_detail(st, event) -> None:
    breakdown = event.importance_breakdown
    st.caption(
        "Önem bileşenleri: "
        f"Kaynak {breakdown.source_reliability}/30 · "
        f"Kapsam {breakdown.market_scope}/25 · "
        f"Olay {breakdown.event_significance}/30 · "
        f"Zaman {breakdown.time_sensitivity}/15"
    )


def _render_summary_metrics(st, events, news) -> None:
    high_importance = sum(item.importance_score >= 80 for item in events)
    multi_source = sum(len(item.news_ids) >= 2 for item in events)
    columns = st.columns(4)
    columns[0].metric("Olay", len(events))
    columns[1].metric("Haber", len(news))
    columns[2].metric("Önem ≥80", high_importance)
    columns[3].metric("Çok kaynaklı olay", multi_source)


def render_news_center_dashboard(st) -> None:
    st.header("Piyasa Haber, Olay ve Etki Merkezi")
    st.caption(
        f"Haber Merkezi V{NEWS_CENTER_V1_VERSION} kararlı çekirdek — Sprint-178 Kararlı Sürüm ve Tam Sistem Doğrulaması. "
        "Sprint-180 Haber Merkezi V1.1 Halka Açık Haber Akışı temeli aktiftir; AA Ekonomi, TRT Haber Ekonomi ve TRT Haber Son Dakika RSS kanalları kullanıcı başlatmalı önizleme + açık arşiv onayıyla eklenir. "
        "Sprint-177 Günlük Haber Merkezi Operasyon Ekranı korunur. "
        "Sprint-176 kaynak operasyon geçmişi ve son başarılı kullanım tanılaması korunur. "
        "Sprint-175 ortak Kaynak Besleme rendererı korunur. "
        "Sprint-174 yapısal sağlık tanılaması ve Sprint-173 ortak güvenlik çekirdeği korunur. "
        "Sprint-173 ortak güvenlik çekirdeği ve yedi kontrollü resmî adapter korunur. "
        "Yedi kontrollü resmî adapterin dış davranışı korunur. "
        "Sprint-169 KAP, TCMB, TÜİK ve SPK adapterleri korunur. "
        "Sprint-167 KAP ve TCMB adapterleri korunur. "
        "Sprint-166 KAP adapteri korunur. "
        "Sprint-165 Güvenilir Kaynak Besleme Hazırlık Katmanı korunur. "
        "Sprint-164 Haber Arşivi Gelişmiş Filtreleme ve Geçmişe Erişim korunur. "
        "Sprint-163 Son Dakika Haber Akışı korunur. "
        "Sprint-162 Gün Sonu Haber ve Olay Özeti korunur. "
        "Sprint-161 Hisse Haberleri ve Sembol Bazlı Haber Görünümü korunur. "
        "Sprint-160 KAP Akışı, Sprint-159 Ekonomik Takvim ve Sprint-158 Bugünün Önemli "
        "Gelişmeleri karar ekranı korunur. "
        "Sprint-156 deterministik Sektör Etki Haritası, Sprint-154 Portföy "
        "Etki Radarı ve Sprint-153 etki bağlantıları korunur. "
        "Sprint-152 güvenli olay eşleştirme kuralları korunur. "
        "Bu ekran otomatik polling veya toplu scraping yapmaz. KAP ağına yalnız açık kullanıcı "
        "onayıyla tek bildirim URL'si için bağlanabilir. Otomatik AI değerlendirmesi yapmaz; "
        "Sprint-181 yalnız kullanıcı başlatmalı halka açık RSS toplu özetini arşiv öncesinde üretir. "
        "AI özeti haber önceliklendirmesi içindir; teknik analiz skorlarını ve işlem karar motorunu "
        "doğrudan değiştirmez."
    )

    try:
        archive = NewsArchive()
        service = NewsCenterService(archive)
        events = archive.list_events()
        all_news = archive.list_news()
    except (NewsArchiveError, OSError, ValueError) as exc:
        st.error(str(exc))
        return

    _render_summary_metrics(st, events, all_news)

    (
        daily_operations_tab,
        feed_tab,
        last_minute_tab,
        daily_tab,
        day_end_tab,
        calendar_tab,
        kap_tab,
        symbol_news_tab,
        add_tab,
        event_tab,
        impact_tab,
        sector_tab,
        portfolio_tab,
        news_tab,
    ) = st.tabs(
        (
            "Günlük Operasyon",
            "Kaynak Besleme",
            "Son Dakika",
            "Bugünün Önemli Gelişmeleri",
            "Gün Sonu Özeti",
            "Ekonomik Takvim",
            "KAP Akışı",
            "Hisse Haberleri",
            "Manuel Haber Ekle",
            "Olay Arşivi",
            "Etki Bağlantıları",
            "Sektör Etki Haritası",
            "Portföy Etki Radarı",
            "Haber Arşivi",
        )
    )


    with daily_operations_tab:
        # GUNLUK_HABER_OPERASYONU_V11_ROLE_CLARITY
        st.subheader("Günlük Haber Operasyonu — Sistem ve Görev Akışı")
        st.caption("Haber Merkezi'nin günlük operasyon durumunu ve görev akışını gösterir; yeni haber skoru, teknik skor veya AL/SAT kararı üretmez.")
        render_daily_news_operations_panel(
            st,
            archive=archive,
            source_names=official_source_adapter_names(),
            timezone=ISTANBUL,
        )

    with feed_tab:
        # OFFLINE_HEALTH_V11_ROLE_CLARITY
        st.subheader("Kaynak Sağlığı — Çevrimdışı ve Erişilebilirlik Kontrolü")
        st.caption("Kaynakların erişilebilirlik/çevrimdışı durumunu operasyonel güvenlik için görünür kılar; haber içeriği, önem skoru veya işlem kararı üretmez.")
        # KAYNAK_BESLEME_V11_ROLE_CLARITY
        st.subheader("Kaynak Besleme — Haber Toplama ve Veri Girişi")
        st.caption("Resmî adapterler ve halka açık haber akışını kullanıcı başlatmalı önizleme/onay süreciyle Haber Merkezi arşivine taşır; kaynak operasyon geçmişi bu akışın izlenebilirlik kanıtıdır.")
        st.caption(
            "Sprint-176 kullanıcı tarafından başlatılan kaynak önizleme ve arşiv işlemlerini yerel audit günlüğünde izler; Sprint-175 ortak rendererı, Sprint-174 yapısal sağlık tanılamasını ve Sprint-173 ortak HTTP/güvenlik çekirdeğini korur; otomatik polling yapmaz, "
            "toplu sorgu veya arka plan taraması yapmaz. Ağ erişimi her önizleme isteğinde "
            "ayrı kullanıcı onayı ister. Akış: tek resmî URL → çek → normalize et → dry-run → "
            "açık onay → arşiv. Yeni skor, fiyat yönü, AL/SAT veya AI yorumu üretmez."
        )

        active_adapter_names = official_source_adapter_names()
        feed_statuses = feed_source_statuses((*active_adapter_names,))
        official_count = sum(
            row.tier is SourceTier.TIER_1_OFFICIAL for row in feed_statuses
        )
        feed_metrics = st.columns(4)
        feed_metrics[0].metric("Kayıtlı kaynak", len(feed_statuses))
        feed_metrics[1].metric("Resmî kaynak", official_count)
        feed_metrics[2].metric("Aktif adapter", len(active_adapter_names))
        feed_metrics[3].metric("Ağ erişimi", "İSTEK BAZLI")

        health_statuses = diagnose_official_source_adapters()
        healthy_adapter_count = sum(row.ready for row in health_statuses)
        passed_health_checks = sum(row.passed_count for row in health_statuses)
        total_health_checks = sum(row.check_count for row in health_statuses)

        st.subheader("Resmî adapter yapısal sağlığı")
        st.caption(
            "Bu tanılama yalnız yerel sözleşmeleri kontrol eder; kaynaklara ping/GET "
            "atmaz ve canlı internet erişilebilirliği anlamına gelmez. Canlı kaynak "
            "kontrolü yalnız aşağıdaki tek-URL önizleme akışlarında açık kullanıcı "
            "onayıyla yapılır."
        )
        health_metrics = st.columns(4)
        health_metrics[0].metric(
            "Yapısal sağlık",
            f"{healthy_adapter_count}/{len(health_statuses)}",
        )
        health_metrics[1].metric(
            "Kontroller",
            f"{passed_health_checks}/{total_health_checks}",
        )
        health_metrics[2].metric("Canlı ağ testi", "YOK")
        health_metrics[3].metric("Varsayılan ağ", "KAPALI")

        st.dataframe(
            [
                {
                    "Kaynak": row.canonical_name,
                    "Adapter": row.adapter_name,
                    "Durum": "HAZIR" if row.ready else "HATA",
                    "Kontrol": f"{row.passed_count}/{row.check_count}",
                    "Canlı ağ testi": "Yok",
                }
                for row in health_statuses
            ],
            width="stretch",
            hide_index=True,
        )

        if healthy_adapter_count != len(health_statuses):
            st.warning("Yapısal tanılamada hata bulunan adapterler var.")
            for health_status in health_statuses:
                for issue in health_status.issues:
                    st.caption(f"• {health_status.canonical_name}: {issue}")

        st.dataframe(
            [
                {
                    "Kaynak": row.canonical_name,
                    "Seviye": row.tier.value,
                    "Alan adları": ", ".join(row.domains) or "—",
                    "Adapter": "Açık" if row.adapter_enabled else "Kapalı",
                }
                for row in feed_statuses
            ],
            width="stretch",
            hide_index=True,
        )

        # RESMI_KAYNAK_OPERASYONLARI_V11_ROLE_CLARITY
        st.subheader("Resmî Kaynak Operasyonları — Kontrollü Kaynak Çalıştırma")
        st.caption("KAP, TCMB, TÜİK, SPK, HMB, BIST ve Resmî Gazete gibi tanımlı resmî kaynakların toplama/önizleme/işlem geçmişi akışını yönetir; haber skoru veya AL/SAT kararı üretmez.")
        render_official_source_operations_panel(
            st,
            source_names=active_adapter_names,
            timezone=ISTANBUL,
        )

        render_official_source_feed_blocks(st, archive, ISTANBUL)

        st.divider()
        render_public_news_feed_panel(st, archive, ISTANBUL)

    with last_minute_tab:
        # GUVENILIR_KAYNAKLAR_V11_ROLE_CLARITY
        st.subheader("Güvenilir Kaynaklar — Kaynak Kalitesi ve İzlenebilirlik")
        st.caption("Kaynak güvenilirliği haberin veri kalitesini ve filtrelenebilirliğini destekler; tek başına fiyat yönü, teknik skor veya AL/SAT kararı üretmez.")
        # BREAKING_STREAM_V11_ROLE_CLARITY
        st.subheader("Son Dakika Akışı — Hızlı Haber İzleme")
        st.caption("Haber Merkezi arşivindeki yayınları en yeniden eskiye izler; zaman, önem, güvenilir kaynak, hisse ve Gölge Portföy filtreleriyle operasyonel farkındalık sağlar.")
        st.caption(
            "Bu ekran Haber Merkezi arşivindeki yayınları en yeniden eskiye "
            "gösterir; otomatik internet akışı değildir. Bir haber kaydı bir "
            "satırdır. Bağlı olayın mevcut önem skoru yalnız gösterilir; yeni "
            "bir skor üretmez. Fiyat yönü, AL/SAT, teknik skor veya AI yorumu "
            "üretmez."
        )
    
        last_minute_now = datetime.now(ISTANBUL)
        last_minute_time_options = {
            "Son 1 saat": 1,
            "Son 3 saat": 3,
            "Son 6 saat": 6,
            "Son 24 saat": 24,
            "Son 3 gün": 72,
            "Tüm arşiv": None,
        }
    
        lm_controls_1 = st.columns(3)
        with lm_controls_1[0]:
            lm_time_label = st.selectbox(
                "Zaman aralığı",
                options=tuple(last_minute_time_options),
                index=3,
                key="news_center_last_minute_window",
            )
        with lm_controls_1[1]:
            lm_min_importance = st.selectbox(
                "Asgari önem",
                options=(0, 60, 70, 80, 90),
                index=0,
                key="news_center_last_minute_min_importance",
            )
        with lm_controls_1[2]:
            lm_trusted_only = st.checkbox(
                "Yalnız güvenilir kaynaklar",
                value=True,
                key="news_center_last_minute_trusted_only",
            )
    
        lm_sources = ("Tümü",) + last_minute_available_sources(all_news)
        lm_symbols = ("Tümü",) + last_minute_available_symbols(events)
    
        lm_controls_2 = st.columns(3)
        with lm_controls_2[0]:
            lm_source = st.selectbox(
                "Kaynak",
                options=lm_sources,
                key="news_center_last_minute_source",
            )
        with lm_controls_2[1]:
            lm_symbol = st.selectbox(
                "Hisse",
                options=lm_symbols,
                key="news_center_last_minute_symbol",
            )
        with lm_controls_2[2]:
            lm_portfolio_only = st.checkbox(
                "Yalnız Gölge Portföy",
                value=False,
                key="news_center_last_minute_portfolio_only",
            )
    
        lm_errors: list[str] = []
        lm_portfolio_symbols: tuple[str, ...] = ()
        try:
            lm_positions = ShadowPortfolioStore().list()
        except ShadowPortfolioError as exc:
            lm_errors.append(f"Gölge portföy: {exc}")
        else:
            lm_portfolio_symbols = tuple(
                item.symbol
                for item in lm_positions
                if item.status == OPEN_STATUS
            )
    
        try:
            lm_brief = build_last_minute_feed(
                events,
                all_news,
                now=last_minute_now,
                lookback_hours=last_minute_time_options[lm_time_label],
                min_importance=int(lm_min_importance),
                source_filter="" if lm_source == "Tümü" else lm_source,
                symbol_filter="" if lm_symbol == "Tümü" else lm_symbol,
                portfolio_symbols=lm_portfolio_symbols,
                portfolio_only=lm_portfolio_only,
                trusted_only=lm_trusted_only,
            )
        except ValueError as exc:
            st.error(str(exc))
        else:
            lm_metrics = st.columns(6)
            lm_metrics[0].metric("Haber", lm_brief.news_count)
            lm_metrics[1].metric("Olay", lm_brief.unique_event_count)
            lm_metrics[2].metric("Birincil", lm_brief.tier1_news_count)
            lm_metrics[3].metric("KAP", lm_brief.kap_news_count)
            lm_metrics[4].metric("Hisse bağlantılı", lm_brief.symbol_news_count)
            lm_metrics[5].metric("Portföy teması", lm_brief.portfolio_news_count)
    
            if lm_brief.latest_published_at is not None:
                st.caption(
                    "En son arşivlenmiş yayın: "
                    + lm_brief.latest_published_at.astimezone(ISTANBUL).strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                    + ". Bu zaman, dış dünyadaki gerçek zamanlı haber akışının "
                    "tazelik garantisi değildir."
                )
            if lm_brief.unlinked_event_count:
                st.caption(
                    f"{lm_brief.unlinked_event_count} kaydın bağlı olayı bulunamadı; "
                    "bu kayıtlar için önem, hisse veya sektör bilgisi uydurulmadı."
                )
    
            if lm_brief.items:
                st.dataframe(
                    last_minute_rows(lm_brief),
                    width="stretch",
                    hide_index=True,
                )
            else:
                st.info("Seçilen filtrelerde Son Dakika kaydı bulunamadı.")
    
        for note in lm_errors:
            st.caption(f"• {note}")
    with daily_tab:
        # COKLU_KAYNAK_BIRLESTIRME_V11_ROLE_CLARITY
        st.subheader("Çoklu Kaynak / Birleştirme — Aynı Olayı Tek Bağlamda Toplama")
        st.caption("Aynı olaya ait birden fazla kaydı duplicate/birleştirme kurallarıyla tek olay bağlamında toplar; orijinal kaynak izi korunur.")
        st.caption(
            "Bu görünüm yeni bir skor üretmez. Mevcut deterministik 0–100 "
            "olay önem skorunu kullanır; eşitliklerde birincil kaynak, çoklu "
            "kaynak, portföy teması ve olay zamanı yalnız sıralama desteğidir. "
            "Fiyat yönü veya AL/SAT kararı değildir."
        )
        control_columns = st.columns(2)
        with control_columns[0]:
            # BUGUNUN_ONEMLI_GELISMELERI_V11_ROLE_CLARITY
            st.subheader("Bugünün Önemli Gelişmeleri — Günlük Olay Öncelik Özeti")
            st.caption(
                "Seçilen gündeki olayları mevcut 0–100 önem skoruna göre süzer ve önceliklendirir; "
                "birincil kaynak, çoklu kaynak, portföy teması ve zaman yalnız eşit önem durumunda sıralama desteğidir."
            )
            st.info(
                "Akış: günlük haber/olay → mevcut önem skoru → etki bağlantıları → sektör/hisse/portföy teması → kullanıcı özeti. "
                "Bu ekran yeni skor, fiyat yönü, teknik skor, AI değerlendirmesi veya AL/SAT kararı üretmez."
            )
            selected_day = st.date_input(
                "Değerlendirme günü",
                value=datetime.now(ISTANBUL).date(),
                key="news_center_daily_developments_date",
            )
        with control_columns[1]:
            min_importance = st.selectbox(
                "Asgari önem",
                options=(0, 60, 70, 80, 90),
                index=2,
                key="news_center_daily_developments_min_importance",
            )

        daily_news_by_event = {}
        daily_errors: list[str] = []
        for item in events:
            if item.occurred_at.astimezone(ISTANBUL).date() != selected_day:
                continue
            try:
                daily_news_by_event[item.event_id] = archive.list_news_for_event(
                    item.event_id
                )
            except NewsArchiveError as exc:
                daily_errors.append(f"{item.title}: {exc}")

        daily_members: tuple[PortfolioMember, ...] = ()
        try:
            daily_shadow_positions = ShadowPortfolioStore().list()
        except ShadowPortfolioError as exc:
            daily_errors.append(f"Gölge portföy: {exc}")
        else:
            daily_members = tuple(
                PortfolioMember(
                    symbol=item.symbol,
                    sector=getattr(item, "sector", "") or "",
                )
                for item in daily_shadow_positions
                if item.status == OPEN_STATUS
            )

        daily_brief = build_daily_developments_brief(
            events,
            daily_news_by_event,
            selected_date=selected_day,
            min_importance=int(min_importance),
            portfolio_members=daily_members,
        )
        daily_columns = st.columns(5)
        daily_columns[0].metric("Gelişme", daily_brief.total_event_count)
        daily_columns[1].metric("Önem ≥80", daily_brief.high_importance_count)
        daily_columns[2].metric("Birincil kaynak", daily_brief.tier1_event_count)
        daily_columns[3].metric("Çok kaynaklı", daily_brief.multi_source_event_count)
        daily_columns[4].metric(
            "Portföye temas", daily_brief.portfolio_touched_event_count
        )

        if not daily_brief.developments:
            st.info(
                "Seçilen gün ve önem eşiğinde arşivlenmiş gelişme bulunamadı."
            )
        else:
            st.dataframe(
                daily_development_rows(daily_brief),
                width="stretch",
                hide_index=True,
            )
            st.caption(
                "Portföy teması yalnız mevcut deterministik etki bağlantılarıyla "
                "açık Gölge Portföy pozisyonlarının kesişimidir; yön tahmini değildir."
            )

        for note in daily_errors:
            st.caption(f"• {note}")


    with day_end_tab:
        # EOD_SUMMARY_V11_ROLE_CLARITY
        st.subheader("Gün Sonu Özeti — Günlük Haber/Olay Kapanışı")
        st.caption("Seçilen günün olaylarını; önem, KAP, hisse/sektör, açık Gölge Portföy teması ve ekonomik takvim metriklerini ayrı ayrı kapanış özeti olarak toplar.")
        st.caption(
            "Sprint-162 gün sonu görünümü yeni bir birleşik skor üretmez. "
            "Mevcut olay önem skoru, doğrulanmış KAP kayıtları, hisse/sektör "
            "bağlantıları, açık Gölge Portföy kesişimi ve ekonomik takvim "
            "metrikleri ayrı ayrı özetlenir. Fiyat yönü, AL/SAT, teknik skor "
            "veya AI yorumu üretmez."
        )
        day_end_date = st.date_input(
            "Gün sonu tarihi",
            value=datetime.now(ISTANBUL).date(),
            key="news_center_day_end_date",
        )
    
        day_end_errors: list[str] = []
        day_end_members: tuple[PortfolioMember, ...] = ()
        try:
            day_end_positions = ShadowPortfolioStore().list()
        except ShadowPortfolioError as exc:
            day_end_errors.append(f"Gölge portföy: {exc}")
        else:
            day_end_members = tuple(
                PortfolioMember(
                    symbol=item.symbol,
                    sector=getattr(item, "sector", "") or "",
                )
                for item in day_end_positions
                if item.status == OPEN_STATUS
            )
    
        try:
            day_end_calendar_entries = EconomicCalendarStore().list_day(day_end_date)
        except (EconomicCalendarError, OSError, ValueError) as exc:
            day_end_errors.append(f"Ekonomik takvim: {exc}")
            day_end_calendar_entries = ()
    
        try:
            day_end_summary = build_day_end_summary(
                events,
                all_news,
                day_end_calendar_entries,
                selected_date=day_end_date,
                portfolio_members=day_end_members,
            )
        except ValueError as exc:
            st.error(str(exc))
        else:
            first_metrics = st.columns(4)
            first_metrics[0].metric("Piyasa olayı", day_end_summary.total_event_count)
            first_metrics[1].metric(
                "Önem ≥80", day_end_summary.high_importance_event_count
            )
            first_metrics[2].metric(
                "Gün içi haber", day_end_summary.news_published_count
            )
            first_metrics[3].metric("KAP", day_end_summary.kap_disclosure_count)
    
            second_metrics = st.columns(4)
            second_metrics[0].metric("Hisse", day_end_summary.unique_symbol_count)
            second_metrics[1].metric("Sektör", day_end_summary.sector_count)
            second_metrics[2].metric(
                "Portföy teması", day_end_summary.affected_portfolio_symbol_count
            )
            second_metrics[3].metric("Takvim", day_end_summary.calendar_event_count)
    
            st.caption(
                "Kaynak teyidi: "
                f"{day_end_summary.tier1_event_count} birincil kaynaklı olay · "
                f"{day_end_summary.multi_source_event_count} çok kaynaklı olay. "
                "Takvim: "
                f"{day_end_summary.calendar_high_critical_count} yüksek/kritik · "
                f"{day_end_summary.calendar_announced_count} açıklanan · "
                f"{day_end_summary.calendar_waiting_count} sonuç beklenen."
            )
    
            if day_end_summary.top_sectors:
                st.caption(
                    "Öne çıkan sektör gündemi: "
                    + ", ".join(day_end_summary.top_sectors)
                )
            if day_end_summary.affected_portfolio_symbols:
                st.caption(
                    "Açık Gölge Portföy teması: "
                    + ", ".join(day_end_summary.affected_portfolio_symbols)
                )
    
            st.subheader("Günün başlıca gelişmeleri")
            if day_end_summary.top_developments:
                st.dataframe(
                    day_end_development_rows(day_end_summary),
                    width="stretch",
                    hide_index=True,
                )
            else:
                st.info("Seçilen gün için arşivlenmiş piyasa olayı bulunamadı.")
    
        for note in day_end_errors:
            st.caption(f"• {note}")
    with calendar_tab:
        # EKONOMIK_TAKVIM_V11_ROLE_CLARITY
        st.subheader("Ekonomik Takvim — Planlı Makro Olay Takibi")
        st.caption("Planlı ekonomik olayları gün, önem, kategori, ülke/bölge, önceki-beklenti-açıklanan değerler ve sonuç durumu ile izler.")
        st.caption(
            "Sprint-159 Ekonomik Takvim ilk sürümü manuel ve deterministiktir. "
            "Önceki, beklenti ve açıklanan değerler ham metin olarak saklanır; "
            "sistem beklentiden iyi/kötü veya fiyat yönü yorumu üretmez."
        )
        try:
            calendar_store = EconomicCalendarStore()
        except (EconomicCalendarError, OSError, ValueError) as exc:
            st.error(str(exc))
        else:
            calendar_controls = st.columns(2)
            with calendar_controls[0]:
                calendar_day = st.date_input(
                    "Takvim günü",
                    value=datetime.now(ISTANBUL).date(),
                    key="news_center_economic_calendar_date",
                )
            with calendar_controls[1]:
                calendar_min_label = st.selectbox(
                    "Asgari takvim önemi",
                    options=("Düşük", "Orta", "Yüksek", "Kritik"),
                    index=0,
                    key="news_center_economic_calendar_min_importance",
                )

            calendar_importance_by_label = {
                "Düşük": CalendarImportance.LOW,
                "Orta": CalendarImportance.MEDIUM,
                "Yüksek": CalendarImportance.HIGH,
                "Kritik": CalendarImportance.CRITICAL,
            }
            try:
                day_entries = calendar_store.list_day(calendar_day)
            except EconomicCalendarError as exc:
                st.error(str(exc))
                day_entries = ()

            visible_calendar_entries = select_calendar_entries(
                day_entries,
                selected_date=calendar_day,
                minimum_importance=calendar_importance_by_label[calendar_min_label],
            )
            announced_count = sum(bool(item.actual_value) for item in visible_calendar_entries)
            high_count = sum(
                item.importance in (CalendarImportance.HIGH, CalendarImportance.CRITICAL)
                for item in visible_calendar_entries
            )
            waiting_count = sum(
                not item.actual_value
                and item.scheduled_at.astimezone(ISTANBUL) <= datetime.now(ISTANBUL)
                for item in visible_calendar_entries
            )
            calendar_metrics = st.columns(4)
            calendar_metrics[0].metric("Takvim olayı", len(visible_calendar_entries))
            calendar_metrics[1].metric("Yüksek/Kritik", high_count)
            calendar_metrics[2].metric("Açıklanan", announced_count)
            calendar_metrics[3].metric("Sonuç bekleniyor", waiting_count)

            if visible_calendar_entries:
                st.dataframe(
                    calendar_rows(visible_calendar_entries),
                    width="stretch",
                    hide_index=True,
                )
            else:
                st.info("Seçilen gün ve önem düzeyinde ekonomik takvim kaydı yok.")

            with st.expander("Ekonomik takvim olayı ekle", expanded=False):
                category_labels = {
                    label: value for value, label in CALENDAR_CATEGORY_LABELS.items()
                }
                importance_labels = {
                    label: value for value, label in CALENDAR_IMPORTANCE_LABELS.items()
                }
                cal_title = st.text_input(
                    "Olay adı",
                    key="news_center_calendar_add_title",
                )
                cal_country = st.text_input(
                    "Ülke/Bölge",
                    value="Türkiye",
                    key="news_center_calendar_add_country",
                )
                cal_cols = st.columns(2)
                with cal_cols[0]:
                    cal_category_label = st.selectbox(
                        "Kategori",
                        options=tuple(category_labels),
                        key="news_center_calendar_add_category",
                    )
                with cal_cols[1]:
                    cal_importance_label = st.selectbox(
                        "Önem",
                        options=("Düşük", "Orta", "Yüksek", "Kritik"),
                        index=2,
                        key="news_center_calendar_add_importance",
                    )
                cal_time_cols = st.columns(2)
                with cal_time_cols[0]:
                    cal_date = st.date_input(
                        "Açıklama tarihi",
                        value=calendar_day,
                        key="news_center_calendar_add_date",
                    )
                with cal_time_cols[1]:
                    cal_time = st.time_input(
                        "Açıklama saati (Türkiye saati)",
                        key="news_center_calendar_add_time",
                    )
                value_cols = st.columns(3)
                with value_cols[0]:
                    cal_previous = st.text_input(
                        "Önceki",
                        key="news_center_calendar_add_previous",
                    )
                with value_cols[1]:
                    cal_expected = st.text_input(
                        "Beklenti",
                        key="news_center_calendar_add_expected",
                    )
                with value_cols[2]:
                    cal_actual = st.text_input(
                        "Açıklanan",
                        key="news_center_calendar_add_actual",
                    )
                cal_source = st.text_input(
                    "Kaynak",
                    key="news_center_calendar_add_source",
                )
                cal_reference = st.text_input(
                    "Kaynak referansı",
                    key="news_center_calendar_add_reference",
                )
                cal_notes = st.text_area(
                    "Not",
                    key="news_center_calendar_add_notes",
                )
                if st.button(
                    "Takvim olayını kaydet",
                    key="news_center_calendar_add_submit",
                    type="primary",
                ):
                    try:
                        entry = create_calendar_entry(
                            title=cal_title,
                            country=cal_country,
                            category=category_labels[cal_category_label],
                            scheduled_at=_combine(cal_date, cal_time),
                            importance=importance_labels[cal_importance_label],
                            previous_value=cal_previous,
                            expected_value=cal_expected,
                            actual_value=cal_actual,
                            source_name=cal_source,
                            source_reference=cal_reference,
                            notes=cal_notes,
                        )
                        calendar_store.add(entry)
                    except DuplicateCalendarEntryError as exc:
                        st.warning(str(exc))
                    except (EconomicCalendarError, ValueError) as exc:
                        st.error(str(exc))
                    else:
                        st.success("Ekonomik takvim olayı kaydedildi.")
                        st.rerun()

            if day_entries:
                with st.expander("Açıklanan / beklenti değerlerini güncelle", expanded=False):
                    entry_by_label = {
                        (
                            f"{item.scheduled_at.astimezone(ISTANBUL).strftime('%H:%M')} · "
                            f"{item.country} · {item.title}"
                        ): item
                        for item in day_entries
                    }
                    selected_entry_label = st.selectbox(
                        "Takvim kaydı",
                        options=tuple(entry_by_label),
                        key="news_center_calendar_update_entry",
                    )
                    selected_entry = entry_by_label[selected_entry_label]
                    update_cols = st.columns(3)
                    with update_cols[0]:
                        update_previous = st.text_input(
                            "Güncel önceki",
                            value=selected_entry.previous_value,
                            key="news_center_calendar_update_previous",
                        )
                    with update_cols[1]:
                        update_expected = st.text_input(
                            "Güncel beklenti",
                            value=selected_entry.expected_value,
                            key="news_center_calendar_update_expected",
                        )
                    with update_cols[2]:
                        update_actual = st.text_input(
                            "Güncel açıklanan",
                            value=selected_entry.actual_value,
                            key="news_center_calendar_update_actual",
                        )
                    update_notes = st.text_area(
                        "Güncel not",
                        value=selected_entry.notes,
                        key="news_center_calendar_update_notes",
                    )
                    if st.button(
                        "Takvim değerlerini güncelle",
                        key="news_center_calendar_update_submit",
                    ):
                        try:
                            calendar_store.update_values(
                                selected_entry.entry_id,
                                previous_value=update_previous,
                                expected_value=update_expected,
                                actual_value=update_actual,
                                notes=update_notes,
                            )
                        except EconomicCalendarError as exc:
                            st.error(str(exc))
                        else:
                            st.success("Ekonomik takvim değerleri güncellendi.")
                            st.rerun()

    with kap_tab:
        # KAP_DRY_RUN_V11_ROLE_CLARITY
        st.subheader("KAP Dry-Run — Yazmadan Önce Kontrollü Önizleme")
        st.caption("KAP kaynak çalıştırmasını kalıcı yazma öncesinde kontrollü önizleme olarak sınar; kullanıcı onayı ve mevcut güvenlik akışı korunur.")
        # KAP_AKISI_V11_ROLE_CLARITY
        st.subheader("KAP Akışı — Şirket Bildirimleri ve Resmî Açıklamalar")
        st.caption("KAP bildirimlerini mevcut Haber Merkezi sınıflandırma, önem ve bağlantı katmanlarına taşır; fiyat yönü veya işlem kararı üretmez.")
        st.caption(
            "Sprint-160 KAP Akışı yalnız mevcut Haber Merkezi arşivinde "
            "kaynak adı KAP olarak doğrulanan veya kap.org.tr referansına "
            "sahip bildirimleri gösterir. Otomatik KAP internet entegrasyonu "
            "yoktur; hisse sembolü uydurulmaz ve fiyat yönü/AL-SAT yorumu "
            "üretilmez."
        )

        kap_periods = {
            "Son 24 saat": 24,
            "Son 3 gün": 72,
            "Son 7 gün": 168,
            "Tüm arşiv": None,
        }
        kap_controls = st.columns(4)
        with kap_controls[0]:
            kap_period_label = st.selectbox(
                "KAP dönemi",
                options=tuple(kap_periods),
                index=0,
                key="news_center_kap_period",
            )
        with kap_controls[1]:
            kap_min_importance = st.selectbox(
                "Asgari KAP önemi",
                options=(0, 60, 70, 80, 90),
                index=0,
                key="news_center_kap_min_importance",
            )

        kap_symbols = kap_available_symbols(events, all_news)
        with kap_controls[2]:
            kap_symbol = st.selectbox(
                "Hisse filtresi",
                options=("Tümü", *kap_symbols),
                key="news_center_kap_symbol",
            )
        with kap_controls[3]:
            kap_portfolio_only = st.checkbox(
                "Yalnız Gölge Portföy",
                value=False,
                key="news_center_kap_portfolio_only",
            )

        kap_portfolio_symbols: tuple[str, ...] = ()
        kap_errors: list[str] = []
        try:
            kap_shadow_positions = ShadowPortfolioStore().list()
        except ShadowPortfolioError as exc:
            kap_errors.append(f"Gölge portföy: {exc}")
        else:
            kap_portfolio_symbols = tuple(
                item.symbol
                for item in kap_shadow_positions
                if item.status == OPEN_STATUS
            )

        try:
            kap_brief = build_kap_flow(
                events,
                all_news,
                now=datetime.now(ISTANBUL),
                lookback_hours=kap_periods[kap_period_label],
                min_importance=int(kap_min_importance),
                symbol_filter="" if kap_symbol == "Tümü" else kap_symbol,
                portfolio_symbols=kap_portfolio_symbols,
                portfolio_only=bool(kap_portfolio_only),
            )
        except ValueError as exc:
            st.error(str(exc))
        else:
            kap_metrics = st.columns(5)
            kap_metrics[0].metric("KAP bildirimi", kap_brief.total_disclosure_count)
            kap_metrics[1].metric("Hisse", kap_brief.unique_company_count)
            kap_metrics[2].metric("Önem ≥80", kap_brief.high_importance_count)
            kap_metrics[3].metric("Portföy teması", kap_brief.portfolio_touch_count)
            kap_metrics[4].metric("Sembolsüz", kap_brief.missing_symbol_count)

            if kap_brief.disclosures:
                st.dataframe(
                    kap_flow_rows(kap_brief),
                    width="stretch",
                    hide_index=True,
                )
            else:
                st.info("Seçilen filtrelerde doğrulanmış KAP bildirimi bulunamadı.")

            st.caption(
                "Portföy teması yalnız KAP olayına açıkça etiketlenmiş hisse "
                "sembolü ile açık Gölge Portföy pozisyonunun doğrudan "
                "kesişimidir; sektör veya fiyat yönü çıkarımı değildir."
            )

        for note in kap_errors:
            st.caption(f"• {note}")

    with symbol_news_tab:
        st.caption("Sprint-161 Hisse Haberleri görünümü yalnız olay kaydında açıkça etiketlenmiş hisse sembollerini kullanır; haber metninden hisse sembolü çıkarılmaz. Aynı olayın birden fazla haber kaynağı ayrı satır üretmez. Bu görünüm yeni bir skor üretmez ve fiyat yönü veya AL/SAT yorumu yapmaz.")

        symbol_news_periods = {
            "Son 24 saat": 24,
            "Son 3 gün": 72,
            "Son 7 gün": 168,
            "Tüm arşiv": None,
        }
        symbol_news_controls = st.columns(4)
        with symbol_news_controls[0]:
            symbol_news_period_label = st.selectbox(
                "Hisse haber dönemi",
                options=tuple(symbol_news_periods),
                index=2,
                key="news_center_symbol_news_period",
            )
        with symbol_news_controls[1]:
            symbol_news_min_importance = st.selectbox(
                "Asgari hisse haber önemi",
                options=(0, 60, 70, 80, 90),
                index=0,
                key="news_center_symbol_news_min_importance",
            )

        symbol_news_symbols = symbol_news_available_symbols(events)
        with symbol_news_controls[2]:
            symbol_news_symbol = st.selectbox(
                "Hisse filtresi",
                options=("Tümü", *symbol_news_symbols),
                key="news_center_symbol_news_symbol",
            )
        with symbol_news_controls[3]:
            symbol_news_portfolio_only = st.checkbox(
                "Yalnız Gölge Portföy",
                value=False,
                key="news_center_symbol_news_portfolio_only",
            )

        symbol_news_portfolio_symbols: tuple[str, ...] = ()
        symbol_news_errors: list[str] = []
        try:
            symbol_news_shadow_positions = ShadowPortfolioStore().list()
        except ShadowPortfolioError as exc:
            symbol_news_errors.append(f"Gölge portföy: {exc}")
        else:
            symbol_news_portfolio_symbols = tuple(
                item.symbol
                for item in symbol_news_shadow_positions
                if item.status == OPEN_STATUS
            )

        try:
            symbol_news_brief = build_symbol_news_brief(
                events,
                all_news,
                now=datetime.now(ISTANBUL),
                lookback_hours=symbol_news_periods[symbol_news_period_label],
                min_importance=int(symbol_news_min_importance),
                symbol_filter=(
                    "" if symbol_news_symbol == "Tümü" else symbol_news_symbol
                ),
                portfolio_symbols=symbol_news_portfolio_symbols,
                portfolio_only=bool(symbol_news_portfolio_only),
            )
        except ValueError as exc:
            st.error(str(exc))
        else:
            symbol_news_metrics = st.columns(6)
            symbol_news_metrics[0].metric("Hisse", symbol_news_brief.unique_symbol_count)
            symbol_news_metrics[1].metric("Olay", symbol_news_brief.unique_event_count)
            symbol_news_metrics[2].metric(
                "Önem ≥80", symbol_news_brief.high_importance_event_count
            )
            symbol_news_metrics[3].metric(
                "Çok kaynaklı", symbol_news_brief.multi_source_event_count
            )
            symbol_news_metrics[4].metric(
                "Birincil kaynak", symbol_news_brief.tier1_event_count
            )
            symbol_news_metrics[5].metric("KAP içeren", symbol_news_brief.kap_event_count)

            if symbol_news_brief.items:
                st.dataframe(
                    symbol_news_rows(symbol_news_brief),
                    width="stretch",
                    hide_index=True,
                )
                st.caption(
                    "Bir olay + bir hisse tek satırdır. Haber ve kaynak sayıları "
                    "aynı satırda özetlenir; portföy işareti yalnız açık Gölge "
                    "Portföy sembolü ile doğrudan eşleşmedir."
                )
            else:
                st.info("Seçilen filtrelerde hisse bazlı haber olayı bulunamadı.")

        for note in symbol_news_errors:
            st.caption(f"• {note}")

    with add_tab:
        # SHA256_BUTUNLUK_V11_ROLE_CLARITY
        st.subheader("Kayıt Bütünlüğü — SHA-256 İzlenebilirliği")
        st.caption("Arşiv/operasyon kayıtlarının değişmezlik ve izlenebilirlik kanıtını destekler; analiz veya AL/SAT mantığı değildir.")
        record_mode_options = (
            ("Yeni olay oluştur", "Mevcut olaya haber bağla")
            if events
            else ("Yeni olay oluştur",)
        )
        mode = st.radio(
            "Kayıt biçimi",
            options=record_mode_options,
            horizontal=True,
            key="news_center_record_mode",
        )
        if not events:
            st.info(
                "Henüz olay yok. İlk haber yeni bir piyasa olayı olarak "
                "arşivlenecek."
            )

        selected_event_id: str | None = None
        if mode == "Mevcut olaya haber bağla":
            by_id = {item.event_id: item for item in events}
            selected_event_id = st.selectbox(
                "Bağlanacak olay",
                options=tuple(by_id),
                format_func=lambda event_id: (
                    f"{by_id[event_id].occurred_at:%Y-%m-%d %H:%M} · "
                    f"{by_id[event_id].importance_score}/100 · "
                    f"{by_id[event_id].title}"
                ),
                key="news_center_existing_event",
            )
            selected = by_id[selected_event_id]
            st.info(
                f"Seçili olay: {selected.title} · "
                f"{selected.event_type.value} · "
                f"{selected.market_scope.value} · "
                f"{len(selected.news_ids)} kaynak"
            )

        with st.form("news_center_manual_form"):
            source_name = st.text_input(
                "Kaynak",
                placeholder="Örn. TCMB, KAP, Reuters",
            )
            source_tier_label = st.selectbox(
                "Kaynak seviyesi",
                options=tuple(SOURCE_TIER_LABELS),
            )
            headline = st.text_input("Haber başlığı")

            time_left, time_right = st.columns(2)
            with time_left:
                published_date = st.date_input("Yayın tarihi")
                published_time = st.time_input("Yayın saati")
            with time_right:
                if selected_event_id is None:
                    occurred_date = st.date_input("Olay tarihi")
                    occurred_time = st.time_input("Olay saati")
                else:
                    occurred_date = None
                    occurred_time = None

            if selected_event_id is None:
                event_title = st.text_input(
                    "Olay başlığı",
                    help="Boş bırakılırsa haber başlığı olay başlığı olarak kullanılır.",
                )
                event_type_label = st.selectbox(
                    "Olay türü",
                    options=tuple(EVENT_TYPE_LABELS),
                )
                scope_label = st.selectbox(
                    "Piyasa kapsamı",
                    options=tuple(SCOPE_LABELS),
                )
                sectors_text = st.text_input(
                    "Etkilenen sektörler",
                    placeholder="Banka, Ulaştırma",
                    help="Birden fazla sektör için virgül kullanın.",
                )
                symbols_text = st.text_input(
                    "Etkilenen BIST hisseleri",
                    placeholder="THYAO, ASELS",
                    help="Birden fazla hisse için virgül kullanın.",
                )
            else:
                event_title = ""
                event_type_label = "Diğer"
                scope_label = "Diğer"
                sectors_text = ""
                symbols_text = ""

            source_reference = st.text_input(
                "Kaynak referansı",
                placeholder="URL, KAP bildirim no veya kurum referansı",
            )
            body = st.text_area(
                "Haber / açıklama metni",
                height=220,
            )
            auto_apply = st.checkbox(
                "Deterministik sınıflandırmayı kayıtta uygula",
                value=True,
                help=(
                    "Yalnız güvenilir kaynak sözlüğü ve sabit anahtar kelime "
                    "kuralları kullanılır. Belirsiz alanlarda manuel seçim "
                    "korunur; AI kullanılmaz."
                ),
            )
            auto_group = st.checkbox(
                "Güvenli olay eşleştirmeyi kayıtta uygula",
                value=True,
                disabled=selected_event_id is not None,
                help=(
                    "Yalnız olay türü, kapsam, zaman, hisse ve başlık benzerliği "
                    "gibi deterministik kurallar kullanılır. Güçlü eşleşme "
                    "otomatik bağlanır; inceleme düzeyindeki eşleşmede kayıt "
                    "durdurulur ve kullanıcı kararı istenir."
                ),
            )
            previewed = st.form_submit_button(
                "Deterministik sınıflandırmayı önizle",
                width="stretch",
            )
            submitted = st.form_submit_button(
                "Haber kaydını arşivle",
                type="primary",
                width="stretch",
            )

        classification = None
        if previewed or submitted:
            classification = classify_news(
                source_name=source_name,
                source_reference=source_reference,
                headline=headline,
                body=body,
            )

        if previewed and classification is not None:
            if not classification.has_suggestion:
                st.info(
                    "Deterministik kurallar güvenilir bir öneri üretmedi. "
                    "Manuel seçimler korunacak."
                )
            else:
                st.markdown("**Deterministik ön sınıflandırma**")
                st.caption(
                    "Kaynak seviyesi: "
                    f"{classification.source_tier.value if classification.source_tier else '—'} · "
                    "Olay türü: "
                    f"{classification.event_type.value if classification.event_type else '—'} · "
                    "Kapsam: "
                    f"{classification.market_scope.value if classification.market_scope else '—'} · "
                    "Sektörler: "
                    f"{', '.join(classification.sectors) or '—'}"
                )
                for reason in classification.reasons:
                    st.caption(f"• {reason}")

        if submitted:
            published_at = _combine(published_date, published_time)
            occurred_at = (
                _combine(occurred_date, occurred_time)
                if selected_event_id is None
                else published_at
            )
            try:
                manual_source_tier = SOURCE_TIER_LABELS[source_tier_label]
                manual_event_type = EVENT_TYPE_LABELS[event_type_label]
                manual_scope = SCOPE_LABELS[scope_label]
                manual_sectors = _comma_values(sectors_text)

                applied_source_tier = manual_source_tier
                applied_event_type = manual_event_type
                applied_scope = manual_scope
                applied_sectors = manual_sectors

                if auto_apply and classification is not None:
                    applied_source_tier = (
                        classification.source_tier or manual_source_tier
                    )
                    if selected_event_id is None:
                        applied_event_type = (
                            classification.event_type or manual_event_type
                        )
                        applied_scope = (
                            classification.market_scope or manual_scope
                        )
                        applied_sectors = tuple(
                            dict.fromkeys(
                                (*manual_sectors, *classification.sectors)
                            )
                        )

                request = ManualNewsRequest(
                    source_name=source_name,
                    source_tier=applied_source_tier,
                    headline=headline,
                    published_at=published_at,
                    body=body,
                    source_reference=source_reference,
                    event_title=event_title,
                    event_type=applied_event_type,
                    occurred_at=occurred_at,
                    market_scope=applied_scope,
                    sectors=applied_sectors,
                    symbols=_comma_values(symbols_text),
                )
                result = service.submit_manual(
                    request,
                    existing_event_id=selected_event_id,
                    auto_group=bool(auto_group and selected_event_id is None),
                )
            except EventGroupingReviewRequired as exc:
                st.warning(str(exc))
                st.caption(
                    "Bu kayıt arşive yazılmadı. Mevcut olaya bağlayabilir veya "
                    "gerçekten ayrı bir olay ise güvenli olay eşleştirmesini "
                    "kapatıp tekrar kaydedebilirsiniz."
                )
                for reason in exc.match.reasons:
                    st.caption(f"• {reason}")
            except DuplicateNewsError as exc:
                st.warning(str(exc))
            except (
                NewsArchiveError,
                NewsCenterServiceError,
                ValueError,
                TypeError,
            ) as exc:
                st.error(str(exc))
            else:
                if result.grouped_automatically:
                    action = "Güvenli deterministik eşleşme ile mevcut olaya bağlandı."
                elif result.attached_to_existing_event:
                    action = "Mevcut olaya yeni kaynak bağlandı."
                else:
                    action = "Yeni piyasa olayı ve haber kaydı arşivlendi."
                st.success(
                    f"{action} Önem: {result.event.importance_score}/100 · "
                    f"Kaynak: {len(result.event.news_ids)}"
                )
                _importance_detail(st, result.event)
                saved_impact = assess_event_impact(result.event, (result.news,))
                if saved_impact.tags:
                    st.caption(
                        "Etki etiketleri: "
                        + ", ".join(tag.value for tag in saved_impact.tags)
                    )
                if saved_impact.links:
                    st.dataframe(
                        impact_rows(result.event, saved_impact),
                        width="stretch",
                        hide_index=True,
                    )
                for note in saved_impact.notes:
                    st.caption(f"• {note}")
                if result.grouped_automatically:
                    st.caption("Deterministik olay eşleştirme gerekçeleri:")
                    for reason in result.grouping_reasons:
                        st.caption(f"• {reason}")
                if auto_apply and classification is not None and classification.has_suggestion:
                    st.caption(
                        "Deterministik sınıflandırma uygulandı; yalnız açık "
                        "kuralların eşleştiği alanlar otomatik seçildi."
                    )
                    for reason in classification.reasons:
                        st.caption(f"• {reason}")
                st.caption(f"Olay kimliği: {result.event.event_id}")
                st.caption(
                    "Aynı haber içeriği SHA-256 özetiyle ikinci kez "
                    "kaydedilemez."
                )

    with event_tab:
        try:
            current_events = archive.list_events()
        except NewsArchiveError as exc:
            st.error(str(exc))
        else:
            if not current_events:
                st.info("Henüz arşivlenmiş piyasa olayı yok.")
            else:
                st.dataframe(
                    event_rows(current_events),
                    width="stretch",
                    hide_index=True,
                )
                st.caption(
                    "Aynı olaya bağlı farklı haber kaynakları tek olay satırında "
                    "Kaynak sayısı alanıyla gruplanır."
                )

                event_by_id = {item.event_id: item for item in current_events}
                detail_event_id = st.selectbox(
                    "Olay detayı",
                    options=tuple(event_by_id),
                    format_func=lambda event_id: (
                        f"{event_by_id[event_id].occurred_at:%Y-%m-%d %H:%M} · "
                        f"{event_by_id[event_id].importance_score}/100 · "
                        f"{event_by_id[event_id].title}"
                    ),
                    key="news_center_event_detail",
                )
                detail_event = event_by_id[detail_event_id]
                detail_columns = st.columns(4)
                detail_columns[0].metric("Önem", f"{detail_event.importance_score}/100")
                detail_columns[1].metric("Tür", detail_event.event_type.value)
                detail_columns[2].metric("Kapsam", detail_event.market_scope.value)
                detail_columns[3].metric("Kaynak", len(detail_event.news_ids))
                _importance_detail(st, detail_event)
                st.caption(
                    f"Sektörler: {', '.join(detail_event.sectors) or '—'} · "
                    f"Hisseler: {', '.join(detail_event.symbols) or '—'}"
                )

                try:
                    attached_news = archive.list_news_for_event(detail_event_id)
                except NewsArchiveError as exc:
                    st.error(str(exc))
                else:
                    detail_impact = assess_event_impact(detail_event, attached_news)
                    st.markdown("**Deterministik etki bağlantıları**")
                    st.caption(
                        "Etiketler: "
                        + (", ".join(tag.value for tag in detail_impact.tags) or "—")
                    )
                    if detail_impact.links:
                        st.dataframe(
                            impact_rows(detail_event, detail_impact),
                            width="stretch",
                            hide_index=True,
                        )
                    else:
                        st.info(
                            "Bu olay için güvenli deterministik etki bağlantısı "
                            "üretilemedi. Sistem sektör veya hisse uydurmadı."
                        )
                    for note in detail_impact.notes:
                        st.caption(f"• {note}")

                    st.markdown("**Bağlı haber kaynakları**")
                    st.dataframe(
                        news_rows(attached_news),
                        width="stretch",
                        hide_index=True,
                    )

    with impact_tab:
        impact_table_rows: list[dict[str, object]] = []
        impact_notes: list[str] = []
        for item in events:
            try:
                item_news = archive.list_news_for_event(item.event_id)
            except NewsArchiveError as exc:
                impact_notes.append(f"{item.title}: {exc}")
                continue
            assessment = assess_event_impact(item, item_news)
            impact_table_rows.extend(impact_rows(item, assessment))

        st.caption(
            "Bu tablo fiyat yönü tahmini değildir. DIRECT bağlantılar olayda "
            "açıkça bulunan hedefleri; SENSITIVITY bağlantıları ise sabit ve "
            "açıklanabilir duyarlılık kurallarını gösterir."
        )
        if impact_table_rows:
            st.dataframe(
                impact_table_rows,
                width="stretch",
                hide_index=True,
            )
        else:
            st.info(
                "Henüz gösterilebilecek deterministik sektör/hisse etki "
                "bağlantısı yok."
            )
        for note in impact_notes:
            st.caption(f"• {note}")

    with sector_tab:
        # ETIKET_BAGLANTI_V11_ROLE_CLARITY
        st.subheader("Etiket ve Bağlantılar — Olayı Hisse/Sektör Bağlamına Taşıma")
        st.caption("Mevcut etiket, hisse, sektör ve olay türü bağlantıları haberin neden ilgili olduğunu açıklar; yeni tahmin veya işlem kararı üretmez.")
        # SEKTOR_ETKI_HARITASI_V11_ROLE_CLARITY
        st.subheader("Sektör Etki Haritası — Haber/Olay Sektör Bağlantıları")
        st.caption("Haber Merkezi olaylarını deterministik sektör bağlantılarıyla toplulaştırır; doğrudan sektör olaylarını ve duyarlılık ilişkilerini ayrı gösterir.")
        st.info("Akış: Haber/Olay → sektör bağlantısı ve gerekçesi → Sektör Etki Haritası → ilgili hisse/Portföy Etki Radarı. Harita fiyat yönü, AL/SAT kararı, teknik skor veya AI kararı üretmez.")
        st.caption(
            "Sektör Etki Haritası fiyat yönü tahmini değildir. Haber Merkezi'nin "
            "deterministik SECTOR bağlantılarını dönem bazında toplulaştırır ve "
            "hangi sektörlerin gündemde olduğunu gösterir."
        )
        window_label = st.selectbox(
            "Sektör haritası dönemi",
            options=("Son 24 saat", "Son 3 gün", "Son 7 gün", "Tüm arşiv"),
            index=2,
            key="news_center_sector_window",
        )
        window_delta = {
            "Son 24 saat": timedelta(hours=24),
            "Son 3 gün": timedelta(days=3),
            "Son 7 gün": timedelta(days=7),
            "Tüm arşiv": None,
        }[window_label]
        since = (
            datetime.now(ISTANBUL) - window_delta
            if window_delta is not None
            else None
        )

        sector_news_by_event = {}
        sector_errors: list[str] = []
        for item in events:
            if since is not None and item.occurred_at < since:
                continue
            try:
                sector_news_by_event[item.event_id] = archive.list_news_for_event(
                    item.event_id
                )
            except NewsArchiveError as exc:
                sector_errors.append(f"{item.title}: {exc}")

        sector_map = build_sector_impact_map(
            events,
            sector_news_by_event,
            since=since,
        )
        sector_columns = st.columns(4)
        sector_columns[0].metric("Sektör", sector_map.sector_count)
        sector_columns[1].metric("Sektöre temas eden olay", sector_map.event_count)
        sector_columns[2].metric(
            "Önem ≥80 olay", sector_map.high_importance_event_count
        )
        sector_columns[3].metric(
            "Doğrudan sektör", sector_map.direct_sector_count
        )

        if not sector_map.summaries:
            st.info(
                "Seçilen dönemde deterministik sektör etki bağlantısı bulunamadı."
            )
        else:
            st.markdown("**Sektör gündem özeti**")
            st.dataframe(
                sector_summary_rows(sector_map),
                width="stretch",
                hide_index=True,
            )
            st.markdown("**Sektör–olay bağlantıları**")
            st.dataframe(
                sector_event_rows(sector_map),
                width="stretch",
                hide_index=True,
            )
            st.caption(
                "Doğrudan ve duyarlılık bağlantıları ayrı sayılır. Aynı olayın "
                "aynı sektöre bağlantısı tek kez sayılır. Gündem yoğunluğu "
                "olumlu/olumsuz fiyat yönü anlamına gelmez."
            )

        for note in sector_errors:
            st.caption(f"• {note}")

    with portfolio_tab:
        # PORTFOY_ETKI_RADARI_V11_ROLE_CLARITY
        st.subheader("Portföy Etki Radarı — Açık Pozisyon Haber/Olay Etkisi")
        st.caption(
            "Haber Merkezi olaylarını yalnız açık Gölge Portföy pozisyonlarıyla kesiştirir; "
            "doğrudan hisse, sektör ve piyasa-geneli bağlantıları üzerinden hangi açık pozisyonların etkilendiğini açıklar."
        )
        st.info(
            "Akış: Haber/Olay → Etki Bağlantıları / Sektör Etki Haritası → Açık Gölge Pozisyonu → Portföy Etki Radarı. "
            "Radar fiyat yönü tahmini, AL/SAT kararı, teknik skor veya yeni pozisyon üretmez."
        )
        st.caption(
            "Sprint-154 Portföy Etki Radarı yalnız açık Gölge Portföy "
            "pozisyonlarını Haber Merkezi'nin deterministik etki bağlantılarıyla "
            "kesiştirir. Bu görünüm fiyat yönü, AL/SAT kararı veya teknik skor "
            "üretmez."
        )
        try:
            shadow_positions = ShadowPortfolioStore().list()
        except ShadowPortfolioError as exc:
            st.warning(f"Gölge portföy okunamadı: {exc}")
        else:
            open_positions = tuple(
                item for item in shadow_positions if item.status == OPEN_STATUS
            )
            if not open_positions:
                st.info(
                    "Gölge Portföyde açık pozisyon yok. Portföy Etki Radarı "
                    "yalnız açık pozisyonları izler."
                )
            else:
                members = tuple(
                    PortfolioMember(
                        symbol=item.symbol,
                        sector=getattr(item, "sector", "") or "",
                    )
                    for item in open_positions
                )
                news_by_event = {}
                radar_errors: list[str] = []
                for item in events:
                    try:
                        news_by_event[item.event_id] = archive.list_news_for_event(
                            item.event_id
                        )
                    except NewsArchiveError as exc:
                        radar_errors.append(f"{item.title}: {exc}")

                radar = build_portfolio_impact_radar(
                    events,
                    news_by_event,
                    members,
                )
                radar_columns = st.columns(4)
                radar_columns[0].metric("Açık pozisyon", radar.member_count)
                radar_columns[1].metric(
                    "Olayla kesişen", radar.affected_member_count
                )
                radar_columns[2].metric(
                    "Doğrudan hisse eşleşmesi", radar.direct_symbol_hit_count
                )
                radar_columns[3].metric(
                    "Önem ≥80 olay", radar.high_importance_event_count
                )

                if not radar.hits:
                    st.info(
                        "Mevcut Haber Merkezi olayları ile açık Gölge Portföy "
                        "arasında deterministik etki kesişimi bulunamadı."
                    )
                else:
                    st.markdown("**Açık pozisyon etki özeti**")
                    st.caption("Önce hangi açık hisselerin olaylarla kesiştiğini, ardından olay bazındaki gerekçe ve eşleşme türünü inceleyin.")
                    st.markdown("**Portföy kapsama özeti**")
                    st.dataframe(
                        portfolio_symbol_summary_rows(radar),
                        width="stretch",
                        hide_index=True,
                    )
                    st.markdown("**Olay–portföy kesişimleri — neden etkilendi?**")
                    st.caption("Eşleşme türü ve Gerekçe alanları etkinin hangi deterministik bağ üzerinden kurulduğunu gösterir.")
                    st.dataframe(
                        portfolio_impact_rows(radar),
                        width="stretch",
                        hide_index=True,
                    )
                    st.caption(
                        "Aynı olay bir hisseye birden fazla yoldan temas ederse "
                        "tek satır gösterilir. Öncelik: DIRECT_SYMBOL > SECTOR > "
                        "MARKET. Bu öncelik yalnız bağlantı gücünü seçer; fiyat "
                        "yönü üretmez."
                    )

                for note in radar_errors:
                    st.caption(f"• {note}")

    with news_tab:
        # HABER_ARSIVI_V11_ROLE_CLARITY
        st.subheader("Haber Arşivi — Filtreli Geçmiş Olay İncelemesi")
        st.caption("Arşivlenmiş haberleri tarih, önem, kaynak, hisse, sektör, olay türü ve piyasa kapsamı filtreleriyle yeniden inceler; yeni haber veya skor üretmez.")
        st.caption(
            "Sprint-164 arşiv görünümü haber metninden hisse veya sektör tahmin etmez. "
            "Hisse, sektör, olay türü, kapsam ve önem yalnız bağlı piyasa olayından "
            "gelir. Mevcut önem skoru yalnız gösterilir; "
            "yeni skor, fiyat yönü, AL/SAT veya AI yorumu üretmez."
        )
        try:
            current_news = archive.list_news(limit=10000)
            current_archive_events = archive.list_events(limit=5000)
        except NewsArchiveError as exc:
            st.error(str(exc))
        else:
            if not current_news:
                st.info("Henüz arşivlenmiş haber kaydı yok.")
            else:
                published_dates = tuple(
                    item.published_at.astimezone(ISTANBUL).date()
                    for item in current_news
                )
                earliest_date = min(published_dates)
                latest_date = max(published_dates)
    
                archive_filter_1 = st.columns(4)
                with archive_filter_1[0]:
                    archive_start_date = st.date_input(
                        "Başlangıç tarihi",
                        value=earliest_date,
                        min_value=earliest_date,
                        max_value=latest_date,
                        key="news_center_archive_start_date",
                    )
                with archive_filter_1[1]:
                    archive_end_date = st.date_input(
                        "Bitiş tarihi",
                        value=latest_date,
                        min_value=earliest_date,
                        max_value=latest_date,
                        key="news_center_archive_end_date",
                    )
                with archive_filter_1[2]:
                    archive_min_importance = st.selectbox(
                        "Asgari önem",
                        options=(0, 60, 70, 80, 90),
                        index=0,
                        key="news_center_archive_min_importance",
                    )
                with archive_filter_1[3]:
                    archive_trusted_only = st.checkbox(
                        "Yalnız güvenilir kaynaklar",
                        value=False,
                        key="news_center_archive_trusted_only",
                    )
    
                archive_sources = ("Tümü",) + archive_available_sources(current_news)
                archive_symbols = ("Tümü",) + archive_available_symbols(
                    current_archive_events
                )
                archive_sectors = ("Tümü",) + archive_available_sectors(
                    current_archive_events
                )
    
                archive_filter_2 = st.columns(3)
                with archive_filter_2[0]:
                    archive_source = st.selectbox(
                        "Kaynak",
                        options=archive_sources,
                        key="news_center_archive_source",
                    )
                with archive_filter_2[1]:
                    archive_symbol = st.selectbox(
                        "Hisse",
                        options=archive_symbols,
                        key="news_center_archive_symbol",
                    )
                with archive_filter_2[2]:
                    archive_sector = st.selectbox(
                        "Sektör",
                        options=archive_sectors,
                        key="news_center_archive_sector",
                    )
    
                archive_event_types = ("Tümü",) + tuple(EVENT_TYPE_LABELS)
                archive_scopes = ("Tümü",) + tuple(SCOPE_LABELS)
    
                archive_filter_3 = st.columns(3)
                with archive_filter_3[0]:
                    archive_event_type_label = st.selectbox(
                        "Olay türü",
                        options=archive_event_types,
                        key="news_center_archive_event_type",
                    )
                with archive_filter_3[1]:
                    archive_scope_label = st.selectbox(
                        "Piyasa kapsamı",
                        options=archive_scopes,
                        key="news_center_archive_scope",
                    )
                with archive_filter_3[2]:
                    archive_limit = st.selectbox(
                        "Gösterilecek kayıt",
                        options=(100, 250, 500, 1000, 2500, 5000),
                        index=2,
                        key="news_center_archive_limit",
                    )
    
                archive_text_query = st.text_input(
                    "Arşivde ara",
                    placeholder="Başlık, haber metni, olay başlığı veya kaynak...",
                    key="news_center_archive_text_query",
                )
    
                try:
                    archive_view = build_archive_news_view(
                        current_archive_events,
                        current_news,
                        start_date=archive_start_date,
                        end_date=archive_end_date,
                        source_filter=(
                            "" if archive_source == "Tümü" else archive_source
                        ),
                        symbol_filter=(
                            "" if archive_symbol == "Tümü" else archive_symbol
                        ),
                        sector_filter=(
                            "" if archive_sector == "Tümü" else archive_sector
                        ),
                        event_type_filter=(
                            None
                            if archive_event_type_label == "Tümü"
                            else EVENT_TYPE_LABELS[archive_event_type_label]
                        ),
                        market_scope_filter=(
                            None
                            if archive_scope_label == "Tümü"
                            else SCOPE_LABELS[archive_scope_label]
                        ),
                        min_importance=int(archive_min_importance),
                        text_query=archive_text_query,
                        trusted_only=archive_trusted_only,
                        limit=int(archive_limit),
                    )
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    archive_metrics = st.columns(6)
                    archive_metrics[0].metric("Haber", archive_view.news_count)
                    archive_metrics[1].metric("Olay", archive_view.unique_event_count)
                    archive_metrics[2].metric("Kaynak", archive_view.source_count)
                    archive_metrics[3].metric("Birincil", archive_view.tier1_news_count)
                    archive_metrics[4].metric("KAP", archive_view.kap_news_count)
                    archive_metrics[5].metric(
                        "Hisse bağlantılı", archive_view.symbol_linked_count
                    )
    
                    if archive_view.unlinked_event_count:
                        st.caption(
                            f"{archive_view.unlinked_event_count} kaydın bağlı olayı "
                            "bulunamadı; bu kayıtlar için olay bilgisi uydurulmadı."
                        )
    
                    if archive_view.items:
                        st.dataframe(
                            archive_news_rows(archive_view),
                            width="stretch",
                            hide_index=True,
                        )
                    else:
                        st.info("Seçilen arşiv filtrelerinde haber bulunamadı.")
    
    st.caption(f"Arşiv: {archive.path}")

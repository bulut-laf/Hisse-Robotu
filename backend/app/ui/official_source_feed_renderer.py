from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from backend.app.news_center.borsa_istanbul_adapter import (
    BorsaIstanbulAdapterError,
    BorsaIstanbulAnnouncementUrlAdapter,
)
from backend.app.news_center.feed_ingestion import FeedIngestionService
from backend.app.news_center.official_source_operations import (
    OfficialSourceOperationError,
    OfficialSourceOperationKind,
    OfficialSourceOperationStore,
)
from backend.app.news_center.hmb_adapter import (
    HmbAdapterError,
    HmbPressUrlAdapter,
)
from backend.app.news_center.kap_adapter import (
    KapAdapterError,
    KapUrlAdapter,
)
from backend.app.news_center.resmi_gazete_adapter import (
    ResmiGazeteAdapterError,
    ResmiGazeteArticleUrlAdapter,
)
from backend.app.news_center.spk_adapter import (
    SpkAdapterError,
    SpkPressUrlAdapter,
)
from backend.app.news_center.tcmb_adapter import (
    TcmbAdapterError,
    TcmbPressUrlAdapter,
)
from backend.app.news_center.tuik_adapter import (
    TuikAdapterError,
    TuikPressUrlAdapter,
)


PreviewSummaryFormatter = Callable[[object, object], str]


@dataclass(frozen=True, slots=True)
class OfficialSourceFeedUiSpec:
    slug: str
    canonical_name: str
    section_title: str
    description: str
    url_label: str
    placeholder: str
    network_label: str
    network_warning: str
    preview_button_label: str
    import_button_label: str
    url_changed_message: str
    duplicate_preview_message: str
    duplicate_import_message: str
    archive_success_message: str
    adapter_type: type
    error_type: type[RuntimeError]
    summary_formatter: PreviewSummaryFormatter
    clear_after_duplicate_import: bool = False

    @property
    def url_key(self) -> str:
        return f"news_center_{self.slug}_feed_url"

    @property
    def network_key(self) -> str:
        return f"news_center_{self.slug}_network_enabled"

    @property
    def preview_button_key(self) -> str:
        return f"news_center_{self.slug}_preview_button"

    @property
    def import_button_key(self) -> str:
        return f"news_center_{self.slug}_import_button"

    @property
    def preview_state_key(self) -> str:
        return f"news_center_{self.slug}_feed_preview"


def _kap_summary(item, timezone) -> str:
    return (
        f"KAP #{item.external_id} · "
        f"{item.published_at.astimezone(timezone).strftime('%Y-%m-%d %H:%M:%S')} · "
        f"{', '.join(item.symbols) or 'Hisse belirtilmemiş'}"
    )


def _event_summary(prefix: str, date_format: str, include_scope: bool = False):
    def formatter(item, timezone) -> str:
        summary = (
            f"{prefix} {item.external_id} · "
            f"{item.published_at.astimezone(timezone).strftime(date_format)} · "
            f"{item.event_type.value}"
        )
        if include_scope:
            summary += f" · {item.market_scope.value}"
        return summary

    return formatter


OFFICIAL_SOURCE_FEED_UI_SPECS: tuple[OfficialSourceFeedUiSpec, ...] = (
    OfficialSourceFeedUiSpec(
        slug="kap",
        canonical_name="KAP",
        section_title="KAP — kontrollü bildirim URL'si",
        description="",
        url_label="KAP bildirim detay URL'si",
        placeholder="https://www.kap.org.tr/tr/Bildirim/1636759",
        network_label="Bu işlem için KAP ağına bağlan",
        network_warning=(
            "KAP ağı kapalı. Yalnız bu önizleme isteği için ağ onayını açın."
        ),
        preview_button_label="KAP URL'sini önizle",
        import_button_label="Önizlemeyi arşive aktar",
        url_changed_message=(
            "URL değiştirildi. Arşive aktarmadan önce yeni URL için tekrar önizleme yapın."
        ),
        duplicate_preview_message=(
            "Bu içerik arşivde zaten var. Yeniden arşivlenmeyecek."
        ),
        duplicate_import_message=(
            "Kayıt arşivde zaten mevcut; ikinci kez yazılmadı."
        ),
        archive_success_message=(
            "KAP bildirimi açık onayla Haber Merkezi arşivine aktarıldı."
        ),
        adapter_type=KapUrlAdapter,
        error_type=KapAdapterError,
        summary_formatter=_kap_summary,
        clear_after_duplicate_import=True,
    ),
    OfficialSourceFeedUiSpec(
        slug="tcmb",
        canonical_name="TCMB",
        section_title="TCMB — kontrollü basın duyurusu URL'si",
        description="",
        url_label="TCMB basın duyurusu URL'si",
        placeholder=(
            "https://www.tcmb.gov.tr/wps/wcm/connect/TR/TCMB%2BTR/"
            "Main%2BMenu/Duyurular/Basin/2026/DUY2026-28"
        ),
        network_label="Bu işlem için TCMB ağına bağlan",
        network_warning=(
            "TCMB ağı kapalı. Yalnız bu önizleme isteği için ağ onayını açın."
        ),
        preview_button_label="TCMB URL'sini önizle",
        import_button_label="TCMB önizlemesini arşive aktar",
        url_changed_message=(
            "URL değiştirildi. Arşive aktarmadan önce yeni TCMB URL'si "
            "için tekrar önizleme yapın."
        ),
        duplicate_preview_message=(
            "Bu TCMB içeriği arşivde zaten var. Yeniden arşivlenmeyecek."
        ),
        duplicate_import_message=(
            "TCMB kaydı arşivde zaten mevcut; ikinci kez yazılmadı."
        ),
        archive_success_message=(
            "TCMB duyurusu açık onayla Haber Merkezi arşivine aktarıldı."
        ),
        adapter_type=TcmbPressUrlAdapter,
        error_type=TcmbAdapterError,
        summary_formatter=_event_summary("TCMB", "%Y-%m-%d"),
    ),
    OfficialSourceFeedUiSpec(
        slug="tuik",
        canonical_name="TÜİK",
        section_title="TÜİK — kontrollü haber bülteni URL'si",
        description="",
        url_label="TÜİK haber bülteni URL'si",
        placeholder="https://veriportali.tuik.gov.tr/tr/press/58175",
        network_label="Bu işlem için TÜİK ağına bağlan",
        network_warning=(
            "TÜİK ağı kapalı. Yalnız bu önizleme isteği için ağ onayını açın."
        ),
        preview_button_label="TÜİK URL'sini önizle",
        import_button_label="TÜİK önizlemesini arşive aktar",
        url_changed_message=(
            "URL değiştirildi. Arşive aktarmadan önce yeni TÜİK URL'si "
            "için tekrar önizleme yapın."
        ),
        duplicate_preview_message=(
            "Bu TÜİK içeriği arşivde zaten var. Yeniden arşivlenmeyecek."
        ),
        duplicate_import_message=(
            "TÜİK kaydı arşivde zaten mevcut; ikinci kez yazılmadı."
        ),
        archive_success_message=(
            "TÜİK bülteni açık onayla Haber Merkezi arşivine aktarıldı."
        ),
        adapter_type=TuikPressUrlAdapter,
        error_type=TuikAdapterError,
        summary_formatter=_event_summary("TÜİK", "%Y-%m-%d %H:%M"),
    ),
    OfficialSourceFeedUiSpec(
        slug="spk",
        canonical_name="SPK",
        section_title="SPK — kontrollü basın duyurusu URL'si",
        description=(
            "SPK adapteri yalnız Basın Duyuruları detay sayfasını okur. "
            "Başlıktan açık bir piyasa düzenlemesi anlaşılmıyorsa olay türü DIGER "
            "ve kapsam OTHER bırakılır; piyasa kapsamı uydurulmaz."
        ),
        url_label="SPK basın duyurusu URL'si",
        placeholder=(
            "https://spk.gov.tr/duyurular/basin-duyurulari/2026/"
            "dolandiricilik-girisimlerine-iliskin-duyuru"
        ),
        network_label="Bu işlem için SPK ağına bağlan",
        network_warning=(
            "SPK ağı kapalı. Yalnız bu önizleme isteği için ağ onayını açın."
        ),
        preview_button_label="SPK URL'sini önizle",
        import_button_label="SPK önizlemesini arşive aktar",
        url_changed_message=(
            "URL değiştirildi. Arşive aktarmadan önce yeni SPK URL'si "
            "için tekrar önizleme yapın."
        ),
        duplicate_preview_message=(
            "Bu SPK içeriği arşivde zaten var. Yeniden arşivlenmeyecek."
        ),
        duplicate_import_message=(
            "SPK kaydı arşivde zaten mevcut; ikinci kez yazılmadı."
        ),
        archive_success_message=(
            "SPK duyurusu açık onayla Haber Merkezi arşivine aktarıldı."
        ),
        adapter_type=SpkPressUrlAdapter,
        error_type=SpkAdapterError,
        summary_formatter=_event_summary("SPK", "%Y-%m-%d", True),
    ),
    OfficialSourceFeedUiSpec(
        slug="hmb",
        canonical_name="Hazine ve Maliye Bakanlığı",
        section_title="HMB — kontrollü basın duyurusu URL'si",
        description=(
            "HMB adapteri yalnız tekil /haberler/<slug> veya /duyuru/<slug> "
            "sayfasını okur. Başlık açık bir makro/finans temasını belirtmiyorsa "
            "DIGER + OTHER bırakılır; gövdeden piyasa etkisi tahmin edilmez."
        ),
        url_label="HMB basın duyurusu URL'si",
        placeholder="https://www.hmb.gov.tr/duyuru/basin-duyurusu-12-04-2026",
        network_label="Bu işlem için HMB ağına bağlan",
        network_warning=(
            "HMB ağı kapalı. Yalnız bu önizleme isteği için ağ onayını açın."
        ),
        preview_button_label="HMB URL'sini önizle",
        import_button_label="HMB önizlemesini arşive aktar",
        url_changed_message=(
            "URL değiştirildi. Arşive aktarmadan önce yeni HMB URL'si "
            "için tekrar önizleme yapın."
        ),
        duplicate_preview_message=(
            "Bu HMB içeriği arşivde zaten var. Yeniden arşivlenmeyecek."
        ),
        duplicate_import_message=(
            "HMB kaydı arşivde zaten mevcut; ikinci kez yazılmadı."
        ),
        archive_success_message=(
            "HMB duyurusu açık onayla Haber Merkezi arşivine aktarıldı."
        ),
        adapter_type=HmbPressUrlAdapter,
        error_type=HmbAdapterError,
        summary_formatter=_event_summary("HMB", "%Y-%m-%d", True),
    ),
    OfficialSourceFeedUiSpec(
        slug="borsa_istanbul",
        canonical_name="Borsa İstanbul",
        section_title="Borsa İstanbul — kontrollü duyuru URL'si",
        description=(
            "Adapter yalnız tekil /duyuru/<id>/<slug> HTML detay sayfasını okur. "
            "Duyuru içindeki ek/PDF/Excel bağlantılarını otomatik takip etmez. "
            "İlk sürümde gövdeden hisse veya sektör tahmin edilmez."
        ),
        url_label="Borsa İstanbul duyuru URL'si",
        placeholder=(
            "https://www.borsaistanbul.com/duyuru/15547/"
            "bist-geri-alim-endeksi-donemsel-degisiklikleri"
        ),
        network_label="Bu işlem için Borsa İstanbul ağına bağlan",
        network_warning=(
            "Borsa İstanbul ağı kapalı. Yalnız bu önizleme isteği için ağ onayını açın."
        ),
        preview_button_label="Borsa İstanbul URL'sini önizle",
        import_button_label="Borsa İstanbul önizlemesini arşive aktar",
        url_changed_message=(
            "URL değiştirildi. Arşive aktarmadan önce yeni Borsa İstanbul "
            "URL'si için tekrar önizleme yapın."
        ),
        duplicate_preview_message=(
            "Bu Borsa İstanbul içeriği arşivde zaten var. Yeniden arşivlenmeyecek."
        ),
        duplicate_import_message=(
            "Borsa İstanbul kaydı arşivde zaten mevcut; ikinci kez yazılmadı."
        ),
        archive_success_message=(
            "Borsa İstanbul duyurusu açık onayla Haber Merkezi arşivine aktarıldı."
        ),
        adapter_type=BorsaIstanbulAnnouncementUrlAdapter,
        error_type=BorsaIstanbulAdapterError,
        summary_formatter=_event_summary("Borsa İstanbul", "%Y-%m-%d", True),
    ),
    OfficialSourceFeedUiSpec(
        slug="resmi_gazete",
        canonical_name="Resmî Gazete",
        section_title="Resmî Gazete — kontrollü HTML mevzuat URL'si",
        description=(
            "Adapter yalnız /eskiler/YYYY/MM/YYYYMMDD-N.htm biçimindeki tekil "
            "HTML mevzuat maddesini okur. PDF/ek veya günlük sayı indeksini otomatik "
            "takip etmez. İlk sürümde gövdeden piyasa kapsamı, hisse veya sektör "
            "tahmin edilmez."
        ),
        url_label="Resmî Gazete mevzuat URL'si",
        placeholder=(
            "https://www.resmigazete.gov.tr/eskiler/2026/05/"
            "20260501-1.htm"
        ),
        network_label="Bu işlem için Resmî Gazete ağına bağlan",
        network_warning=(
            "Resmî Gazete ağı kapalı. Yalnız bu önizleme isteği için ağ onayını açın."
        ),
        preview_button_label="Resmî Gazete URL'sini önizle",
        import_button_label="Resmî Gazete önizlemesini arşive aktar",
        url_changed_message=(
            "URL değiştirildi. Arşive aktarmadan önce yeni Resmî Gazete "
            "URL'si için tekrar önizleme yapın."
        ),
        duplicate_preview_message=(
            "Bu Resmî Gazete içeriği arşivde zaten var. Yeniden arşivlenmeyecek."
        ),
        duplicate_import_message=(
            "Resmî Gazete kaydı arşivde zaten mevcut; ikinci kez yazılmadı."
        ),
        archive_success_message=(
            "Resmî Gazete mevzuatı açık onayla Haber Merkezi arşivine aktarıldı."
        ),
        adapter_type=ResmiGazeteArticleUrlAdapter,
        error_type=ResmiGazeteAdapterError,
        summary_formatter=_event_summary("Resmî Gazete", "%Y-%m-%d", True),
    ),
)


def official_source_feed_ui_names() -> tuple[str, ...]:
    return tuple(spec.canonical_name for spec in OFFICIAL_SOURCE_FEED_UI_SPECS)


def _record_operation(
    st,
    store: OfficialSourceOperationStore,
    spec: OfficialSourceFeedUiSpec,
    kind: OfficialSourceOperationKind,
    *,
    source_reference="",
    detail="",
) -> None:
    try:
        store.append(
            spec.canonical_name,
            kind,
            source_reference=source_reference,
            detail=detail,
        )
    except (OfficialSourceOperationError, OSError, ValueError) as exc:
        st.caption(f"Operasyon günlüğü yazılamadı: {exc}")


def _render_source_feed_block(
    st,
    archive,
    timezone,
    spec: OfficialSourceFeedUiSpec,
    operation_store: OfficialSourceOperationStore,
) -> None:
    st.subheader(spec.section_title)
    if spec.description:
        st.caption(spec.description)

    source_url = st.text_input(
        spec.url_label,
        placeholder=spec.placeholder,
        key=spec.url_key,
    )
    network_enabled = st.checkbox(
        spec.network_label,
        value=False,
        key=spec.network_key,
    )

    if st.button(
        spec.preview_button_label,
        key=spec.preview_button_key,
        width="stretch",
    ):
        if not network_enabled:
            _record_operation(
                st,
                operation_store,
                spec,
                OfficialSourceOperationKind.PREVIEW_BLOCKED,
                source_reference=source_url,
                detail="Ağ onayı kapalı olduğu için önizleme başlatılmadı.",
            )
            st.warning(spec.network_warning)
        else:
            try:
                result = spec.adapter_type(network_enabled=True).fetch(source_url)
                preview = FeedIngestionService(archive).preview(result.item)
            except (spec.error_type, RuntimeError, ValueError) as exc:
                _record_operation(
                    st,
                    operation_store,
                    spec,
                    OfficialSourceOperationKind.PREVIEW_ERROR,
                    source_reference=source_url,
                    detail=str(exc),
                )
                st.error(str(exc))
            else:
                _record_operation(
                    st,
                    operation_store,
                    spec,
                    OfficialSourceOperationKind.PREVIEW_SUCCESS,
                    source_reference=result.item.source_reference,
                    detail=(
                        "Dry-run duplicate."
                        if preview.duplicate
                        else "Dry-run yeni kayıt."
                    ),
                )
                st.session_state[spec.preview_state_key] = (
                    source_url,
                    result.item,
                    preview,
                )

    stored_preview = st.session_state.get(spec.preview_state_key)
    if not stored_preview:
        return

    preview_url, preview_item, preview = stored_preview
    if str(source_url or "").strip() != str(preview_url or "").strip():
        st.caption(spec.url_changed_message)
        return

    st.caption(spec.summary_formatter(preview_item, timezone))
    st.write(preview_item.headline)
    st.caption(preview_item.body)

    if preview.duplicate:
        st.warning(spec.duplicate_preview_message)
    else:
        st.success("Dry-run başarılı. Henüz arşive yazılmadı.")

    if not st.button(
        spec.import_button_label,
        key=spec.import_button_key,
        width="stretch",
        disabled=preview.duplicate,
    ):
        return

    try:
        import_result = FeedIngestionService(archive).import_item(preview_item)
    except RuntimeError as exc:
        _record_operation(
            st,
            operation_store,
            spec,
            OfficialSourceOperationKind.ARCHIVE_ERROR,
            source_reference=preview_item.source_reference,
            detail=str(exc),
        )
        st.error(str(exc))
        return

    if import_result.duplicate:
        _record_operation(
            st,
            operation_store,
            spec,
            OfficialSourceOperationKind.ARCHIVE_DUPLICATE,
            source_reference=preview_item.source_reference,
            detail="Arşivde mevcut kayıt; ikinci kez yazılmadı.",
        )
        st.warning(spec.duplicate_import_message)
        if spec.clear_after_duplicate_import:
            st.session_state.pop(spec.preview_state_key, None)
            st.rerun()
        return

    if import_result.archived:
        _record_operation(
            st,
            operation_store,
            spec,
            OfficialSourceOperationKind.ARCHIVE_SUCCESS,
            source_reference=preview_item.source_reference,
            detail="Kayıt açık kullanıcı onayıyla arşivlendi.",
        )
        st.success(spec.archive_success_message)
        st.session_state.pop(spec.preview_state_key, None)
        st.rerun()


def render_official_source_feed_blocks(
    st,
    archive,
    timezone,
    operation_store: OfficialSourceOperationStore | None = None,
) -> None:
    """Yedi kontrollü resmî kaynak için tek ortak Streamlit akışını çizer."""
    store = operation_store or OfficialSourceOperationStore()
    for index, spec in enumerate(OFFICIAL_SOURCE_FEED_UI_SPECS):
        if index:
            st.divider()
        _render_source_feed_block(st, archive, timezone, spec, store)

from __future__ import annotations

from datetime import date
from pathlib import Path

from backend.app.market_context.service import MarketContextService
from backend.app.market_context.store import DuplicateMarketContextError


def render_market_context_dashboard(
    st,
    *,
    project_root: str | Path = "D:/Projects/Hisse-Robotu",
) -> None:
    """Seans Öncesi Bağlam ekranını çizer.

    Bu UI yalnızca karar desteği sağlar.
    Teknik skor, aday sıralaması veya AL/SAT zincirine veri yazmaz.
    """

    project_root = Path(project_root)
    data_root = project_root / "backend" / "data"
    service = MarketContextService(data_root=data_root)

    st.header("Seans Öncesi Bağlam")
    st.caption(
        "Aracı kurum bültenleri, KAP açıklamaları ve benzeri piyasa metinleri "
        "karar desteği amacıyla ayrı kaynak olarak saklanır. "
        "Bu bilgiler teknik skorları ve AL/SAT kararlarını doğrudan değiştirmez."
    )

    source = st.text_input(
        "Kaynak",
        placeholder="Örn. ICBC, Gedik, KAP",
        key="market_context_source",
    )

    document_date = st.date_input(
        "Tarih",
        value=date.today(),
        key="market_context_date",
    )

    input_mode = st.radio(
        "Girdi türü",
        ("Metin Yapıştır", "TXT Yükle", "PDF Yükle"),
        horizontal=True,
        key="market_context_input_mode",
    )

    manual_text = ""
    uploaded_file = None

    if input_mode == "Metin Yapıştır":
        manual_text = st.text_area(
            "Bülten / haber metni",
            height=260,
            placeholder="Piyasa bülteni veya KAP metnini buraya yapıştırın...",
            key="market_context_manual_text",
        )
    elif input_mode == "TXT Yükle":
        uploaded_file = st.file_uploader(
            "TXT dosyası seç",
            type=["txt"],
            key="market_context_txt_file",
        )
    else:
        uploaded_file = st.file_uploader(
            "PDF dosyası seç",
            type=["pdf"],
            key="market_context_pdf_file",
        )

    if st.button(
        "İçeriği İşle ve Kaydet",
        type="primary",
        key="market_context_process",
    ):
        if not source.strip():
            st.error("Kaynak bilgisi girilmelidir.")
        else:
            try:
                saved = _process_input(
                    service=service,
                    input_mode=input_mode,
                    manual_text=manual_text,
                    uploaded_file=uploaded_file,
                    source=source.strip(),
                    document_date=document_date.isoformat(),
                    temp_root=project_root / "backend" / "cache" / "market_context_uploads",
                )
            except DuplicateMarketContextError:
                st.warning("Bu içerik daha önce yüklenmiş.")
            except ValueError as exc:
                st.error(str(exc))
            except Exception as exc:
                st.error(f"İçerik işlenemedi: {exc}")
            else:
                st.success("İçerik işlendi ve günlük arşive kaydedildi.")
                _render_document_result(st, saved)

    _render_daily_archive_summary(
        st,
        service=service,
        document_date=document_date.isoformat(),
    )


def _process_input(
    *,
    service: MarketContextService,
    input_mode: str,
    manual_text: str,
    uploaded_file,
    source: str,
    document_date: str,
    temp_root: Path,
):
    if input_mode == "Metin Yapıştır":
        if not manual_text.strip():
            raise ValueError("Metin boş olamaz.")
        return service.import_text(
            text=manual_text,
            source=source,
            document_date=document_date,
        )

    if uploaded_file is None:
        raise ValueError("Dosya seçilmelidir.")

    temp_root.mkdir(parents=True, exist_ok=True)
    suffix = ".txt" if input_mode == "TXT Yükle" else ".pdf"
    temp_path = temp_root / f"upload{suffix}"
    temp_path.write_bytes(uploaded_file.getvalue())

    try:
        if input_mode == "TXT Yükle":
            return service.import_txt(
                path=temp_path,
                source=source,
                document_date=document_date,
            )

        return service.import_pdf(
            path=temp_path,
            source=source,
            document_date=document_date,
        )
    finally:
        temp_path.unlink(missing_ok=True)


def _render_document_result(st, document) -> None:
    st.subheader("Yapılandırılmış Sonuç")

    c1, c2, c3 = st.columns(3)
    c1.metric("Endeks görünümü", document.index_outlook or "Belirlenemedi")
    c2.metric("Dış piyasa", document.external_market_outlook or "Belirlenemedi")
    c3.metric("Vadeli piyasa", document.futures_outlook or "Belirlenemedi")

    st.markdown("**Destekler**")
    st.write(", ".join(document.supports) if document.supports else "Belirlenemedi")

    st.markdown("**Dirençler**")
    st.write(", ".join(document.resistances) if document.resistances else "Belirlenemedi")

    st.markdown("**Makro / genel piyasa riskleri**")
    if document.macro_risks:
        for item in document.macro_risks:
            st.write(f"- {item}")
    else:
        st.write("Belirlenemedi")

    st.markdown("**Sektör etkileri**")
    if document.sector_impacts:
        for item in document.sector_impacts:
            st.write(f"- {item.get('sector', 'Sektör')}: {item.get('content', '')}")
    else:
        st.write("Belirlenemedi")

    st.markdown("**Hisse bazlı haberlar / KAP açıklamaları**")
    if document.stock_news:
        for item in document.stock_news:
            st.write(f"- {item.get('symbol', '')}: {item.get('content', '')}")
    else:
        st.write("Belirlenemedi")

    st.caption(
        f"Kaynak: {document.source} · Tarih: {document.document_date} · "
        f"Arşiv durumu: {document.archive_status}"
    )


def _render_daily_archive_summary(
    st,
    *,
    service: MarketContextService,
    document_date: str,
) -> None:
    manifest = service.store.load_manifest(document_date)

    st.divider()
    st.subheader("Günlük Rapor Arşivi")
    st.metric("Bu gün arşivlenen rapor", manifest.document_count)

    if manifest.sources:
        st.write("Kaynaklar: " + ", ".join(manifest.sources))
    else:
        st.caption("Seçili tarih için henüz arşivlenmiş rapor yok.")

    st.caption(
        "Bu arşiv ileride aynı güne ait çoklu raporların "
        "AI destekli toplu değerlendirmesinde kullanılacaktır."
    )

from __future__ import annotations

from datetime import date
from pathlib import Path

from backend.app.market_context.ai_daily_review_service import (
    DailyAIReviewService,
)
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
    ai_review_service = DailyAIReviewService(data_root=data_root)

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

    selected_date = document_date.isoformat()

    manifest = _render_daily_archive_summary(
        st,
        service=service,
        document_date=selected_date,
    )

    _render_daily_ai_review(
        st,
        ai_review_service=ai_review_service,
        document_date=selected_date,
        document_count=manifest.document_count,
        ai_review_status=manifest.ai_review_status,
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
):
    manifest = service.store.load_manifest(document_date)

    st.divider()
    st.subheader("Günlük Rapor Arşivi")
    st.metric("Bu gün arşivlenen rapor", manifest.document_count)

    if manifest.sources:
        st.write("Kaynaklar: " + ", ".join(manifest.sources))
    else:
        st.caption("Seçili tarih için henüz arşivlenmiş rapor yok.")

    st.caption(
        "Aynı güne ait çoklu raporlar aşağıdaki AI değerlendirme katmanında "
        "birlikte ele alınabilir."
    )

    return manifest


def _render_daily_ai_review(
    st,
    *,
    ai_review_service: DailyAIReviewService,
    document_date: str,
    document_count: int,
    ai_review_status: str,
) -> None:
    st.divider()
    st.subheader("AI Toplu Değerlendirme")
    st.caption(
        "Seçili güne ait arşivlenmiş raporları birlikte değerlendirir. "
        "Sonuç yalnızca karar desteğidir; teknik skor veya AL/SAT sinyali üretmez."
    )

    if document_count <= 0:
        st.info("AI değerlendirmesi için önce seçili tarihe en az bir rapor yükleyin.")
        return

    latest = ai_review_service.load_latest_review(document_date)

    # Kolon konteynerlerini düğmeden önce oluşturuyoruz; metrik değerlerini ise
    # değerlendirme sonucundan sonra yazıyoruz. Böylece başarılı AI çağrısı aynı
    # Streamlit render turunda "Değerlendirildi" durumuna yansır ve ayrıca
    # st.rerun() gerektirmez.
    c1, c2 = st.columns(2)

    if st.button(
        "Günlük Raporları AI ile Değerlendir",
        key=f"market_context_ai_review_{document_date}",
    ):
        try:
            with st.spinner("Günlük raporlar AI ile değerlendiriliyor..."):
                result = ai_review_service.run_daily_review(document_date)
        except Exception as exc:
            st.error(f"AI değerlendirmesi çalıştırılamadı: {exc}")
        else:
            if result.get("ok"):
                st.success("AI toplu değerlendirmesi tamamlandı ve arşivlendi.")
                latest = result.get("record")
                ai_review_status = "reviewed"
            else:
                error = result.get("error") or "AI değerlendirmesi tamamlanamadı."
                st.error(error)

    status_text = "Değerlendirilmedi"
    if ai_review_status == "reviewed" and latest:
        status_text = "Değerlendirildi"

    c1.metric("Rapor sayısı", document_count)
    c2.metric("AI durumu", status_text)

    if latest:
        _render_ai_review_record(st, latest)
    else:
        st.caption("Seçili tarih için henüz arşivlenmiş AI değerlendirmesi yok.")


def _render_ai_review_record(st, record: dict) -> None:
    output = record.get("output", {})
    if not isinstance(output, dict):
        output = {}

    st.markdown("### Son AI Değerlendirmesi")

    summary = output.get("summary")
    if summary:
        st.write(summary)
    else:
        st.caption("Özet üretilemedi.")

    left, right = st.columns(2)

    with left:
        st.markdown("**Olumlu faktörler**")
        _render_list(st, output.get("positive_factors", []), "Belirlenemedi")

    with right:
        st.markdown("**Risk faktörleri**")
        _render_list(st, output.get("risk_factors", []), "Belirlenemedi")

    with st.expander("Uyum, çelişki ve izlenecek başlıklar", expanded=False):
        st.markdown("**Kaynaklar arası uyumlu noktalar**")
        _render_list(st, output.get("aligned_points", []), "Belirlenemedi")

        st.markdown("**Çelişkili noktalar**")
        _render_list(st, output.get("conflicting_points", []), "Belirlenemedi")

        st.markdown("**İzlenecek başlıklar**")
        _render_list(st, output.get("watch_items", []), "Belirlenemedi")

    provider = record.get("provider") or "Bilinmiyor"
    model = record.get("model") or "Bilinmiyor"
    report_count = record.get("report_count", 0)
    created_at = record.get("created_at") or ""

    st.caption(
        f"Sağlayıcı: {provider} · Model: {model} · "
        f"Değerlendirilen rapor: {report_count} · Kayıt: {created_at}"
    )


def _render_list(st, values, empty_text: str) -> None:
    if isinstance(values, list) and values:
        for item in values:
            st.write(f"- {item}")
        return

    st.caption(empty_text)

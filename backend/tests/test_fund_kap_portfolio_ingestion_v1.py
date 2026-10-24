from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from backend.app.funds.kap_portfolio_ingestion import (
    KapFundPortfolioError,
    extract_kap_portfolio_pdf_payload,
    ingest_kap_portfolio_pdf_upload,
    ingest_kap_portfolio_report_url,
    parse_kap_portfolio_report_reference,
    parse_kap_portfolio_report_text,
)
from backend.app.funds.portfolio_tracking import FundPortfolioSnapshotJsonStore


DETAIL_URL = "https://www.kap.org.tr/tr/Bildirim/1614366"
ATTACHMENT_URL = "https://www.kap.org.tr/tr/api/file/download/abc123"
STAMP = datetime(2026, 9, 4, 8, 0, tzinfo=timezone.utc)


DETAIL_HTML = f"""
<html><body>
<div>Gönderim Tarihi 08.06.2026 12:08:03</div>
<div>Yıl 2026</div>
<div>Periyot 5. Aylık</div>
<div>Portföy Dağılım Raporu</div>
<a href="{ATTACHMENT_URL}">AP5 FON MAYIS 2026 PORTFÖY DAĞILIM RAPORU.pdf</a>
</body></html>
"""


REPORT_TEXT = """
AP5 FON MAYIS 2026 PORTFÖY DAĞILIM RAPORU
1- FONU TANITICI BİLGİLER
A. FONUN ADI : AP5-ATLAS PORTFÖY BEŞİNCİ HİSSE SENEDİ SERBEST FON (HİSSE SENEDİ YOĞUN FON)
3- FON PORTFÖY DEĞERİ TABLOSU
İhraççı Nominal Değeri Rayiç Değeri %
A) HİSSE SENETLERİ
SAHOL SABANCI HOLDING A.Ş 4.800,00 441.600,00 %45,66
TTKOM TÜRK TELEKOMÜNİKASYON A.Ş. 8.580,00 525.525,00 %54,34
TOPLAM: 13.380,00 967.125,00
B) VARANTLAR
C) DEVLET TAHVİLİ VE BONOLAR
"""


def test_reference_uses_kap_publication_and_month_end_contract():
    reference = parse_kap_portfolio_report_reference(DETAIL_HTML, detail_url=DETAIL_URL)
    assert reference.notification_id == "1614366"
    assert reference.portfolio_date.isoformat() == "2026-05-31"
    assert reference.publication_at.isoformat().startswith("2026-06-08T12:08:03")
    assert reference.attachment_url == ATTACHMENT_URL


def test_report_text_maps_real_equity_table_shape_to_snapshot():
    reference = parse_kap_portfolio_report_reference(DETAIL_HTML, detail_url=DETAIL_URL)
    snapshot = parse_kap_portfolio_report_text(REPORT_TEXT, reference=reference, ingested_at=STAMP)
    assert snapshot.canonical_fund_id == "fund:tefas:AP5"
    assert snapshot.provider == "KAP"
    assert snapshot.portfolio_date.isoformat() == "2026-05-31"
    assert snapshot.publication_date.isoformat() == "2026-06-08"
    assert [item.symbol for item in snapshot.positions] == ["SAHOL", "TTKOM"]
    by_symbol = {item.symbol: item for item in snapshot.positions}
    assert by_symbol["SAHOL"].shares_held == Decimal("4800.00")
    assert by_symbol["SAHOL"].market_value == Decimal("441600.00")
    assert by_symbol["SAHOL"].portfolio_weight == Decimal("0.4566")
    assert by_symbol["TTKOM"].portfolio_weight == Decimal("0.5434")


def test_report_text_accepts_real_pdf_extraction_order_when_fund_name_value_is_detached():
    reference = parse_kap_portfolio_report_reference(DETAIL_HTML, detail_url=DETAIL_URL)
    detached_name_text = REPORT_TEXT.replace(
        "A. FONUN ADI : AP5-ATLAS PORTFÖY BEŞİNCİ HİSSE SENEDİ SERBEST FON (HİSSE SENEDİ YOĞUN FON)",
        "A. FONUN ADI :\nAP5-ATLAS PORTFÖY BEŞİNCİ HİSSE SENEDİ SERBEST FON (HİSSE SENEDİ YOĞUN FON)",
    )
    snapshot = parse_kap_portfolio_report_text(
        detached_name_text,
        reference=reference,
        ingested_at=STAMP,
    )
    assert snapshot.canonical_fund_id == "fund:tefas:AP5"


def test_ingestion_is_explicit_bounded_and_idempotent(tmp_path):
    store = FundPortfolioSnapshotJsonStore(tmp_path / "portfolio_snapshots.json")
    calls = []

    def detail_fetcher(url, timeout):
        calls.append(("detail", url, timeout))
        return DETAIL_HTML.encode("utf-8"), DETAIL_URL, "text/html; charset=utf-8"

    def attachment_fetcher(url, timeout):
        calls.append(("pdf", url, timeout))
        return b"%PDF-fake", ATTACHMENT_URL, "application/pdf"

    with pytest.raises(KapFundPortfolioError, match="NETWORK_DISABLED"):
        ingest_kap_portfolio_report_url(
            DETAIL_URL,
            store=store,
            detail_fetcher=detail_fetcher,
            attachment_fetcher=attachment_fetcher,
            pdf_text_extractor=lambda _raw: REPORT_TEXT,
        )
    assert calls == []

    first = ingest_kap_portfolio_report_url(
        DETAIL_URL,
        store=store,
        network_enabled=True,
        ingested_at=STAMP,
        detail_fetcher=detail_fetcher,
        attachment_fetcher=attachment_fetcher,
        pdf_text_extractor=lambda _raw: REPORT_TEXT,
    )
    assert first.store_result.inserted == 1
    assert first.store_result.unchanged == 0
    assert len(store.list_snapshots()) == 1

    second = ingest_kap_portfolio_report_url(
        DETAIL_URL,
        store=store,
        network_enabled=True,
        ingested_at=datetime(2026, 9, 4, 9, 0, tzinfo=timezone.utc),
        detail_fetcher=detail_fetcher,
        attachment_fetcher=attachment_fetcher,
        pdf_text_extractor=lambda _raw: REPORT_TEXT,
    )
    assert second.store_result.inserted == 0
    assert second.store_result.unchanged == 1
    assert len(store.list_snapshots()) == 1


def test_multiple_pdf_attachments_fail_closed():
    html = DETAIL_HTML.replace(
        "</body>",
        '<a href="https://www.kap.org.tr/tr/api/file/download/second">FTD.pdf</a></body>',
    )
    with pytest.raises(KapFundPortfolioError, match="ATTACHMENT_AMBIGUOUS"):
        parse_kap_portfolio_report_reference(html, detail_url=DETAIL_URL)


def test_missing_equity_section_fails_closed():
    reference = parse_kap_portfolio_report_reference(DETAIL_HTML, detail_url=DETAIL_URL)
    with pytest.raises(KapFundPortfolioError, match="EQUITY_SECTION_MISSING"):
        parse_kap_portfolio_report_text(
            REPORT_TEXT.replace("A) HİSSE SENETLERİ", "A) PAYLAR"),
            reference=reference,
            ingested_at=STAMP,
        )


def test_manual_pdf_upload_ingests_without_network_and_keeps_kap_identity(tmp_path):
    store = FundPortfolioSnapshotJsonStore(tmp_path / "portfolio_snapshots.json")

    first = ingest_kap_portfolio_pdf_upload(
        b"%PDF-fake",
        filename="AP5 FON MAYIS 2026 PORTFÖY DAĞILIM RAPORU.pdf",
        report_year=2026,
        report_month=5,
        publication_date=date(2026, 6, 8),
        notification_id="1614366",
        source_reference="https://mirror.example/ap5-mayis.pdf",
        store=store,
        ingested_at=STAMP,
        pdf_text_extractor=lambda _raw: REPORT_TEXT,
    )

    assert first.snapshot.canonical_fund_id == "fund:tefas:AP5"
    assert first.snapshot.provider == "KAP"
    assert first.snapshot.portfolio_date.isoformat() == "2026-05-31"
    assert first.snapshot.publication_date.isoformat() == "2026-06-08"
    assert first.snapshot.source_reference == DETAIL_URL
    assert first.store_result.inserted == 1

    second = ingest_kap_portfolio_pdf_upload(
        b"%PDF-fake",
        filename="same-report.pdf",
        report_year=2026,
        report_month=5,
        publication_date=date(2026, 6, 8),
        source_reference="https://different.example/ap5.pdf",
        store=store,
        ingested_at=datetime(2026, 9, 4, 10, 0, tzinfo=timezone.utc),
        pdf_text_extractor=lambda _raw: REPORT_TEXT,
    )
    assert second.store_result.inserted == 0
    assert second.store_result.unchanged == 1
    assert len(store.list_snapshots()) == 1


def test_manual_pdf_upload_rejects_notification_page_print_without_holdings_table(tmp_path):
    store = FundPortfolioSnapshotJsonStore(tmp_path / "portfolio_snapshots.json")
    notification_page_text = """
    ATLAS PORTFÖY BEŞİNCİ HİSSE SENEDİ SERBEST FON AP5
    Gönderim Tarihi 10.08.2026 10:35:38
    Periyot 7. Aylık
    Bildirim Ekleri (1)
    AP5 FON TEMMUZ 2026 PORTFÖY DAĞILIM RAPORLARI.pdf
    """

    with pytest.raises(KapFundPortfolioError, match="NOT_PORTFOLIO_ATTACHMENT"):
        ingest_kap_portfolio_pdf_upload(
            b"%PDF-fake",
            filename="kap-bildirim-sayfasi.pdf",
            report_year=2026,
            report_month=7,
            publication_date=date(2026, 8, 10),
            notification_id="1646130",
            store=store,
            ingested_at=STAMP,
            pdf_text_extractor=lambda _raw: notification_page_text,
        )


def test_wrapped_pdf_payload_is_unwrapped_before_native_extraction():
    native = b"%PDF-1.7\nbody\n%%EOF"
    wrapped = b"\xac\xed\x00\x05transport-prefix" + native + b"transport-suffix"
    assert extract_kap_portfolio_pdf_payload(wrapped) == native


def test_non_pdf_payload_still_fails_closed():
    with pytest.raises(KapFundPortfolioError, match="ATTACHMENT_NOT_PDF"):
        extract_kap_portfolio_pdf_payload(b"not-a-pdf")

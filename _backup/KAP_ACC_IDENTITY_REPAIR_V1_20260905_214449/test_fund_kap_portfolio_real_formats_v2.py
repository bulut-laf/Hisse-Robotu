from datetime import datetime, timezone
from backend.app.funds.kap_portfolio_ingestion import KapPortfolioReportReference, MAX_KAP_PORTFOLIO_PDF_PAGES, parse_kap_portfolio_report_text

STAMP = datetime(2026, 9, 5, 20, 30, tzinfo=timezone.utc)

def _ref(name):
    return KapPortfolioReportReference(notification_id="9999999", detail_url="https://www.kap.org.tr/tr/Bildirim/9999999", attachment_url="https://www.kap.org.tr/tr/api/file/download/test", attachment_name=name, publication_at=STAMP, report_year=2026, report_month=6)

def test_real_yapi_kredi_text_native_holdings_format_and_filename_identity():
    text = """YAPI KREDİ PORTFÖY YÖNETİMİ A.Ş.
A. FONUN ADI : YAPI KREDİ PORTFÖY BİRİNCİ HİSSE SENEDİ FONU
III- FON PORTFÖY DEĞERİ TABLOSU
:A) HİSSE SENETLERİ
Akbank 1,560,245.35 120,138,891.80 3.33TRAAKBNK91N6AKBNK
Aselsan 825,000.00 284,625,000.00 7.90TRAASELS91H2ASELS
:O) TAKASBANK PARA PİYASASI
IV- FON TOPLAM DEĞERİ TABLOSU
"""
    snap = parse_kap_portfolio_report_text(text, reference=_ref("YHS.pdf"), ingested_at=STAMP)
    assert snap.canonical_fund_id == "fund:tefas:YHS"
    by_symbol = {p.symbol: p for p in snap.positions}
    assert set(by_symbol) == {"AKBNK", "ASELS"}
    assert str(by_symbol["AKBNK"].shares_held) == "1560245.35"
    assert str(by_symbol["AKBNK"].market_value) == "120138891.80"
    assert str(by_symbol["AKBNK"].portfolio_weight) == "0.0333"

def test_real_acc_split_tabular_holdings_format():
    text = """ACC - İSTANBUL PORTFÖY DÖRDÜNCÜ HİSSE SENEDİ FONU
III-FON PORTFÖY DEĞERİ TABLOSU
HİSSE SENETLERİ
Hisse Türk
AKBNK AKBANK
T.A.Ş.
120.000,00 67,722029 10/06/26 77,000000 9.240.000,00 5,48 4,86TL 80100511 4,91TRAAKBNK91N6
BETAE BETA
ENERJİ VE
TEKNOLOJİ
A.Ş.
10.000,00 40,000000 30/06/26 40,000000 400.000,00 0,24 0,21TL 0,21TREBTAE00025
GRUP TOPLAMI
IV-FON TOPLAM DEĞERİ TABLOSU
"""
    snap = parse_kap_portfolio_report_text(text, reference=_ref("ACC_2026.06.pdf"), ingested_at=STAMP)
    assert snap.canonical_fund_id == "fund:tefas:ACC"
    by_symbol = {p.symbol: p for p in snap.positions}
    assert set(by_symbol) == {"AKBNK", "BETAE"}
    assert str(by_symbol["AKBNK"].shares_held) == "120000.00"
    assert str(by_symbol["AKBNK"].market_value) == "9240000.00"
    assert str(by_symbol["AKBNK"].portfolio_weight) == "0.0486"

def test_numeric_expense_code_cannot_become_fund_identity():
    text = """UPH-ÜNLÜ PORTFÖY HİSSE SENEDİ (TL) FONU
III-FON PORTFÖY DEĞERİ TABLOSU
:A) HİSSE SENETLERİ
Akbank 10,000.00 770,000.00 1.00TRAAKBNK91N6AKBNK
:B) VARANTLAR
IV-FON TOPLAM DEĞERİ TABLOSU
370001 Fon Yönetim Ücreti
"""
    snap = parse_kap_portfolio_report_text(text, reference=_ref("UPH HAZİRAN 2026 PORTFÖY DAĞILIM RAPORU.pdf"), ingested_at=STAMP)
    assert snap.canonical_fund_id == "fund:tefas:UPH"

def test_observed_real_report_page_bound_is_supported():
    assert MAX_KAP_PORTFOLIO_PDF_PAGES >= 129


def test_split_tabular_uppercase_name_continuation_does_not_become_symbol():
    text = """
ACC - İSTANBUL PORTFÖY DÖRDÜNCÜ HİSSE SENEDİ FONU
III-FON PORTFÖY DEĞERİ TABLOSU
HİSSE SENETLERİ
Hisse Türk
RGYAS RÖNESANS
GAYRİMENKUL
Y.O
20.000,00 204,215511 08/06/26 193,400000 3.868.000,00 2,30 2,04TL 80100511 2,05TRERSGY00036
TCKRC KIRAÇ
GALVANİZ
TELEKOMÜNİKASYON
METAL
MAKİNE
İNŞAAT VE SANAYİ A.Ş.
110.000,00 62,917228 02/06/26 164,000000 18.040.000,00 10,72 9,48TL 80100511 9,58TREKIRC00019
IV-FON TOPLAM DEĞERİ TABLOSU
"""
    snap = parse_kap_portfolio_report_text(text, reference=_ref("ACC_2026.06.pdf"), ingested_at=STAMP)
    symbols = {p.symbol for p in snap.positions}
    assert "RGYAS" in symbols
    assert "TCKRC" in symbols
    assert "KUL" not in symbols
    assert "INSAAT" not in symbols

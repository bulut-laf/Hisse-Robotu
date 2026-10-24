from __future__ import annotations

import csv
from dataclasses import dataclass
from io import BytesIO, StringIO
import math
import os
from pathlib import Path
import re
import unicodedata
from typing import TYPE_CHECKING, Iterable, Mapping, Sequence
from xml.sax.saxutils import escape

if TYPE_CHECKING:
    from .backtest_dashboard import DashboardResult
    from .portfolio_dashboard import PortfolioDashboardResult


UTF8_BOM = b"\xef\xbb\xbf"


class ReportExportError(RuntimeError):
    """Rapor dışa aktarımı kullanıcıya gösterilebilir biçimde başarısız oldu."""


@dataclass(frozen=True)
class ExportFileNames:
    """Bir analiz sonucu için güvenli CSV ve PDF dosya adları."""

    csv: str
    pdf: str


@dataclass(frozen=True)
class PortfolioExportFileNames:
    """Portföy sonucu için güvenli dışa aktarım dosya adları."""

    contribution_csv: str
    equity_csv: str
    pdf: str


def guvenli_dosya_parcasi(deger: object, *, maksimum: int = 96) -> str:
    """Dosya adında güvenle kullanılabilecek ASCII bir parça üretir."""

    metin = str(deger).strip()
    if not metin:
        return "rapor"

    turkce_donusum = str.maketrans(
        {
            "ç": "c",
            "Ç": "C",
            "ğ": "g",
            "Ğ": "G",
            "ı": "i",
            "İ": "I",
            "ö": "o",
            "Ö": "O",
            "ş": "s",
            "Ş": "S",
            "ü": "u",
            "Ü": "U",
        }
    )
    metin = metin.translate(turkce_donusum)
    metin = unicodedata.normalize("NFKD", metin)
    metin = metin.encode("ascii", "ignore").decode("ascii")
    metin = re.sub(r"[^A-Za-z0-9]+", "_", metin).strip("_")
    metin = re.sub(r"_+", "_", metin)
    return (metin[:maksimum] or "rapor")


def tek_hisse_dosya_adlari(sonuc: DashboardResult) -> ExportFileNames:
    ozet = sonuc.ozet
    sembol = guvenli_dosya_parcasi(ozet.sembol)
    analiz = guvenli_dosya_parcasi(ozet.analiz_kimligi)
    kok = f"{sembol}_backtest_{analiz}"
    return ExportFileNames(csv=f"{kok}_islemler.csv", pdf=f"{kok}_rapor.pdf")


def portfoy_dosya_adlari(
    sonuc: PortfolioDashboardResult,
) -> PortfolioExportFileNames:
    ozet = sonuc.ozet
    semboller = guvenli_dosya_parcasi("_".join(ozet.semboller), maksimum=72)
    veri = guvenli_dosya_parcasi(ozet.portfoy_veri_kimligi)
    kok = f"portfoy_{semboller}_{veri}"
    return PortfolioExportFileNames(
        contribution_csv=f"{kok}_katki.csv",
        equity_csv=f"{kok}_gunluk_ozsermaye.csv",
        pdf=f"{kok}_rapor.pdf",
    )


def _csv_degeri(deger: object) -> object:
    if deger is None:
        return ""
    if isinstance(deger, float):
        if not math.isfinite(deger):
            return ""
        return f"{deger:.6f}".rstrip("0").rstrip(".")
    return deger


def csv_baytlari(
    sutunlar: Sequence[str],
    kayitlar: Iterable[Mapping[str, object]],
) -> bytes:
    """UTF-8 BOM ve noktalı virgül ayırıcıyla Excel uyumlu CSV üretir."""

    cikti = StringIO(newline="")
    yazici = csv.DictWriter(
        cikti,
        fieldnames=list(sutunlar),
        delimiter=";",
        lineterminator="\n",
        extrasaction="ignore",
    )
    yazici.writeheader()
    for kayit in kayitlar:
        yazici.writerow(
            {sutun: _csv_degeri(kayit.get(sutun)) for sutun in sutunlar}
        )
    return UTF8_BOM + cikti.getvalue().encode("utf-8")


def tek_hisse_islem_csv_baytlari(sonuc: DashboardResult) -> bytes:
    sutunlar = (
        "No",
        "Sinyal",
        "Giriş",
        "Çıkış",
        "Skor",
        "Giriş Fiyatı",
        "Çıkış Fiyatı",
        "Net Getiri (%)",
        "Bar",
        "Çıkış Nedeni",
    )
    return csv_baytlari(sutunlar, sonuc.islem_kayitlari())


def portfoy_katki_csv_baytlari(
    sonuc: PortfolioDashboardResult,
) -> bytes:
    sutunlar = (
        "Sembol",
        "İşlem",
        "Kazanma (%)",
        "Toplam Ayrılan Sermaye",
        "Net Kâr",
        "Başlangıca Katkı (%)",
    )
    return csv_baytlari(sutunlar, sonuc.katki_kayitlari())


def portfoy_ozsermaye_csv_baytlari(
    sonuc: PortfolioDashboardResult,
) -> bytes:
    sutunlar = (
        "Tarih",
        "Özsermaye",
        "Düşüş (%)",
        "Açık Pozisyon",
        "Sermaye Kullanımı (%)",
    )
    return csv_baytlari(sutunlar, sonuc.ozsermaye_kayitlari())


def _reportlab_bilesenleri() -> dict[str, object]:
    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER, TA_LEFT
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.platypus import (
            KeepTogether,
            PageBreak,
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )
    except ImportError as hata:
        raise ReportExportError(
            "PDF raporu için reportlab paketi gereklidir. "
            "backend/requirements-dashboard.txt dosyasını kurun."
        ) from hata

    return {
        "colors": colors,
        "TA_CENTER": TA_CENTER,
        "TA_LEFT": TA_LEFT,
        "A4": A4,
        "landscape": landscape,
        "ParagraphStyle": ParagraphStyle,
        "getSampleStyleSheet": getSampleStyleSheet,
        "mm": mm,
        "pdfmetrics": pdfmetrics,
        "TTFont": TTFont,
        "KeepTogether": KeepTogether,
        "PageBreak": PageBreak,
        "Paragraph": Paragraph,
        "SimpleDocTemplate": SimpleDocTemplate,
        "Spacer": Spacer,
        "Table": Table,
        "TableStyle": TableStyle,
    }


def _font_adaylari() -> tuple[tuple[Path, Path], ...]:
    windows = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
    return (
        (windows / "arial.ttf", windows / "arialbd.ttf"),
        (windows / "segoeui.ttf", windows / "segoeuib.ttf"),
        (windows / "calibri.ttf", windows / "calibrib.ttf"),
        (
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        ),
        (
            Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"),
            Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"),
        ),
    )


def _pdf_fontlarini_kaydet(bilesenler: Mapping[str, object]) -> tuple[str, str, bool]:
    pdfmetrics = bilesenler["pdfmetrics"]
    TTFont = bilesenler["TTFont"]
    normal_adi = "HisseRobotuSans"
    kalin_adi = "HisseRobotuSansBold"

    for normal_yol, kalin_yol in _font_adaylari():
        if not normal_yol.exists():
            continue
        kalin_yol = kalin_yol if kalin_yol.exists() else normal_yol
        try:
            kayitli = pdfmetrics.getRegisteredFontNames()
            if normal_adi not in kayitli:
                pdfmetrics.registerFont(TTFont(normal_adi, str(normal_yol)))
            kayitli = pdfmetrics.getRegisteredFontNames()
            if kalin_adi not in kayitli:
                pdfmetrics.registerFont(TTFont(kalin_adi, str(kalin_yol)))
            return normal_adi, kalin_adi, True
        except Exception:
            continue

    return "Helvetica", "Helvetica-Bold", False


def _ascii_pdf_metni(metin: object) -> str:
    donusum = str.maketrans(
        {
            "ç": "c",
            "Ç": "C",
            "ğ": "g",
            "Ğ": "G",
            "ı": "i",
            "İ": "I",
            "ö": "o",
            "Ö": "O",
            "ş": "s",
            "Ş": "S",
            "ü": "u",
            "Ü": "U",
            "—": "-",
            "–": "-",
            "’": "'",
        }
    )
    sonuc = unicodedata.normalize("NFKD", str(metin).translate(donusum))
    return sonuc.encode("ascii", "ignore").decode("ascii")


def _pdf_metni(metin: object, unicode_destekli: bool) -> str:
    deger = str(metin)
    return deger if unicode_destekli else _ascii_pdf_metni(deger)


def _sayi_yaz(deger: float | int | None, *, yuzde: bool = False) -> str:
    if deger is None:
        return "-"
    if isinstance(deger, float) and not math.isfinite(deger):
        return "-"
    son = f"{float(deger):,.2f}"
    return f"%{son}" if yuzde else son


def dengeli_sayfa_boyutlari(
    toplam_satir: int,
    maksimum_satir: int = 24,
) -> tuple[int, ...]:
    """Tablo satırlarını küçük bir son sayfa bırakmadan dengeler.

    Sayfa sayısı önce ``maksimum_satir`` sınırından hesaplanır; ardından
    satırlar sayfalara mümkün olduğunca eşit dağıtılır.
    """

    if toplam_satir < 0:
        raise ValueError("Toplam satır sayısı negatif olamaz.")
    if maksimum_satir <= 0:
        raise ValueError("Maksimum satır sayısı pozitif olmalıdır.")
    if toplam_satir == 0:
        return ()

    sayfa_sayisi = math.ceil(toplam_satir / maksimum_satir)
    taban, fazladan = divmod(toplam_satir, sayfa_sayisi)
    return tuple(
        taban + (1 if sira < fazladan else 0)
        for sira in range(sayfa_sayisi)
    )


def _dengeli_kayit_sayfalari(
    kayitlar: Sequence[Mapping[str, object]],
    *,
    maksimum_satir: int = 24,
) -> tuple[tuple[Mapping[str, object], ...], ...]:
    boyutlar = dengeli_sayfa_boyutlari(len(kayitlar), maksimum_satir)
    sayfalar: list[tuple[Mapping[str, object], ...]] = []
    baslangic = 0
    for boyut in boyutlar:
        bitis = baslangic + boyut
        sayfalar.append(tuple(kayitlar[baslangic:bitis]))
        baslangic = bitis
    return tuple(sayfalar)


def _pdf_stilleri(
    bilesenler: Mapping[str, object],
    normal_font: str,
    kalin_font: str,
) -> dict[str, object]:
    ParagraphStyle = bilesenler["ParagraphStyle"]
    TA_CENTER = bilesenler["TA_CENTER"]
    TA_LEFT = bilesenler["TA_LEFT"]
    mm = bilesenler["mm"]

    return {
        "baslik": ParagraphStyle(
            "HisseRobotuBaslik",
            fontName=kalin_font,
            fontSize=20,
            leading=24,
            alignment=TA_CENTER,
            spaceAfter=6 * mm,
        ),
        "alt_baslik": ParagraphStyle(
            "HisseRobotuAltBaslik",
            fontName=kalin_font,
            fontSize=12,
            leading=15,
            alignment=TA_LEFT,
            spaceBefore=4 * mm,
            spaceAfter=2 * mm,
        ),
        "bolum_baslik": ParagraphStyle(
            "HisseRobotuBolumBaslik",
            fontName=kalin_font,
            fontSize=10.5,
            leading=12,
            alignment=TA_LEFT,
            spaceBefore=1.5 * mm,
            spaceAfter=1 * mm,
        ),
        "govde": ParagraphStyle(
            "HisseRobotuGovde",
            fontName=normal_font,
            fontSize=8.5,
            leading=11,
            alignment=TA_LEFT,
        ),
        "kucuk": ParagraphStyle(
            "HisseRobotuKucuk",
            fontName=normal_font,
            fontSize=7,
            leading=9,
            alignment=TA_LEFT,
        ),
        "uyari": ParagraphStyle(
            "HisseRobotuUyari",
            fontName=normal_font,
            fontSize=8,
            leading=10,
            alignment=TA_CENTER,
            textColor=bilesenler["colors"].HexColor("#555555"),
            spaceAfter=4 * mm,
        ),
    }


def _paragraf(
    bilesenler: Mapping[str, object],
    metin: object,
    stil: object,
    unicode_destekli: bool,
) -> object:
    Paragraph = bilesenler["Paragraph"]
    temiz = escape(_pdf_metni(metin, unicode_destekli)).replace("\n", "<br/>")
    return Paragraph(temiz, stil)


def _tablo_stili(
    bilesenler: Mapping[str, object],
    normal_font: str,
    kalin_font: str,
    *,
    govde_boyutu: float = 7.0,
) -> object:
    colors = bilesenler["colors"]
    TableStyle = bilesenler["TableStyle"]
    return TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8EDF3")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1F2937")),
            ("FONTNAME", (0, 0), (-1, 0), kalin_font),
            ("FONTNAME", (0, 1), (-1, -1), normal_font),
            ("FONTSIZE", (0, 0), (-1, 0), govde_boyutu),
            ("FONTSIZE", (0, 1), (-1, -1), govde_boyutu),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#B8C0CC")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
        ]
    )


def _ozet_tablosu(
    bilesenler: Mapping[str, object],
    satirlar: Sequence[tuple[str, str]],
    normal_font: str,
    kalin_font: str,
    unicode_destekli: bool,
) -> object:
    Table = bilesenler["Table"]
    veriler = [["Ölçüt", "Değer"]]
    veriler.extend(
        [
            _pdf_metni(etiket, unicode_destekli),
            _pdf_metni(deger, unicode_destekli),
        ]
        for etiket, deger in satirlar
    )
    tablo = Table(veriler, colWidths=[250, 250], repeatRows=1)
    tablo.setStyle(
        _tablo_stili(
            bilesenler,
            normal_font,
            kalin_font,
            govde_boyutu=8.0,
        )
    )
    return tablo


def _cift_ozet_tablosu(
    bilesenler: Mapping[str, object],
    satirlar: Sequence[tuple[str, str]],
    normal_font: str,
    kalin_font: str,
    unicode_destekli: bool,
) -> object:
    """Özet ölçütlerini dört sütunda daha az dikey alanla gösterir."""

    Table = bilesenler["Table"]
    veriler: list[list[object]] = [["Ölçüt", "Değer", "Ölçüt", "Değer"]]
    yarim = math.ceil(len(satirlar) / 2)
    sol = tuple(satirlar[:yarim])
    sag = tuple(satirlar[yarim:])
    for sira in range(yarim):
        sol_etiket, sol_deger = sol[sira]
        if sira < len(sag):
            sag_etiket, sag_deger = sag[sira]
        else:
            sag_etiket, sag_deger = "", ""
        veriler.append(
            [
                _pdf_metni(sol_etiket, unicode_destekli),
                _pdf_metni(sol_deger, unicode_destekli),
                _pdf_metni(sag_etiket, unicode_destekli),
                _pdf_metni(sag_deger, unicode_destekli),
            ]
        )

    tablo = Table(veriler, colWidths=[145, 130, 145, 130], repeatRows=1)
    tablo.setStyle(
        _tablo_stili(
            bilesenler,
            normal_font,
            kalin_font,
            govde_boyutu=7.5,
        )
    )
    return tablo


def _sayfa_altligi(
    bilesenler: Mapping[str, object],
    normal_font: str,
    unicode_destekli: bool,
):
    mm = bilesenler["mm"]

    def ciz(canvas: object, doc: object) -> None:
        canvas.saveState()
        canvas.setFont(normal_font, 7)
        canvas.setFillColor(bilesenler["colors"].HexColor("#6B7280"))
        canvas.drawString(
            14 * mm,
            8 * mm,
            _pdf_metni(
                "Hisse Robotu - Kişisel analiz amaçlıdır, yatırım tavsiyesi değildir.",
                unicode_destekli,
            ),
        )
        canvas.drawRightString(
            doc.pagesize[0] - 14 * mm,
            8 * mm,
            _pdf_metni(f"Sayfa {doc.page}", unicode_destekli),
        )
        canvas.restoreState()

    return ciz


def _tek_hisse_islem_tablosu(
    bilesenler: Mapping[str, object],
    kayitlar: Sequence[Mapping[str, object]],
    normal_font: str,
    kalin_font: str,
    unicode_destekli: bool,
) -> object:
    basliklar = (
        "No",
        "Sinyal",
        "Giriş",
        "Çıkış",
        "Skor",
        "Giriş Fiyatı",
        "Çıkış Fiyatı",
        "Net Getiri (%)",
        "Bar",
        "Çıkış Nedeni",
    )
    tablo_verisi: list[list[object]] = [
        [_pdf_metni(baslik, unicode_destekli) for baslik in basliklar]
    ]
    for kayit in kayitlar:
        tablo_verisi.append(
            [
                kayit["No"],
                kayit["Sinyal"],
                kayit["Giriş"],
                kayit["Çıkış"],
                kayit["Skor"],
                _sayi_yaz(float(kayit["Giriş Fiyatı"])),
                _sayi_yaz(float(kayit["Çıkış Fiyatı"])),
                _sayi_yaz(float(kayit["Net Getiri (%)"]), yuzde=True),
                kayit["Bar"],
                _pdf_metni(kayit["Çıkış Nedeni"], unicode_destekli),
            ]
        )

    tablo = bilesenler["Table"](
        tablo_verisi,
        colWidths=[28, 60, 60, 60, 32, 58, 58, 60, 30, 72],
        repeatRows=1,
    )
    tablo.setStyle(
        _tablo_stili(
            bilesenler,
            normal_font,
            kalin_font,
            govde_boyutu=6.2,
        )
    )
    return tablo


def tek_hisse_pdf_baytlari(sonuc: DashboardResult) -> bytes:
    b = _reportlab_bilesenleri()
    normal_font, kalin_font, unicode_destekli = _pdf_fontlarini_kaydet(b)
    stiller = _pdf_stilleri(b, normal_font, kalin_font)
    tampon = BytesIO()
    mm = b["mm"]
    sayfa = b["landscape"](b["A4"])
    belge = b["SimpleDocTemplate"](
        tampon,
        pagesize=sayfa,
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=15 * mm,
        title="Hisse Robotu - Tek Hisse Backtest Raporu",
        author="Hisse Robotu",
    )

    ozet = sonuc.ozet
    islemler = sonuc.islem_kayitlari()
    islem_sayfalari = _dengeli_kayit_sayfalari(
        islemler,
        maksimum_satir=24,
    )
    hikaye: list[object] = [
        _paragraf(b, "Hisse Robotu", stiller["baslik"], unicode_destekli),
        _paragraf(
            b,
            f"{ozet.sembol} - Tek Hisse Backtest Raporu",
            stiller["alt_baslik"],
            unicode_destekli,
        ),
        _paragraf(
            b,
            "Bu rapor geçmiş veriye dayalıdır. Kişisel analiz amaçlıdır ve yatırım tavsiyesi değildir.",
            stiller["uyari"],
            unicode_destekli,
        ),
        _ozet_tablosu(
            b,
            (
                ("Fiyat dönemi", ozet.fiyat_donemi),
                ("Fiyat barı", str(ozet.fiyat_bar_sayisi)),
                ("Tamamlanan işlem", str(ozet.tamamlanan_islem_sayisi)),
                ("Atlanan sinyal", str(ozet.atlanan_sinyal_sayisi)),
                ("Bitiş sermayesi", _sayi_yaz(ozet.bitis_sermayesi)),
                ("Toplam getiri", _sayi_yaz(ozet.toplam_getiri_yuzde, yuzde=True)),
                ("Kazanma oranı", _sayi_yaz(ozet.kazanma_yuzde, yuzde=True)),
                ("Maksimum düşüş", _sayi_yaz(ozet.maksimum_dusus_yuzde, yuzde=True)),
                ("Güncel düşüş", _sayi_yaz(ozet.guncel_dusus_yuzde, yuzde=True)),
                ("Kâr faktörü", _sayi_yaz(ozet.kar_faktoru)),
                ("Hizalanmış Al-Tut", _sayi_yaz(ozet.al_tut_getiri_yuzde, yuzde=True)),
                ("İşlem ayrıntısı sayfası", str(len(islem_sayfalari))),
                ("Analiz kimliği", ozet.analiz_kimligi),
                ("Veri kimliği", ozet.veri_kimligi),
                ("Ayar kimliği", ozet.ayar_kimligi),
            ),
            normal_font,
            kalin_font,
            unicode_destekli,
        ),
    ]

    if islem_sayfalari:
        toplam_sayfa = len(islem_sayfalari)
        for sayfa_sirasi, sayfa_kayitlari in enumerate(islem_sayfalari, start=1):
            hikaye.append(b["PageBreak"]())
            hikaye.append(
                _paragraf(
                    b,
                    f"Tamamlanan işlemler ({sayfa_sirasi}/{toplam_sayfa})",
                    stiller["alt_baslik"],
                    unicode_destekli,
                )
            )
            hikaye.append(
                _tek_hisse_islem_tablosu(
                    b,
                    sayfa_kayitlari,
                    normal_font,
                    kalin_font,
                    unicode_destekli,
                )
            )
    else:
        hikaye.extend(
            [
                b["Spacer"](1, 5 * mm),
                _paragraf(
                    b,
                    "Tamamlanan işlemler",
                    stiller["alt_baslik"],
                    unicode_destekli,
                ),
                _paragraf(
                    b,
                    "Seçilen ayarlarda tamamlanan işlem bulunamadı.",
                    stiller["govde"],
                    unicode_destekli,
                ),
            ]
        )

    altlik = _sayfa_altligi(b, normal_font, unicode_destekli)
    belge.build(hikaye, onFirstPage=altlik, onLaterPages=altlik)
    veri = tampon.getvalue()
    if not veri.startswith(b"%PDF-"):
        raise ReportExportError("PDF raporu üretilemedi.")
    return veri


def portfoy_pdf_baytlari(sonuc: PortfolioDashboardResult) -> bytes:
    b = _reportlab_bilesenleri()
    normal_font, kalin_font, unicode_destekli = _pdf_fontlarini_kaydet(b)
    stiller = _pdf_stilleri(b, normal_font, kalin_font)
    tampon = BytesIO()
    mm = b["mm"]
    sayfa = b["landscape"](b["A4"])
    belge = b["SimpleDocTemplate"](
        tampon,
        pagesize=sayfa,
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=15 * mm,
        title="Hisse Robotu - Portföy Backtest Raporu",
        author="Hisse Robotu",
    )

    ozet = sonuc.ozet
    semboller = ", ".join(ozet.semboller)
    hikaye: list[object] = [
        _paragraf(b, "Hisse Robotu", stiller["baslik"], unicode_destekli),
        _paragraf(
            b,
            "Çoklu Hisse Portföy Backtest Raporu",
            stiller["alt_baslik"],
            unicode_destekli,
        ),
        _paragraf(
            b,
            "Bu rapor geçmiş veriye dayalıdır. Kişisel analiz amaçlıdır ve yatırım tavsiyesi değildir.",
            stiller["uyari"],
            unicode_destekli,
        ),
        _cift_ozet_tablosu(
            b,
            (
                ("Semboller", semboller),
                ("Portföy dönemi", ozet.portfoy_donemi),
                ("Tamamlanan işlem", str(ozet.tamamlanan_islem_sayisi)),
                ("Atlanan işlem", str(ozet.atlanan_islem_sayisi)),
                ("Bitiş sermayesi", _sayi_yaz(ozet.bitis_sermayesi)),
                ("Toplam getiri", _sayi_yaz(ozet.toplam_getiri_yuzde, yuzde=True)),
                ("Maksimum düşüş", _sayi_yaz(ozet.maksimum_dusus_yuzde, yuzde=True)),
                ("Güncel düşüş", _sayi_yaz(ozet.guncel_dusus_yuzde, yuzde=True)),
                ("Kâr faktörü", _sayi_yaz(ozet.kar_faktoru)),
                ("Ortalama sermaye kullanımı", _sayi_yaz(ozet.ortalama_sermaye_kullanim_yuzde, yuzde=True)),
                ("Maksimum sermaye kullanımı", _sayi_yaz(ozet.maksimum_sermaye_kullanim_yuzde, yuzde=True)),
                ("Gerçekleşen maksimum pozisyon", str(ozet.gerceklesen_maksimum_pozisyon)),
                ("Ayar kimliği", ozet.ayar_kimligi),
                ("Portföy veri kimliği", ozet.portfoy_veri_kimligi),
            ),
            normal_font,
            kalin_font,
            unicode_destekli,
        ),
        b["Spacer"](1, 1 * mm),
        _paragraf(b, "Hisse bazlı katkı", stiller["alt_baslik"], unicode_destekli),
    ]

    katkilar = sonuc.katki_kayitlari()
    if katkilar:
        basliklar = (
            "Sembol",
            "İşlem",
            "Kazanma (%)",
            "Toplam Ayrılan Sermaye",
            "Net Kâr",
            "Başlangıca Katkı (%)",
        )
        tablo_verisi: list[list[object]] = [
            [_pdf_metni(baslik, unicode_destekli) for baslik in basliklar]
        ]
        for kayit in katkilar:
            tablo_verisi.append(
                [
                    kayit["Sembol"],
                    kayit["İşlem"],
                    _sayi_yaz(float(kayit["Kazanma (%)"]), yuzde=True),
                    _sayi_yaz(float(kayit["Toplam Ayrılan Sermaye"])),
                    _sayi_yaz(float(kayit["Net Kâr"])),
                    _sayi_yaz(float(kayit["Başlangıca Katkı (%)"]), yuzde=True),
                ]
            )
        tablo = b["Table"](
            tablo_verisi,
            colWidths=[85, 55, 80, 135, 105, 115],
            repeatRows=1,
        )
        tablo.setStyle(
            _tablo_stili(b, normal_font, kalin_font, govde_boyutu=7.5)
        )
        hikaye.append(tablo)
    else:
        hikaye.append(
            _paragraf(
                b,
                "Hisse bazlı katkı kaydı bulunamadı.",
                stiller["govde"],
                unicode_destekli,
            )
        )

    ozsermaye = sonuc.ozsermaye_kayitlari()
    ozsermaye_bolumu: list[object] = [
        b["Spacer"](1, 1 * mm),
        _paragraf(
            b,
            "Günlük özsermaye özeti",
            stiller["bolum_baslik"],
            unicode_destekli,
        ),
    ]
    if ozsermaye:
        ozsermaye_degerleri = [float(k["Özsermaye"]) for k in ozsermaye]
        dusus_degerleri = [float(k["Düşüş (%)"]) for k in ozsermaye]
        ozsermaye_bolumu.append(
            _ozet_tablosu(
                b,
                (
                    ("İlk tarih", str(ozsermaye[0]["Tarih"])),
                    ("Son tarih", str(ozsermaye[-1]["Tarih"])),
                    ("Günlük nokta", str(len(ozsermaye))),
                    (
                        "En düşük özsermaye",
                        _sayi_yaz(min(ozsermaye_degerleri)),
                    ),
                    (
                        "En yüksek özsermaye",
                        _sayi_yaz(max(ozsermaye_degerleri)),
                    ),
                    (
                        "En yüksek günlük düşüş",
                        _sayi_yaz(max(dusus_degerleri), yuzde=True),
                    ),
                ),
                normal_font,
                kalin_font,
                unicode_destekli,
            )
        )
    else:
        ozsermaye_bolumu.append(
            _paragraf(
                b,
                "Günlük özsermaye kaydı bulunamadı.",
                stiller["govde"],
                unicode_destekli,
            )
        )
    hikaye.append(b["KeepTogether"](ozsermaye_bolumu))

    atlanmalar = sonuc.atlanma_kayitlari()
    if atlanmalar:
        tablo_verisi = [["Neden", "Adet"]]
        tablo_verisi.extend(
            [
                _pdf_metni(kayit["Neden"], unicode_destekli),
                kayit["Adet"],
            ]
            for kayit in atlanmalar
        )
        tablo = b["Table"](
            tablo_verisi,
            colWidths=[430, 70],
            repeatRows=1,
        )
        tablo.setStyle(
            _tablo_stili(b, normal_font, kalin_font, govde_boyutu=8.0)
        )
        hikaye.append(
            b["KeepTogether"](
                [
                    b["Spacer"](1, 1 * mm),
                    _paragraf(
                        b,
                        "Atlanan işlem nedenleri",
                        stiller["alt_baslik"],
                        unicode_destekli,
                    ),
                    tablo,
                ]
            )
        )

    altlik = _sayfa_altligi(b, normal_font, unicode_destekli)
    belge.build(hikaye, onFirstPage=altlik, onLaterPages=altlik)
    veri = tampon.getvalue()
    if not veri.startswith(b"%PDF-"):
        raise ReportExportError("PDF raporu üretilemedi.")
    return veri

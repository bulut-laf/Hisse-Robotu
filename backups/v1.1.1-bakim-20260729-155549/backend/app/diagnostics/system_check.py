from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import importlib.util
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from time import perf_counter
from typing import Callable

import numpy as np
import pandas as pd

from ..analysis.position_monitor import OpenPosition, acik_pozisyonu_izle
from ..analysis.loss_analysis import analyze_trade_losses
from ..history.trade_journal import GERCEK_HESAP, TradeRecord
from ..risk.safety_lock import (
    SafetyLockContext,
    SafetyPolicy,
    TradeProposal,
    evaluate_trade_safety,
)
from ..analysis.momentum_discovery import MomentumDiscoveryEngine
from ..analysis.momentum_walk_forward import MomentumWalkForwardEngine
from ..analysis.bist_universe import BistUniverseRepository
from ..analysis.stock_scanner import BatchStockScanner
from ..data.batch_market_data import BatchMarketDataResult
from ..analysis.technical_confirmation import teknik_teyit_analizi_yap
from ..analysis.trade_plan import islem_plani_olustur
from ..backtest.backtest_service import StockBacktestService
from ..data.data_freshness import gunluk_veri_tazeligini_degerlendir
from ..data.multi_timeframe_data import (
    GUNLUK,
    HAFTALIK,
    SAATLIK,
    MultiTimeframeDataBundle,
    TimeframeSnapshot,
)
from ..history.backtest_history import BacktestHistoryStore, varsayilan_gecmis_klasoru
from ..ui.backtest_dashboard import (
    BacktestDashboardService,
    DashboardBacktestRequest,
    DashboardResult,
)
from ..ui.report_export import (
    tek_hisse_islem_csv_baytlari,
    tek_hisse_pdf_baytlari,
)


BASARILI = "Başarılı"
UYARI = "Uyarı"
BASARISIZ = "Başarısız"
GECERLI_DURUMLAR = (BASARILI, UYARI, BASARISIZ)
SISTEM_KONTROL_SURUMU = "V1.1"
MINIMUM_PYTHON = (3, 11)

ModuleFinder = Callable[[str], object | None]


@dataclass(frozen=True)
class SystemCheckItem:
    """Tek sistem kontrolünün kullanıcıya gösterilebilir sonucu."""

    ad: str
    durum: str
    aciklama: str
    kritik: bool = True
    sure_ms: float = 0.0

    def __post_init__(self) -> None:
        if not self.ad.strip():
            raise ValueError("Kontrol adı boş olamaz.")
        if self.durum not in GECERLI_DURUMLAR:
            raise ValueError(f"Geçersiz kontrol durumu: {self.durum}")
        if self.sure_ms < 0:
            raise ValueError("Kontrol süresi negatif olamaz.")

    def sozluk(self) -> dict[str, object]:
        return {
            "ad": self.ad,
            "durum": self.durum,
            "aciklama": self.aciklama,
            "kritik": self.kritik,
            "sure_ms": round(self.sure_ms, 2),
        }


@dataclass(frozen=True)
class SystemCheckReport:
    """Hisse Robotu çalışma ortamı ve ana akış kontrol raporu."""

    surum: str
    baslangic_zamani: str
    bitis_zamani: str
    kontroller: tuple[SystemCheckItem, ...]

    @property
    def basarili_sayisi(self) -> int:
        return sum(item.durum == BASARILI for item in self.kontroller)

    @property
    def uyari_sayisi(self) -> int:
        return sum(item.durum == UYARI for item in self.kontroller)

    @property
    def basarisiz_sayisi(self) -> int:
        return sum(item.durum == BASARISIZ for item in self.kontroller)

    @property
    def kullanima_hazir(self) -> bool:
        return not any(
            item.kritik and item.durum == BASARISIZ
            for item in self.kontroller
        )

    def sozluk(self) -> dict[str, object]:
        return {
            "surum": self.surum,
            "baslangic_zamani": self.baslangic_zamani,
            "bitis_zamani": self.bitis_zamani,
            "kullanima_hazir": self.kullanima_hazir,
            "basarili": self.basarili_sayisi,
            "uyari": self.uyari_sayisi,
            "basarisiz": self.basarisiz_sayisi,
            "kontroller": [item.sozluk() for item in self.kontroller],
        }

    def json_metni(self) -> str:
        return json.dumps(self.sozluk(), ensure_ascii=False, indent=2)


ZORUNLU_MODULLER = (
    ("numpy", "Sayısal hesaplama"),
    ("pandas", "Tablo ve zaman serisi"),
    ("yfinance", "BIST piyasa verisi"),
    ("streamlit", "Kullanıcı arayüzü"),
    ("reportlab", "PDF raporu"),
)

ISTEGE_BAGLI_MODULLER = (("pytest", "Otomatik testler"),)

ZORUNLU_DOSYALAR = (
    "backend/dashboard.py",
    "backend/app/data/market_data.py",
    "backend/app/data/data_freshness.py",
    "backend/app/data/batch_market_data.py",
    "backend/app/data/multi_timeframe_data.py",
    "backend/app/analysis/bist_universe.py",
    "backend/app/analysis/market_scanner.py",
    "backend/app/analysis/momentum_discovery.py",
    "backend/app/analysis/momentum_walk_forward.py",
    "backend/app/history/momentum_history.py",
    "backend/app/analysis/technical_confirmation.py",
    "backend/app/analysis/trade_plan.py",
    "backend/app/analysis/position_monitor.py",
    "backend/app/analysis/loss_analysis.py",
    "backend/app/history/trade_journal.py",
    "backend/app/risk/safety_lock.py",
    "backend/app/ui/live_analysis_dashboard.py",
    "backend/requirements-dashboard.txt",
    "backend/resources/bist_endeks_bilesenleri.csv",
    "Hisse-Robotu-Baslat.ps1",
    "KULLANIM.md",
)


def sistem_kontrolu_calistir(
    proje_koku: str | Path | None = None,
    *,
    modul_bulucu: ModuleFinder = importlib.util.find_spec,
    gecmis_klasoru: str | Path | None = None,
    simdi: Callable[[], datetime] = datetime.now,
) -> SystemCheckReport:
    """
    Çalışma ortamını ve ana iş akışlarını ağ bağlantısı kullanmadan doğrular.

    Kontrol gerçek piyasa verisi indirmez. Bunun yerine tekrarlanabilir sentetik
    veriyle backtest, raporlama, geçmiş kaydı, teknik teyit, işlem planı ve açık
    pozisyon izleme zincirlerini baştan sona çalıştırır.
    """
    baslangic = simdi()
    kok = (
        Path(proje_koku).expanduser().resolve()
        if proje_koku is not None
        else Path(__file__).resolve().parents[3]
    )
    kontroller: list[SystemCheckItem] = []

    kontroller.append(_python_kontrolu())
    kontroller.extend(_modul_kontrolleri(modul_bulucu))
    kontroller.append(_proje_yapisi_kontrolu(kok))
    kontroller.append(_kaynak_derleme_kontrolu(kok))
    kontroller.append(_bist_evreni_kontrolu(kok))
    kontroller.append(_toplu_tarama_zinciri_kontrolu())
    kontroller.append(_momentum_kesif_zinciri_kontrolu())
    kontroller.append(_momentum_walk_forward_zinciri_kontrolu())
    kontroller.append(_veri_tazeligi_kilidi_kontrolu())
    kontroller.append(_kayip_analizi_guvenlik_zinciri_kontrolu())
    kontroller.append(
        _gecmis_yazma_kontrolu(
            Path(gecmis_klasoru).expanduser()
            if gecmis_klasoru is not None
            else varsayilan_gecmis_klasoru()
        )
    )

    backtest_sonucu: DashboardResult | None = None
    try:
        basla = perf_counter()
        backtest_sonucu = _sentetik_backtest_calistir()
        kontroller.append(
            SystemCheckItem(
                ad="Tek hisse backtest zinciri",
                durum=BASARILI,
                aciklama=(
                    f"{backtest_sonucu.ozet.fiyat_bar_sayisi} bar, "
                    f"{backtest_sonucu.ozet.tamamlanan_islem_sayisi} "
                    "tamamlanmış işlem ile çalıştı."
                ),
                sure_ms=_sure_ms(basla),
            )
        )
    except Exception as hata:  # Tanılama katmanı tüm beklenmeyen hataları raporlar.
        kontroller.append(
            _hata_itemi("Tek hisse backtest zinciri", hata)
        )

    if backtest_sonucu is None:
        kontroller.extend(
            (
                SystemCheckItem(
                    ad="CSV ve PDF rapor üretimi",
                    durum=BASARISIZ,
                    aciklama="Backtest sonucu üretilemediği için kontrol atlandı.",
                ),
                SystemCheckItem(
                    ad="Analiz geçmişi kayıt zinciri",
                    durum=BASARISIZ,
                    aciklama="Backtest sonucu üretilemediği için kontrol atlandı.",
                ),
            )
        )
    else:
        kontroller.append(_rapor_uretimi_kontrolu(backtest_sonucu))
        kontroller.append(_gecmis_kaydi_kontrolu(backtest_sonucu))

    kontroller.append(_canli_analiz_zinciri_kontrolu())

    kontroller.append(_kap_vbts_guvenlik_kontrolu())

    bitis = simdi()
    return SystemCheckReport(
        surum=SISTEM_KONTROL_SURUMU,
        baslangic_zamani=baslangic.isoformat(timespec="seconds"),
        bitis_zamani=bitis.isoformat(timespec="seconds"),
        kontroller=tuple(kontroller),
    )


def _kap_vbts_guvenlik_kontrolu() -> SystemCheckItem:
    basla = perf_counter()

    import os

    from backend.app.compliance.kap_settings import KapSettings

    degiskenler = (
        "HISSE_ROBOTU_KAP_BASE_URL",
        "HISSE_ROBOTU_KAP_API_KEY",
        "HISSE_ROBOTU_KAP_TIMEOUT_SECONDS",
        "HISSE_ROBOTU_KAP_ENDPOINT_PATH",
        "HISSE_ROBOTU_KAP_API_KEY_HEADER",
        "HISSE_ROBOTU_KAP_COLLECTION_KEY",
        "HISSE_ROBOTU_KAP_API_KEY_PREFIX",
    )
    onceki = {ad: os.environ.get(ad) for ad in degiskenler}

    try:
        for ad in degiskenler:
            os.environ.pop(ad, None)

        guvenli_durdu = False
        try:
            KapSettings.from_environment()
        except ValueError as exc:
            guvenli_durdu = "KAP temel adresi" in str(exc)

        os.environ["HISSE_ROBOTU_KAP_BASE_URL"] = "https://kap.test/api"
        os.environ["HISSE_ROBOTU_KAP_API_KEY"] = "test-anahtari"
        os.environ["HISSE_ROBOTU_KAP_ENDPOINT_PATH"] = "disclosures"
        os.environ["HISSE_ROBOTU_KAP_API_KEY_HEADER"] = "X-API-KEY"
        os.environ["HISSE_ROBOTU_KAP_COLLECTION_KEY"] = "disclosures"

        ayarlar = KapSettings.from_environment()
        yapilandirma_dogru = (
            ayarlar.endpoint_path == "disclosures"
            and ayarlar.api_key_header == "X-API-KEY"
            and ayarlar.collection_key == "disclosures"
            and ayarlar.api_key_prefix == ""
        )

        uygun = guvenli_durdu and yapilandirma_dogru
        durum = BASARILI if uygun else BASARISIZ
        aciklama = (
            "Eksik ayarlarda güvenli durdurma ve sözleşmeye bağlı "
            "endpoint, başlık ve yanıt anahtarı yapılandırması doğrulandı."
            if uygun
            else "KAP/VBTS güvenlik yapılandırması doğrulanamadı."
        )

        return SystemCheckItem(
            ad="KAP/VBTS güvenli yapılandırma",
            durum=durum,
            aciklama=aciklama,
            kritik=True,
            sure_ms=(perf_counter() - basla) * 1000,
        )
    except Exception as exc:
        return SystemCheckItem(
            ad="KAP/VBTS güvenli yapılandırma",
            durum=BASARISIZ,
            aciklama=f"KAP/VBTS kontrolü çalıştırılamadı: {exc}",
            kritik=True,
            sure_ms=(perf_counter() - basla) * 1000,
        )
    finally:
        for ad, deger in onceki.items():
            if deger is None:
                os.environ.pop(ad, None)
            else:
                os.environ[ad] = deger

def _veri_tazeligi_kilidi_kontrolu() -> SystemCheckItem:
    basla = perf_counter()
    simdi = datetime(2026, 7, 28, 19, 0)
    guncel = pd.DataFrame({"Close": [100.0]}, index=pd.to_datetime(["2026-07-28"]))
    eski = pd.DataFrame({"Close": [99.0]}, index=pd.to_datetime(["2026-07-27"]))
    guncel_sonuc = gunluk_veri_tazeligini_degerlendir(guncel, simdi=simdi)
    eski_sonuc = gunluk_veri_tazeligini_degerlendir(eski, simdi=simdi)
    uygun = (not guncel_sonuc.kilitli) and eski_sonuc.kilitli
    return SystemCheckItem(
        ad="Veri tazeliği güvenlik kilidi",
        durum=BASARILI if uygun else BASARISIZ,
        aciklama=(
            "Güncel tamamlanmış bar kabul edildi; bir işlem günü eski veri "
            "momentum, teknik analiz ve işlem planı için kilitlendi."
        ),
        sure_ms=_sure_ms(basla),
    )


def _python_kontrolu() -> SystemCheckItem:
    mevcut = sys.version_info[:3]
    uygun = mevcut[:2] >= MINIMUM_PYTHON
    return SystemCheckItem(
        ad="Python sürümü",
        durum=BASARILI if uygun else BASARISIZ,
        aciklama=(
            f"Python {mevcut[0]}.{mevcut[1]}.{mevcut[2]} "
            f"(minimum {MINIMUM_PYTHON[0]}.{MINIMUM_PYTHON[1]})."
        ),
    )


def _modul_kontrolleri(modul_bulucu: ModuleFinder) -> tuple[SystemCheckItem, ...]:
    sonuclar: list[SystemCheckItem] = []
    for modul, amac in ZORUNLU_MODULLER:
        sonuclar.append(
            _tek_modul_kontrolu(modul, amac, True, modul_bulucu)
        )
    for modul, amac in ISTEGE_BAGLI_MODULLER:
        sonuclar.append(
            _tek_modul_kontrolu(modul, amac, False, modul_bulucu)
        )
    return tuple(sonuclar)


def _tek_modul_kontrolu(
    modul: str,
    amac: str,
    kritik: bool,
    modul_bulucu: ModuleFinder,
) -> SystemCheckItem:
    basla = perf_counter()
    try:
        bulundu = modul_bulucu(modul) is not None
    except Exception as hata:
        return _hata_itemi(
            f"Paket: {modul}",
            hata,
            kritik=kritik,
            sure_ms=_sure_ms(basla),
        )

    if bulundu:
        return SystemCheckItem(
            ad=f"Paket: {modul}",
            durum=BASARILI,
            aciklama=f"{amac} paketi kullanılabilir.",
            kritik=kritik,
            sure_ms=_sure_ms(basla),
        )
    return SystemCheckItem(
        ad=f"Paket: {modul}",
        durum=BASARISIZ if kritik else UYARI,
        aciklama=(
            f"{amac} paketi kurulu değil. "
            "requirements.txt ile kurulabilir."
        ),
        kritik=kritik,
        sure_ms=_sure_ms(basla),
    )


def _proje_yapisi_kontrolu(kok: Path) -> SystemCheckItem:
    basla = perf_counter()
    eksikler = [yol for yol in ZORUNLU_DOSYALAR if not (kok / yol).is_file()]
    if eksikler:
        return SystemCheckItem(
            ad="Proje dosya yapısı",
            durum=BASARISIZ,
            aciklama="Eksik dosyalar: " + ", ".join(eksikler),
            sure_ms=_sure_ms(basla),
        )
    return SystemCheckItem(
        ad="Proje dosya yapısı",
        durum=BASARILI,
        aciklama=f"{len(ZORUNLU_DOSYALAR)} zorunlu dosya bulundu.",
        sure_ms=_sure_ms(basla),
    )


def _kaynak_derleme_kontrolu(kok: Path) -> SystemCheckItem:
    basla = perf_counter()
    backend = kok / "backend"
    if not backend.is_dir():
        return SystemCheckItem(
            ad="Python kaynak doğrulaması",
            durum=BASARISIZ,
            aciklama="backend klasörü bulunamadı.",
            sure_ms=_sure_ms(basla),
        )

    dosyalar = tuple(
        dosya
        for dosya in backend.rglob("*.py")
        if "__pycache__" not in dosya.parts
    )
    try:
        for dosya in dosyalar:
            kaynak = dosya.read_text(encoding="utf-8")
            compile(kaynak, str(dosya), "exec")
    except (OSError, UnicodeError, SyntaxError) as hata:
        return _hata_itemi(
            "Python kaynak doğrulaması",
            hata,
            sure_ms=_sure_ms(basla),
        )

    return SystemCheckItem(
        ad="Python kaynak doğrulaması",
        durum=BASARILI,
        aciklama=f"{len(dosyalar)} Python dosyası sözdizimi kontrolünden geçti.",
        sure_ms=_sure_ms(basla),
    )



def _kayip_analizi_guvenlik_zinciri_kontrolu() -> SystemCheckItem:
    basla = perf_counter()
    try:
        kayitlar = (
            TradeRecord(
                account_type=GERCEK_HESAP,
                symbol="AAA",
                entry_date=datetime(2026, 7, 1).date(),
                exit_date=datetime(2026, 7, 6).date(),
                entry_price=100.0,
                exit_price=110.0,
                quantity=100,
                capital_at_entry=100_000.0,
                stop_loss=95.0,
                target_price=110.0,
                signal_class="E3",
                created_at="2026-07-06T18:00:00",
            ),
            TradeRecord(
                account_type=GERCEK_HESAP,
                symbol="BBB",
                entry_date=datetime(2026, 7, 2).date(),
                exit_date=datetime(2026, 7, 7).date(),
                entry_price=100.0,
                exit_price=90.0,
                quantity=100,
                capital_at_entry=100_000.0,
                stop_loss=None,
                target_price=None,
                late_entry=True,
                created_at="2026-07-07T18:00:00",
            ),
            TradeRecord(
                account_type=GERCEK_HESAP,
                symbol="CCC",
                entry_date=datetime(2026, 7, 3).date(),
                exit_date=datetime(2026, 7, 8).date(),
                entry_price=100.0,
                exit_price=94.0,
                quantity=100,
                capital_at_entry=100_000.0,
                stop_loss=96.0,
                target_price=104.0,
                averaging_down=True,
                created_at="2026-07-08T18:00:00",
            ),
        )
        politika = SafetyPolicy()
        analiz = analyze_trade_losses(
            kayitlar,
            policy=politika,
            evaluation_date=datetime(2026, 7, 8).date(),
        )
        guvenli = evaluate_trade_safety(
            TradeProposal(
                symbol="AAA",
                capital=100_000.0,
                entry_price=100.0,
                quantity=200,
                stop_loss=95.0,
                target_price=110.0,
            ),
            context=SafetyLockContext(),
            policy=politika,
        )
        guvensiz = evaluate_trade_safety(
            TradeProposal(
                symbol="BBB",
                capital=100_000.0,
                entry_price=100.0,
                quantity=500,
                stop_loss=None,
                target_price=None,
                averaging_down=True,
            ),
            context=analiz.safety_context,
            policy=politika,
        )
        if analiz.summary.trade_count != 3 or analiz.summary.losing_count != 2:
            raise ValueError("Sentetik işlem günlüğü doğru özetlenemedi.")
        if not analiz.causes:
            raise ValueError("Kayıp nedenleri üretilemedi.")
        if not guvenli.allowed or guvensiz.allowed:
            raise ValueError("Güvenlik kilidi güvenli ve riskli planları ayıramadı.")
    except Exception as hata:
        return _hata_itemi(
            "İşlem kayıp analizi ve güvenlik kilidi",
            hata,
            sure_ms=_sure_ms(basla),
        )

    return SystemCheckItem(
        ad="İşlem kayıp analizi ve güvenlik kilidi",
        durum=BASARILI,
        aciklama=(
            "3 tamamlanmış işlem analiz edildi; stop, risk/getiri, pozisyon, "
            "günlük/haftalık zarar ve disiplin kilitleri doğrulandı."
        ),
        sure_ms=_sure_ms(basla),
    )

def _gecmis_yazma_kontrolu(klasor: Path) -> SystemCheckItem:
    basla = perf_counter()
    deneme = klasor / ".hisse_robotu_yazma_kontrolu"
    try:
        klasor.mkdir(parents=True, exist_ok=True)
        deneme.write_text("ok", encoding="utf-8")
        deneme.unlink()
    except OSError as hata:
        return _hata_itemi(
            "Analiz geçmişi yazma izni",
            hata,
            sure_ms=_sure_ms(basla),
        )
    return SystemCheckItem(
        ad="Analiz geçmişi yazma izni",
        durum=BASARILI,
        aciklama=f"Yazılabilir klasör: {klasor}",
        sure_ms=_sure_ms(basla),
    )


def _sentetik_backtest_calistir() -> DashboardResult:
    veri = _sentetik_gunluk_veri()

    def veri_getirici(**_: object) -> pd.DataFrame:
        return veri.copy(deep=True)

    servis = BacktestDashboardService(
        StockBacktestService(veri_getirici=veri_getirici)
    )
    return servis.calistir(
        DashboardBacktestRequest(
            sembol="THYAO",
            islem_gunu=300,
            indirme_donemi="5y",
        )
    )


def _rapor_uretimi_kontrolu(sonuc: DashboardResult) -> SystemCheckItem:
    basla = perf_counter()
    try:
        csv = tek_hisse_islem_csv_baytlari(sonuc)
        pdf = tek_hisse_pdf_baytlari(sonuc)
        if not csv.startswith(b"\xef\xbb\xbf"):
            raise ValueError("CSV UTF-8 BOM ile başlamıyor.")
        if not pdf.startswith(b"%PDF"):
            raise ValueError("PDF başlığı geçersiz.")
    except Exception as hata:
        return _hata_itemi(
            "CSV ve PDF rapor üretimi",
            hata,
            sure_ms=_sure_ms(basla),
        )
    return SystemCheckItem(
        ad="CSV ve PDF rapor üretimi",
        durum=BASARILI,
        aciklama=f"CSV {len(csv)} bayt, PDF {len(pdf)} bayt üretildi.",
        sure_ms=_sure_ms(basla),
    )


def _gecmis_kaydi_kontrolu(sonuc: DashboardResult) -> SystemCheckItem:
    basla = perf_counter()
    try:
        with TemporaryDirectory(prefix="hisse_robotu_kontrol_") as klasor:
            depo = BacktestHistoryStore(kok_klasor=klasor)
            kayit = depo.tek_hisse_kaydet(sonuc)
            listelenen = depo.kayitlari_listele()
            okunan = depo.kayit_getir(kayit.kayit_kimligi)
            if len(listelenen) != 1 or okunan.kayit_kimligi != kayit.kayit_kimligi:
                raise ValueError("Kaydedilen analiz geçmişten geri okunamadı.")
    except Exception as hata:
        return _hata_itemi(
            "Analiz geçmişi kayıt zinciri",
            hata,
            sure_ms=_sure_ms(basla),
        )
    return SystemCheckItem(
        ad="Analiz geçmişi kayıt zinciri",
        durum=BASARILI,
        aciklama="Analiz kaydedildi, listelendi ve tekrar okundu.",
        sure_ms=_sure_ms(basla),
    )


def _bist_evreni_kontrolu(kok: Path) -> SystemCheckItem:
    basla = perf_counter()
    try:
        snapshot = kok / "backend" / "resources" / "bist_endeks_bilesenleri.csv"
        depo = BistUniverseRepository(
            snapshot_yolu=snapshot,
            onbellek_yolu=kok / "backend" / "cache" / "sistem_kontrol.csv",
        )
        beklenenler = {
            "BIST 30": 30,
            "BIST 100": 100,
            "BIST 500": 500,
            "BIST Tüm": 500,
        }
        sayilar: list[str] = []
        for ad, minimum in beklenenler.items():
            evren = depo.evreni_yukle(ad, internetten_guncelle=False)
            if evren.sembol_sayisi < minimum:
                raise ValueError(
                    f"{ad} yalnızca {evren.sembol_sayisi} sembol içeriyor; "
                    f"minimum {minimum} bekleniyor."
                )
            sayilar.append(f"{ad}: {evren.sembol_sayisi}")
    except Exception as hata:
        return _hata_itemi(
            "BIST tarama evrenleri",
            hata,
            sure_ms=_sure_ms(basla),
        )

    return SystemCheckItem(
        ad="BIST tarama evrenleri",
        durum=BASARILI,
        aciklama=", ".join(sayilar),
        sure_ms=_sure_ms(basla),
    )


def _toplu_tarama_zinciri_kontrolu() -> SystemCheckItem:
    basla = perf_counter()
    try:
        veri = _sentetik_gunluk_veri(200)
        semboller = ("AAA.IS", "BBB.IS", "CCC.IS")

        def veri_getirici(
            istenen_semboller: object,
            **_kwargs: object,
        ) -> BatchMarketDataResult:
            return BatchMarketDataResult(
                veriler={
                    sembol: veri.copy()
                    for sembol in tuple(istenen_semboller)  # type: ignore[arg-type]
                },
                hatalar=(),
            )

        tarama = BatchStockScanner(veri_getirici=veri_getirici).tara(semboller)
        if tarama.basarili_sayisi != len(semboller):
            raise ValueError(
                f"{len(semboller)} sembolden yalnızca "
                f"{tarama.basarili_sayisi} tanesi analiz edildi."
            )
        if tarama.hatali_sayisi:
            raise ValueError("Sentetik toplu taramada veri hatası oluştu.")
    except Exception as hata:
        return _hata_itemi(
            "BIST toplu tarama zinciri",
            hata,
            sure_ms=_sure_ms(basla),
        )

    return SystemCheckItem(
        ad="BIST toplu tarama zinciri",
        durum=BASARILI,
        aciklama=(
            f"{tarama.toplam_sembol} sembol tek toplu veri paketiyle "
            "analiz edilip sıralandı."
        ),
        sure_ms=_sure_ms(basla),
    )


def _momentum_kesif_zinciri_kontrolu() -> SystemCheckItem:
    basla = perf_counter()
    try:
        temel = _sentetik_gunluk_veri(200)
        guclu = temel.copy()
        guclu.loc[guclu.index[-1], "Close"] = float(
            guclu["High"].iloc[-20:-1].max() * 1.04
        )
        guclu.loc[guclu.index[-5:], "Volume"] *= 2.0
        asiri = temel.copy()
        asiri.loc[asiri.index[-5:], "Close"] *= np.linspace(1.0, 1.35, 5)
        asiri.loc[asiri.index[-5:], "High"] = asiri["Close"].iloc[-5:] + 1.4
        asiri.loc[asiri.index[-5:], "Low"] = asiri["Close"].iloc[-5:] - 1.4

        motor = MomentumDiscoveryEngine()
        adaylar, hatalar = motor.analiz_et(
            {"AAA.IS": guclu, "BBB.IS": temel, "CCC.IS": asiri}
        )
        if len(adaylar) != 3 or hatalar:
            raise ValueError("Sentetik momentum keşfi bütün sembolleri üretemedi.")
        if not any(aday.kirilim for aday in adaylar):
            raise ValueError("Momentum keşfi kırılım adayını belirleyemedi.")
        if not any(aday.asiri_uzamis for aday in adaylar):
            raise ValueError("Momentum keşfi aşırı yükselmiş adayı ayıramadı.")
    except Exception as hata:
        return _hata_itemi(
            "Momentum keşif zinciri",
            hata,
            sure_ms=_sure_ms(basla),
        )

    return SystemCheckItem(
        ad="Momentum keşif zinciri",
        durum=BASARILI,
        aciklama=(
            f"{len(adaylar)} sembol göreceli güç, hacim, kırılım ve "
            "aşırı uzama ölçütleriyle sınıflandırıldı."
        ),
        sure_ms=_sure_ms(basla),
    )


def _momentum_walk_forward_zinciri_kontrolu() -> SystemCheckItem:
    basla = perf_counter()
    try:
        veri = _sentetik_gunluk_veri(150)
        kesim_indeksi = 119
        kesim_tarihi = str(pd.Timestamp(veri.index[kesim_indeksi]).date())
        # Kesim sonrasında aday üretiminden gizlenecek güçlü hareket.
        baslangic = float(veri["Close"].iloc[kesim_indeksi])
        veri.loc[veri.index[kesim_indeksi + 1 :], "Close"] = np.linspace(
            baslangic * 1.01,
            baslangic * 1.18,
            len(veri) - kesim_indeksi - 1,
        )
        veri.loc[veri.index[kesim_indeksi + 1 :], "High"] = (
            veri["Close"].iloc[kesim_indeksi + 1 :] + 1.0
        )
        veri.loc[veri.index[kesim_indeksi + 1 :], "Low"] = (
            veri["Close"].iloc[kesim_indeksi + 1 :] - 1.0
        )

        motor = MomentumWalkForwardEngine()
        sonuclar, hatalar = motor.calistir(
            {"AAA.IS": veri},
            kesim_tarihi=kesim_tarihi,
            ufuklar=(5, 10, 20),
            sinyal_gecmisi_olustur=True,
            sinyal_gecmisi_adim_sayisi=4,
        )
        if hatalar:
            raise ValueError(hatalar[0].hata)
        if not sonuclar:
            raise ValueError("Yeniden oynatma sentetik sonucu üretemedi.")
        sonuc = sonuclar[0]
        if sonuc.aday.analiz_tarihi != kesim_tarihi:
            raise ValueError("Yeniden oynatma kesim tarihini korumadı.")
        if sonuc.maksimum_fiyat is None or sonuc.maksimum_olumlu_hareket is None:
            raise ValueError("Dönem içi gerçek en yüksek fiyat hesaplanamadı.")
        if sonuc.maksimum_fiyat <= baslangic:
            raise ValueError("Gerçek azami yükseliş beklenen yönde oluşmadı.")
        if len(sonuc.sinyal_gecmisi) != 4:
            raise ValueError("Sinyal sınıfı geçmişi üretilemedi.")
        if sonuc.aday.kirilim_tetik_seviyesi <= sonuc.aday.yakin_direnc:
            raise ValueError("Kırılım tetik seviyesi yakın direncin üzerinde değil.")
    except Exception as hata:
        return _hata_itemi(
            "Momentum tarihsel yeniden oynatma",
            hata,
            sure_ms=_sure_ms(basla),
        )

    return SystemCheckItem(
        ad="Momentum tarihsel yeniden oynatma",
        durum=BASARILI,
        aciklama=(
            "Kesim sonrası barlar gizlendi; 5/10/20 kapanış getirileri, "
            "gerçek dönem içi tepe/dip ve sınıf geçmişi üretildi."
        ),
        sure_ms=_sure_ms(basla),
    )


def _canli_analiz_zinciri_kontrolu() -> SystemCheckItem:
    basla = perf_counter()
    try:
        paket = _sentetik_coklu_zaman_paketi()
        teknik = teknik_teyit_analizi_yap(paket)
        plan = islem_plani_olustur(
            paket=paket,
            teknik_teyit=teknik,
            sermaye=100_000.0,
            azami_risk_orani=0.01,
        )

        gunluk = paket.getir(GUNLUK).veri
        giris_satiri = gunluk.iloc[-40]
        giris = float(giris_satiri["Close"])
        pozisyon = OpenPosition(
            giris_tarihi=str(pd.Timestamp(giris_satiri.name).date()),
            giris_fiyati=giris,
            lot_sayisi=10,
            ilk_stop=giris - 12.0,
            hedef_1=giris + 12.0,
            hedef_2=giris + 24.0,
        )
        izleme = acik_pozisyonu_izle(
            paket=paket,
            teknik_teyit=teknik,
            pozisyon=pozisyon,
        )

        if teknik.veri_kimligi != paket.veri_kimligi:
            raise ValueError("Teknik analiz veri kimliğiyle eşleşmiyor.")
        if plan.teknik_analiz_kimligi != teknik.analiz_kimligi:
            raise ValueError("İşlem planı teknik analiz kimliğiyle eşleşmiyor.")
        if izleme.teknik_analiz_kimligi != teknik.analiz_kimligi:
            raise ValueError("Pozisyon izleme teknik analiz kimliğiyle eşleşmiyor.")
    except Exception as hata:
        return _hata_itemi(
            "Güncel analiz ve pozisyon zinciri",
            hata,
            sure_ms=_sure_ms(basla),
        )

    return SystemCheckItem(
        ad="Güncel analiz ve pozisyon zinciri",
        durum=BASARILI,
        aciklama=(
            f"Teknik skor {teknik.teyit_skoru}/100, "
            f"plan ‘{plan.karar}’, pozisyon ‘{izleme.durum}’ olarak üretildi."
        ),
        sure_ms=_sure_ms(basla),
    )


def _sentetik_gunluk_veri(bar: int = 360) -> pd.DataFrame:
    indeks = pd.bdate_range("2023-01-02", periods=bar)
    x = np.arange(bar, dtype=float)
    kapanis = (
        100.0
        + x * 0.03
        + np.sin(x / 8.0) * 5.0
        + np.sin(x / 31.0) * 8.0
    )
    return pd.DataFrame(
        {
            "Open": kapanis - 0.20,
            "High": kapanis + 1.40,
            "Low": kapanis - 1.40,
            "Close": kapanis,
            "Volume": 1_000_000.0 + (np.sin(x / 5.0) + 1.5) * 300_000.0,
        },
        index=indeks,
    )


def _sentetik_coklu_zaman_paketi() -> MultiTimeframeDataBundle:
    ayarlar = (
        (SAATLIK, "1h", "h", 300, "2026-01-02"),
        (GUNLUK, "1d", "B", 500, "2024-01-02"),
        (HAFTALIK, "1wk", "7D", 260, "2021-01-04"),
    )
    snapshots: list[TimeframeSnapshot] = []
    for sira, (ad, interval, frekans, bar, baslangic) in enumerate(ayarlar):
        indeks = pd.date_range(baslangic, periods=bar, freq=frekans)
        x = np.arange(bar, dtype=float)
        kapanis = (
            100.0
            + x * (0.035 + sira * 0.005)
            + np.sin(x / 7.0) * 3.5
            + np.sin(x / 23.0) * 2.0
        )
        veri = pd.DataFrame(
            {
                "Open": kapanis - 0.25,
                "High": kapanis + 1.20,
                "Low": kapanis - 1.20,
                "Close": kapanis,
                "Volume": 1_000_000.0 + x * 1_500.0,
            },
            index=indeks,
        )
        snapshots.append(
            TimeframeSnapshot(
                ad=ad,
                interval=interval,
                period="sistem-kontrolu",
                veri=veri,
                tamamlanmamis_bar_cikarildi=False,
                veri_kimligi=f"kontrol-{interval}",
            )
        )

    return MultiTimeframeDataBundle(
        sembol="THYAO.IS",
        zaman_dilimleri=tuple(snapshots),
        veri_kimligi="sistem-kontrol-paketi",
    )


def _hata_itemi(
    ad: str,
    hata: Exception,
    *,
    kritik: bool = True,
    sure_ms: float = 0.0,
) -> SystemCheckItem:
    return SystemCheckItem(
        ad=ad,
        durum=BASARISIZ if kritik else UYARI,
        aciklama=f"{type(hata).__name__}: {hata}",
        kritik=kritik,
        sure_ms=sure_ms,
    )


def _sure_ms(baslangic: float) -> float:
    return (perf_counter() - baslangic) * 1000.0

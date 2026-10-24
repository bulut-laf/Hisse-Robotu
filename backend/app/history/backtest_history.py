from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import re
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Iterable

from ..ui.backtest_dashboard import DashboardResult
from ..ui.live_analysis_dashboard import LiveAnalysisResult
from ..ui.portfolio_dashboard import PortfolioDashboardResult
from ..ui.report_export import (
    ReportExportError,
    portfoy_dosya_adlari,
    portfoy_katki_csv_baytlari,
    portfoy_ozsermaye_csv_baytlari,
    portfoy_pdf_baytlari,
    tek_hisse_dosya_adlari,
    tek_hisse_islem_csv_baytlari,
    tek_hisse_pdf_baytlari,
)


TEK_HISSE_ANALIZI = "tek_hisse"
PORTFOY_ANALIZI = "portfoy"
GUNCEL_TEKNIK_ANALIZ = "guncel_teknik_analiz"
BACKTEST_ANALIZ_TURLERI = (TEK_HISSE_ANALIZI, PORTFOY_ANALIZI)
DESTEKLENEN_ANALIZ_TURLERI = (
    TEK_HISSE_ANALIZI,
    PORTFOY_ANALIZI,
    GUNCEL_TEKNIK_ANALIZ,
)
GECMIS_KLASORU_DEGISKENI = "HISSE_ROBOTU_ANALIZ_GECMISI"
METADATA_DOSYASI = "metadata.json"
KAYIT_SURUMU = 1


class BacktestHistoryError(RuntimeError):
    """Analiz geçmişi okunamadığında veya yazılamadığında oluşur."""


@dataclass(frozen=True)
class HistoryArtifact:
    """Geçmiş kaydıyla birlikte saklanan indirilebilir dosya."""

    tur: str
    dosya_adi: str
    mime: str
    goreli_yol: str

    def sozluk(self) -> dict[str, str]:
        return {
            "tur": self.tur,
            "dosya_adi": self.dosya_adi,
            "mime": self.mime,
            "goreli_yol": self.goreli_yol,
        }

    @classmethod
    def sozlukten(cls, veri: object) -> "HistoryArtifact":
        if not isinstance(veri, dict):
            raise ValueError("Geçmiş dosya bilgisi sözlük olmalıdır.")

        return cls(
            tur=str(veri["tur"]),
            dosya_adi=str(veri["dosya_adi"]),
            mime=str(veri["mime"]),
            goreli_yol=str(veri["goreli_yol"]),
        )


@dataclass(frozen=True)
class BacktestHistoryRecord:
    """Tek-hisse veya portföy analizinin kalıcı özet kaydı."""

    kayit_kimligi: str
    analiz_turu: str
    kaydedilme_zamani: str
    baslik: str
    semboller: tuple[str, ...]
    donem: str
    tamamlanan_islem_sayisi: int
    atlanan_islem_sayisi: int
    bitis_sermayesi: float
    toplam_getiri_yuzde: float
    maksimum_dusus_yuzde: float
    guncel_dusus_yuzde: float
    kar_faktoru: float | None
    kazanma_yuzde: float | None
    ortalama_sermaye_kullanim_yuzde: float | None
    maksimum_pozisyon: int | None
    analiz_kimligi: str | None
    veri_kimligi: str
    ayar_kimligi: str
    dosyalar: tuple[HistoryArtifact, ...]
    ozel_bilgiler: dict[str, object] = field(default_factory=dict)
    surum: int = KAYIT_SURUMU

    def sozluk(self) -> dict[str, object]:
        return {
            "surum": self.surum,
            "kayit_kimligi": self.kayit_kimligi,
            "analiz_turu": self.analiz_turu,
            "kaydedilme_zamani": self.kaydedilme_zamani,
            "baslik": self.baslik,
            "semboller": list(self.semboller),
            "donem": self.donem,
            "tamamlanan_islem_sayisi": self.tamamlanan_islem_sayisi,
            "atlanan_islem_sayisi": self.atlanan_islem_sayisi,
            "bitis_sermayesi": self.bitis_sermayesi,
            "toplam_getiri_yuzde": self.toplam_getiri_yuzde,
            "maksimum_dusus_yuzde": self.maksimum_dusus_yuzde,
            "guncel_dusus_yuzde": self.guncel_dusus_yuzde,
            "kar_faktoru": self.kar_faktoru,
            "kazanma_yuzde": self.kazanma_yuzde,
            "ortalama_sermaye_kullanim_yuzde": (
                self.ortalama_sermaye_kullanim_yuzde
            ),
            "maksimum_pozisyon": self.maksimum_pozisyon,
            "analiz_kimligi": self.analiz_kimligi,
            "veri_kimligi": self.veri_kimligi,
            "ayar_kimligi": self.ayar_kimligi,
            "dosyalar": [dosya.sozluk() for dosya in self.dosyalar],
            "ozel_bilgiler": dict(self.ozel_bilgiler),
        }

    @classmethod
    def sozlukten(cls, veri: object) -> "BacktestHistoryRecord":
        if not isinstance(veri, dict):
            raise ValueError("Geçmiş kayıt bilgisi sözlük olmalıdır.")

        analiz_turu = str(veri["analiz_turu"])
        if analiz_turu not in DESTEKLENEN_ANALIZ_TURLERI:
            raise ValueError("Desteklenmeyen analiz geçmişi türü.")

        surum = int(veri.get("surum", 0))
        if surum != KAYIT_SURUMU:
            raise ValueError("Desteklenmeyen analiz geçmişi sürümü.")

        ham_semboller = veri["semboller"]
        if not isinstance(ham_semboller, list):
            raise ValueError("Geçmiş sembol listesi geçersiz.")

        ham_dosyalar = veri.get("dosyalar", [])
        if not isinstance(ham_dosyalar, list):
            raise ValueError("Geçmiş dosya listesi geçersiz.")

        ham_ozel_bilgiler = veri.get("ozel_bilgiler", {})
        if ham_ozel_bilgiler is None:
            ham_ozel_bilgiler = {}
        if not isinstance(ham_ozel_bilgiler, dict):
            raise ValueError("Geçmiş özel bilgi alanı sözlük olmalıdır.")

        return cls(
            kayit_kimligi=str(veri["kayit_kimligi"]),
            analiz_turu=analiz_turu,
            kaydedilme_zamani=str(veri["kaydedilme_zamani"]),
            baslik=str(veri["baslik"]),
            semboller=tuple(str(sembol) for sembol in ham_semboller),
            donem=str(veri["donem"]),
            tamamlanan_islem_sayisi=int(veri["tamamlanan_islem_sayisi"]),
            atlanan_islem_sayisi=int(veri["atlanan_islem_sayisi"]),
            bitis_sermayesi=float(veri["bitis_sermayesi"]),
            toplam_getiri_yuzde=float(veri["toplam_getiri_yuzde"]),
            maksimum_dusus_yuzde=float(veri["maksimum_dusus_yuzde"]),
            guncel_dusus_yuzde=float(veri["guncel_dusus_yuzde"]),
            kar_faktoru=_istege_bagli_float(veri.get("kar_faktoru")),
            kazanma_yuzde=_istege_bagli_float(veri.get("kazanma_yuzde")),
            ortalama_sermaye_kullanim_yuzde=_istege_bagli_float(
                veri.get("ortalama_sermaye_kullanim_yuzde")
            ),
            maksimum_pozisyon=_istege_bagli_int(
                veri.get("maksimum_pozisyon")
            ),
            analiz_kimligi=(
                None
                if veri.get("analiz_kimligi") is None
                else str(veri["analiz_kimligi"])
            ),
            veri_kimligi=str(veri["veri_kimligi"]),
            ayar_kimligi=str(veri["ayar_kimligi"]),
            dosyalar=tuple(
                HistoryArtifact.sozlukten(dosya)
                for dosya in ham_dosyalar
            ),
            ozel_bilgiler=dict(ham_ozel_bilgiler),
            surum=surum,
        )

    def dosya(self, tur: str) -> HistoryArtifact | None:
        return next(
            (dosya for dosya in self.dosyalar if dosya.tur == tur),
            None,
        )


Clock = Callable[[], datetime]


def varsayilan_gecmis_klasoru() -> Path:
    """Kullanıcı projesinden bağımsız kalıcı geçmiş klasörünü döndürür."""

    ortam_degeri = os.getenv(GECMIS_KLASORU_DEGISKENI)
    if ortam_degeri and ortam_degeri.strip():
        return Path(ortam_degeri).expanduser()

    return Path.home() / ".hisse_robotu" / "analiz_gecmisi"


class BacktestHistoryStore:
    """Backtest özetlerini ve indirilebilir raporlarını dosyada saklar."""

    def __init__(
        self,
        kok_klasor: str | Path | None = None,
        saat: Clock | None = None,
    ) -> None:
        self.kok_klasor = (
            Path(kok_klasor).expanduser()
            if kok_klasor is not None
            else varsayilan_gecmis_klasoru()
        )
        self._saat = saat if saat is not None else _yerel_zaman

    def tek_hisse_kaydet(
        self,
        sonuc: DashboardResult,
    ) -> BacktestHistoryRecord:
        if not isinstance(sonuc, DashboardResult):
            raise TypeError("Tek-hisse geçmiş sonucu DashboardResult olmalıdır.")

        ozet = sonuc.ozet
        kayit_kimligi = _kayit_kimligi(
            "tek_hisse",
            ozet.analiz_kimligi,
            ozet.veri_kimligi,
            ozet.ayar_kimligi,
        )
        adlar = tek_hisse_dosya_adlari(sonuc)
        dosya_verileri: list[tuple[HistoryArtifact, bytes]] = [
            (
                HistoryArtifact(
                    tur="islemler_csv",
                    dosya_adi=adlar.csv,
                    mime="text/csv; charset=utf-8",
                    goreli_yol=adlar.csv,
                ),
                tek_hisse_islem_csv_baytlari(sonuc),
            )
        ]
        _pdf_eklemeyi_dene(
            dosya_verileri,
            tur="pdf",
            dosya_adi=adlar.pdf,
            uretici=lambda: tek_hisse_pdf_baytlari(sonuc),
        )

        kayit = BacktestHistoryRecord(
            kayit_kimligi=kayit_kimligi,
            analiz_turu=TEK_HISSE_ANALIZI,
            kaydedilme_zamani=_zaman_metin(self._saat()),
            baslik=f"{ozet.sembol} · Tek Hisse Backtest",
            semboller=(ozet.sembol,),
            donem=ozet.fiyat_donemi,
            tamamlanan_islem_sayisi=ozet.tamamlanan_islem_sayisi,
            atlanan_islem_sayisi=ozet.atlanan_sinyal_sayisi,
            bitis_sermayesi=ozet.bitis_sermayesi,
            toplam_getiri_yuzde=ozet.toplam_getiri_yuzde,
            maksimum_dusus_yuzde=ozet.maksimum_dusus_yuzde,
            guncel_dusus_yuzde=ozet.guncel_dusus_yuzde,
            kar_faktoru=ozet.kar_faktoru,
            kazanma_yuzde=ozet.kazanma_yuzde,
            ortalama_sermaye_kullanim_yuzde=None,
            maksimum_pozisyon=None,
            analiz_kimligi=ozet.analiz_kimligi,
            veri_kimligi=ozet.veri_kimligi,
            ayar_kimligi=ozet.ayar_kimligi,
            dosyalar=tuple(dosya for dosya, _ in dosya_verileri),
        )
        self._kaydi_yaz(kayit, dosya_verileri)
        return kayit

    def portfoy_kaydet(
        self,
        sonuc: PortfolioDashboardResult,
    ) -> BacktestHistoryRecord:
        if not isinstance(sonuc, PortfolioDashboardResult):
            raise TypeError(
                "Portföy geçmiş sonucu PortfolioDashboardResult olmalıdır."
            )

        ozet = sonuc.ozet
        kayit_kimligi = _kayit_kimligi(
            "portfoy",
            ozet.portfoy_veri_kimligi,
            ozet.ayar_kimligi,
            "-".join(ozet.semboller),
        )
        adlar = portfoy_dosya_adlari(sonuc)
        dosya_verileri: list[tuple[HistoryArtifact, bytes]] = [
            (
                HistoryArtifact(
                    tur="katki_csv",
                    dosya_adi=adlar.contribution_csv,
                    mime="text/csv; charset=utf-8",
                    goreli_yol=adlar.contribution_csv,
                ),
                portfoy_katki_csv_baytlari(sonuc),
            ),
            (
                HistoryArtifact(
                    tur="ozsermaye_csv",
                    dosya_adi=adlar.equity_csv,
                    mime="text/csv; charset=utf-8",
                    goreli_yol=adlar.equity_csv,
                ),
                portfoy_ozsermaye_csv_baytlari(sonuc),
            ),
        ]
        _pdf_eklemeyi_dene(
            dosya_verileri,
            tur="pdf",
            dosya_adi=adlar.pdf,
            uretici=lambda: portfoy_pdf_baytlari(sonuc),
        )

        kayit = BacktestHistoryRecord(
            kayit_kimligi=kayit_kimligi,
            analiz_turu=PORTFOY_ANALIZI,
            kaydedilme_zamani=_zaman_metin(self._saat()),
            baslik=f"{len(ozet.semboller)} Hisselik Portföy Backtest",
            semboller=ozet.semboller,
            donem=ozet.portfoy_donemi,
            tamamlanan_islem_sayisi=ozet.tamamlanan_islem_sayisi,
            atlanan_islem_sayisi=ozet.atlanan_islem_sayisi,
            bitis_sermayesi=ozet.bitis_sermayesi,
            toplam_getiri_yuzde=ozet.toplam_getiri_yuzde,
            maksimum_dusus_yuzde=ozet.maksimum_dusus_yuzde,
            guncel_dusus_yuzde=ozet.guncel_dusus_yuzde,
            kar_faktoru=ozet.kar_faktoru,
            kazanma_yuzde=None,
            ortalama_sermaye_kullanim_yuzde=(
                ozet.ortalama_sermaye_kullanim_yuzde
            ),
            maksimum_pozisyon=ozet.gerceklesen_maksimum_pozisyon,
            analiz_kimligi=None,
            veri_kimligi=ozet.portfoy_veri_kimligi,
            ayar_kimligi=ozet.ayar_kimligi,
            dosyalar=tuple(dosya for dosya, _ in dosya_verileri),
        )
        self._kaydi_yaz(kayit, dosya_verileri)
        return kayit

    def guncel_analiz_kaydet(
        self,
        sonuc: LiveAnalysisResult,
    ) -> BacktestHistoryRecord:
        """Güncel teknik analiz sonucunu yeniden açılabilir biçimde saklar."""

        if not isinstance(sonuc, LiveAnalysisResult):
            raise TypeError(
                "Güncel analiz geçmiş sonucu LiveAnalysisResult olmalıdır."
            )

        teknik = sonuc.teknik_teyit
        plan = sonuc.islem_plani
        tazelik = sonuc.veri_tazeligi
        istek = sonuc.istek
        kaydedilme_zamani = _zaman_metin(self._saat())
        fiyat_veri_tarihi = (
            None
            if tazelik is None or tazelik.son_veri_tarihi is None
            else str(tazelik.son_veri_tarihi)
        )
        donem = (
            f"Fiyat veri tarihi: {fiyat_veri_tarihi}"
            if fiyat_veri_tarihi is not None
            else "Güncel teknik analiz"
        )

        pozisyon = plan.pozisyon
        ozel_bilgiler: dict[str, object] = {
            "kaydedilme_zamani": kaydedilme_zamani,
            "sembol": teknik.sembol,
            "fiyat_verisi": {
                "durum": None if tazelik is None else tazelik.durum,
                "son_veri_tarihi": fiyat_veri_tarihi,
                "beklenen_tarih": (
                    None if tazelik is None else str(tazelik.beklenen_tarih)
                ),
                "is_gunu_gecikmesi": (
                    None if tazelik is None else tazelik.is_gunu_gecikmesi
                ),
                "kilitli": None if tazelik is None else tazelik.kilitli,
                "aciklama": None if tazelik is None else tazelik.aciklama,
            },
            "teknik_teyit": {
                "skor": teknik.teyit_skoru,
                "durum": teknik.teyit_durumu,
                "haftalik_yon": teknik.haftalik.yon,
                "haftalik_skor": teknik.haftalik.skor,
                "gunluk_yon": teknik.gunluk.yon,
                "gunluk_skor": teknik.gunluk.skor,
                "saatlik_yon": teknik.saatlik.yon,
                "saatlik_skor": teknik.saatlik.skor,
                "pozitif_nedenler": list(teknik.pozitif_nedenler),
                "riskler": list(teknik.riskler),
            },
            "islem_plani": {
                "karar": plan.karar,
                "plan_tipi": plan.plan_tipi,
                "son_kapanis": plan.son_kapanis,
                "atr14": plan.atr14,
                "atr_yuzde": plan.atr_yuzde,
                "izleme_tetik_fiyati": plan.izleme_tetik_fiyati,
                "giris_alt": plan.giris_alt,
                "giris_ust": plan.giris_ust,
                "referans_giris": plan.referans_giris,
                "stop_loss": plan.stop_loss,
                "hedef_1": plan.hedef_1,
                "hedef_2": plan.hedef_2,
                "risk_odul_1": plan.risk_odul_1,
                "risk_odul_2": plan.risk_odul_2,
                "beklenen_teyitler": list(plan.beklenen_teyitler),
                "gecersizlik_kosullari": list(plan.gecersizlik_kosullari),
                "notlar": list(plan.notlar),
            },
            "risk_ve_pozisyon": {
                "sermaye": (
                    None if istek is None else float(istek.sermaye)
                ),
                "azami_risk_orani": (
                    None if istek is None else float(istek.azami_risk_orani)
                ),
                "risk_butcesi": (
                    None if pozisyon is None else pozisyon.risk_butcesi
                ),
                "lot_sayisi": (
                    None if pozisyon is None else pozisyon.lot_sayisi
                ),
                "pozisyon_tutari": (
                    None if pozisyon is None else pozisyon.pozisyon_tutari
                ),
                "planlanan_risk": (
                    None if pozisyon is None else pozisyon.planlanan_risk
                ),
            },
            "kimlikler": {
                "veri_kimligi": teknik.veri_kimligi,
                "teknik_analiz_kimligi": teknik.analiz_kimligi,
                "islem_plani_kimligi": plan.plan_kimligi,
            },
        }

        kayit_kimligi = _kayit_kimligi(
            GUNCEL_TEKNIK_ANALIZ,
            teknik.sembol,
            teknik.veri_kimligi,
            teknik.analiz_kimligi,
            plan.plan_kimligi,
        )
        csv_adi = (
            f"{_guvenli_kimlik(teknik.sembol)}_guncel_teknik_analiz.csv"
        )
        csv_artifact = HistoryArtifact(
            tur="guncel_analiz_csv",
            dosya_adi=csv_adi,
            mime="text/csv; charset=utf-8",
            goreli_yol=csv_adi,
        )
        kayit = BacktestHistoryRecord(
            kayit_kimligi=kayit_kimligi,
            analiz_turu=GUNCEL_TEKNIK_ANALIZ,
            kaydedilme_zamani=kaydedilme_zamani,
            baslik=f"{teknik.sembol} · Güncel Teknik Analiz",
            semboller=(teknik.sembol,),
            donem=donem,
            tamamlanan_islem_sayisi=0,
            atlanan_islem_sayisi=0,
            bitis_sermayesi=0.0,
            toplam_getiri_yuzde=0.0,
            maksimum_dusus_yuzde=0.0,
            guncel_dusus_yuzde=0.0,
            kar_faktoru=None,
            kazanma_yuzde=None,
            ortalama_sermaye_kullanim_yuzde=None,
            maksimum_pozisyon=(
                None if pozisyon is None else pozisyon.lot_sayisi
            ),
            analiz_kimligi=teknik.analiz_kimligi,
            veri_kimligi=teknik.veri_kimligi,
            ayar_kimligi=plan.plan_kimligi,
            dosyalar=(csv_artifact,),
            ozel_bilgiler=ozel_bilgiler,
        )
        self._kaydi_yaz(
            kayit,
            ((csv_artifact, _guncel_analiz_csv_baytlari(ozel_bilgiler)),),
        )
        return kayit

    def kayitlari_listele(
        self,
        *,
        analiz_turu: str | None = None,
        limit: int = 100,
    ) -> tuple[BacktestHistoryRecord, ...]:
        if limit <= 0:
            raise ValueError("Geçmiş kayıt limiti pozitif olmalıdır.")
        if (
            analiz_turu is not None
            and analiz_turu not in DESTEKLENEN_ANALIZ_TURLERI
        ):
            raise ValueError("Desteklenmeyen analiz geçmişi türü.")
        if not self.kok_klasor.exists():
            return ()

        kayitlar: list[BacktestHistoryRecord] = []
        for metadata_yolu in self.kok_klasor.glob(f"*/{METADATA_DOSYASI}"):
            try:
                kayit = self._metadata_oku(metadata_yolu)
            except (
                OSError,
                ValueError,
                KeyError,
                json.JSONDecodeError,
                BacktestHistoryError,
            ):
                continue
            if analiz_turu is None or kayit.analiz_turu == analiz_turu:
                kayitlar.append(kayit)

        kayitlar.sort(
            key=lambda kayit: kayit.kaydedilme_zamani,
            reverse=True,
        )
        return tuple(kayitlar[:limit])

    def kayit_getir(self, kayit_kimligi: str) -> BacktestHistoryRecord:
        metadata_yolu = self._kayit_klasoru(kayit_kimligi) / METADATA_DOSYASI
        if not metadata_yolu.is_file():
            raise BacktestHistoryError("Analiz geçmişi kaydı bulunamadı.")
        try:
            return self._metadata_oku(metadata_yolu)
        except (OSError, ValueError, KeyError, json.JSONDecodeError) as hata:
            raise BacktestHistoryError(
                "Analiz geçmişi kaydı okunamadı."
            ) from hata

    def kayit_sil(self, kayit_kimligi: str) -> BacktestHistoryRecord:
        """Bir geçmiş kaydını ve yalnızca kendi rapor klasörünü siler."""

        kayit = self.kayit_getir(kayit_kimligi)
        self._kayit_klasorunu_sil(kayit.kayit_kimligi)
        return kayit

    def kayitlari_sil(
        self,
        kayit_kimlikleri: Iterable[str],
    ) -> tuple[BacktestHistoryRecord, ...]:
        """Seçili geçmiş kayıtlarını ön doğrulamadan sonra topluca siler."""

        if isinstance(kayit_kimlikleri, (str, bytes)):
            raise TypeError("Silinecek kayıt kimlikleri koleksiyon olmalıdır.")

        benzersiz_kimlikler = tuple(dict.fromkeys(kayit_kimlikleri))
        if not benzersiz_kimlikler:
            return ()

        kayitlar = tuple(
            self.kayit_getir(kayit_kimligi)
            for kayit_kimligi in benzersiz_kimlikler
        )
        for kayit in kayitlar:
            self._kayit_klasorunu_sil(kayit.kayit_kimligi)
        return kayitlar

    def dosya_baytlari(
        self,
        kayit: BacktestHistoryRecord | str,
        dosya_turu: str,
    ) -> bytes:
        kayit_nesnesi = (
            self.kayit_getir(kayit)
            if isinstance(kayit, str)
            else kayit
        )
        dosya = kayit_nesnesi.dosya(dosya_turu)
        if dosya is None:
            raise BacktestHistoryError(
                "İstenen geçmiş rapor dosyası bulunamadı."
            )

        kayit_klasoru = self._kayit_klasoru(
            kayit_nesnesi.kayit_kimligi
        ).resolve()
        dosya_yolu = (kayit_klasoru / dosya.goreli_yol).resolve()
        if kayit_klasoru not in dosya_yolu.parents:
            raise BacktestHistoryError("Geçmiş rapor dosya yolu geçersiz.")
        try:
            return dosya_yolu.read_bytes()
        except OSError as hata:
            raise BacktestHistoryError(
                "Geçmiş rapor dosyası okunamadı."
            ) from hata

    def _kayit_klasorunu_sil(self, kayit_kimligi: str) -> None:
        kayit_klasoru = self._kayit_klasoru(kayit_kimligi)
        kok_klasor = self.kok_klasor.resolve()

        try:
            if kayit_klasoru.is_symlink():
                raise BacktestHistoryError(
                    "Analiz geçmişi kayıt klasörü bağlantı olamaz."
                )

            gercek_kayit_klasoru = kayit_klasoru.resolve()
            if gercek_kayit_klasoru.parent != kok_klasor:
                raise BacktestHistoryError(
                    "Analiz geçmişi silme yolu geçersiz."
                )
            if not kayit_klasoru.is_dir():
                raise BacktestHistoryError(
                    "Analiz geçmişi kaydı bulunamadı."
                )

            shutil.rmtree(kayit_klasoru)
        except BacktestHistoryError:
            raise
        except OSError as hata:
            raise BacktestHistoryError(
                "Analiz geçmişi kaydı silinemedi."
            ) from hata

    def _kaydi_yaz(
        self,
        kayit: BacktestHistoryRecord,
        dosya_verileri: Iterable[tuple[HistoryArtifact, bytes]],
    ) -> None:
        kayit_klasoru = self._kayit_klasoru(kayit.kayit_kimligi)
        try:
            kayit_klasoru.mkdir(parents=True, exist_ok=True)
            yeni_yollar: set[Path] = set()
            for dosya, veri in dosya_verileri:
                hedef = kayit_klasoru / dosya.goreli_yol
                _dosyayi_atomik_yaz(hedef, veri)
                yeni_yollar.add(hedef.resolve())

            for eski_dosya in kayit_klasoru.iterdir():
                if (
                    eski_dosya.is_file()
                    and eski_dosya.name != METADATA_DOSYASI
                    and eski_dosya.resolve() not in yeni_yollar
                ):
                    eski_dosya.unlink()

            metadata = json.dumps(
                kayit.sozluk(),
                ensure_ascii=False,
                indent=2,
            ).encode("utf-8")
            _dosyayi_atomik_yaz(
                kayit_klasoru / METADATA_DOSYASI,
                metadata,
            )
        except OSError as hata:
            raise BacktestHistoryError(
                "Analiz geçmişi diske yazılamadı."
            ) from hata

    def _metadata_oku(self, metadata_yolu: Path) -> BacktestHistoryRecord:
        veri = json.loads(metadata_yolu.read_text(encoding="utf-8"))
        kayit = BacktestHistoryRecord.sozlukten(veri)
        beklenen_klasor = self._kayit_klasoru(kayit.kayit_kimligi).resolve()
        if metadata_yolu.parent.resolve() != beklenen_klasor:
            raise ValueError("Geçmiş kayıt klasörü kimliğiyle uyuşmuyor.")
        return kayit

    def _kayit_klasoru(self, kayit_kimligi: str) -> Path:
        guvenli_kimlik = _guvenli_kimlik(kayit_kimligi)
        if guvenli_kimlik != kayit_kimligi:
            raise BacktestHistoryError("Analiz geçmişi kayıt kimliği geçersiz.")
        return self.kok_klasor / guvenli_kimlik


def _guncel_analiz_csv_baytlari(
    ozel_bilgiler: dict[str, object],
) -> bytes:
    """İç içe güncel analiz özetini iki sütunlu UTF-8 CSV'ye dönüştürür."""

    satirlar: list[tuple[str, object]] = []

    def duzlestir(onek: str, deger: object) -> None:
        if isinstance(deger, dict):
            for anahtar, alt_deger in deger.items():
                yeni_onek = f"{onek}.{anahtar}" if onek else str(anahtar)
                duzlestir(yeni_onek, alt_deger)
            return
        if isinstance(deger, (list, tuple)):
            satirlar.append((onek, " | ".join(str(item) for item in deger)))
            return
        satirlar.append((onek, "" if deger is None else deger))

    duzlestir("", ozel_bilgiler)
    metin = io.StringIO(newline="")
    yazici = csv.writer(metin, lineterminator="\n")
    yazici.writerow(("alan", "deger"))
    yazici.writerows(satirlar)
    return b"\xef\xbb\xbf" + metin.getvalue().encode("utf-8")


def _pdf_eklemeyi_dene(
    dosya_verileri: list[tuple[HistoryArtifact, bytes]],
    *,
    tur: str,
    dosya_adi: str,
    uretici: Callable[[], bytes],
) -> None:
    try:
        pdf = uretici()
    except ReportExportError:
        return

    dosya_verileri.append(
        (
            HistoryArtifact(
                tur=tur,
                dosya_adi=dosya_adi,
                mime="application/pdf",
                goreli_yol=dosya_adi,
            ),
            pdf,
        )
    )


def _kayit_kimligi(*parcalar: str) -> str:
    ham = "|".join(str(parca) for parca in parcalar)
    ozet = hashlib.sha256(ham.encode("utf-8")).hexdigest()[:16]
    onek = _guvenli_kimlik(parcalar[0])[:24]
    return f"{onek}_{ozet}"


def _guvenli_kimlik(deger: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "_", str(deger)).strip("_")


def _yerel_zaman() -> datetime:
    return datetime.now().astimezone()


def _zaman_metin(deger: datetime) -> str:
    if deger.tzinfo is None:
        deger = deger.astimezone()
    return deger.isoformat(timespec="seconds")


def _dosyayi_atomik_yaz(hedef: Path, veri: bytes) -> None:
    gecici = hedef.with_name(f".{hedef.name}.tmp")
    gecici.write_bytes(veri)
    gecici.replace(hedef)


def _istege_bagli_float(deger: object) -> float | None:
    return None if deger is None else float(deger)


def _istege_bagli_int(deger: object) -> int | None:
    return None if deger is None else int(deger)

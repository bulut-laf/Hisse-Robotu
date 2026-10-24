from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from hashlib import sha256
import json

from ..analysis.scan_filter import (
    NEGATIF_GORUNUM,
    NOTR_GORUNUM,
    POZITIF_GORUNUM,
    TUM_GORUNUMLER,
)
from .backtest_models import BacktestConfig
from .historical_signal_generator import HistoricalSignalGeneratorConfig


GECERLI_INDIRME_DONEMLERI = (
    "1d",
    "5d",
    "1mo",
    "3mo",
    "6mo",
    "1y",
    "2y",
    "5y",
    "10y",
    "ytd",
    "max",
)

GECERLI_GORUNUM_SECIMLERI = (
    "tum",
    "pozitif",
    "notr",
    "negatif",
    "pozitif-notr",
)

ORTAK_ISLEM_GUNU = 1253
ORTAK_INDIRME_DONEMI = "5y"
ORTAK_MINIMUM_BAR = 60
ORTAK_GORUNUM_SECIMI = "pozitif-notr"
ORTAK_ELDE_TUTMA_GUNU = 10
ORTAK_MINIMUM_SKOR = 50
ORTAK_BASLANGIC_SERMAYESI = 100_000.0
ORTAK_POZISYON_YUZDE = 100.0
ORTAK_MALIYET_YUZDE = 0.10
ORTAK_STOP_YUZDE = 5.0
ORTAK_HEDEF_YUZDE = 10.0


def gorunumleri_coz(secim: str) -> tuple[str, ...]:
    temiz_secim = secim.strip().casefold()

    donusumler = {
        "tum": TUM_GORUNUMLER,
        "pozitif": (POZITIF_GORUNUM,),
        "notr": (NOTR_GORUNUM,),
        "negatif": (NEGATIF_GORUNUM,),
        "pozitif-notr": (
            POZITIF_GORUNUM,
            NOTR_GORUNUM,
        ),
    }

    try:
        return donusumler[temiz_secim]
    except KeyError as hata:
        raise ValueError(
            "Geçersiz teknik görünüm seçimi: "
            f"{secim}. Geçerli değerler: "
            + ", ".join(GECERLI_GORUNUM_SECIMLERI)
        ) from hata


def sembolu_hazirla(sembol: str) -> str:
    temiz_sembol = sembol.strip().upper()

    if not temiz_sembol:
        raise ValueError("Hisse sembolü boş olamaz.")

    if "." not in temiz_sembol:
        temiz_sembol += ".IS"

    return temiz_sembol


@dataclass(frozen=True)
class AnalysisProfile:
    """Analiz komutlarının ortak veri, sinyal ve backtest ayarları."""

    islem_gunu: int = ORTAK_ISLEM_GUNU
    indirme_donemi: str = ORTAK_INDIRME_DONEMI
    minimum_bar_sayisi: int = ORTAK_MINIMUM_BAR
    gorunum_secimi: str = ORTAK_GORUNUM_SECIMI
    elde_tutma_gunu: int = ORTAK_ELDE_TUTMA_GUNU
    minimum_skor: int = ORTAK_MINIMUM_SKOR
    baslangic_sermayesi: float = ORTAK_BASLANGIC_SERMAYESI
    pozisyon_yuzde: float = ORTAK_POZISYON_YUZDE
    maliyet_yuzde: float = ORTAK_MALIYET_YUZDE
    stop_yuzde: float | None = ORTAK_STOP_YUZDE
    hedef_yuzde: float | None = ORTAK_HEDEF_YUZDE

    def __post_init__(self) -> None:
        temiz_donem = self.indirme_donemi.strip()
        temiz_gorunum = self.gorunum_secimi.strip().casefold()

        if self.islem_gunu <= 0:
            raise ValueError("İşlem günü sayısı pozitif olmalıdır.")

        if temiz_donem not in GECERLI_INDIRME_DONEMLERI:
            raise ValueError(
                "Geçersiz indirme dönemi: "
                f"{temiz_donem}. Geçerli değerler: "
                + ", ".join(GECERLI_INDIRME_DONEMLERI)
            )

        gorunumleri_coz(temiz_gorunum)

        object.__setattr__(self, "indirme_donemi", temiz_donem)
        object.__setattr__(self, "gorunum_secimi", temiz_gorunum)

        # Nihai doğrulama mevcut yapılandırma sınıflarına bırakılır.
        self.sinyal_yapilandirmasi()
        self.backtest_yapilandirmasi()

    def sinyal_yapilandirmasi(
        self,
        baslangic_tarihi: date | None = None,
        bitis_tarihi: date | None = None,
    ) -> HistoricalSignalGeneratorConfig:
        return HistoricalSignalGeneratorConfig(
            minimum_bar_sayisi=self.minimum_bar_sayisi,
            baslangic_tarihi=baslangic_tarihi,
            bitis_tarihi=bitis_tarihi,
            izin_verilen_gorunumler=gorunumleri_coz(
                self.gorunum_secimi
            ),
        )

    def backtest_yapilandirmasi(self) -> BacktestConfig:
        return BacktestConfig(
            elde_tutma_gunu=self.elde_tutma_gunu,
            minimum_skor=self.minimum_skor,
            baslangic_sermayesi=self.baslangic_sermayesi,
            pozisyon_orani=self.pozisyon_yuzde / 100.0,
            islem_maliyeti_orani=self.maliyet_yuzde / 100.0,
            zarar_durdur_orani=self._yuzdeyi_orana_cevir(
                self.stop_yuzde
            ),
            hedef_orani=self._yuzdeyi_orana_cevir(
                self.hedef_yuzde
            ),
        )

    @property
    def ayar_kimligi(self) -> str:
        icerik = json.dumps(
            asdict(self),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")

        return sha256(icerik).hexdigest()[:12]

    @staticmethod
    def _yuzdeyi_orana_cevir(
        deger: float | None,
    ) -> float | None:
        if deger is None:
            return None

        return deger / 100.0

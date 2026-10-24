from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Callable

import pandas as pd

from ..analysis.scan_filter import TUM_GORUNUMLER
from .backtest_models import BacktestSignal


GEREKLI_SUTUNLAR = (
    "Open",
    "High",
    "Low",
    "Close",
    "Volume",
)

AnalizFonksiyonu = Callable[
    [str, pd.DataFrame],
    object,
]


class HistoricalSignalGeneratorError(Exception):
    """Geçmiş sinyal üretiminde oluşan veri hatası."""


@dataclass(frozen=True)
class HistoricalSignalGeneratorConfig:
    """Geçmiş sinyal üretiminde kullanılacak ayarlardır."""

    minimum_bar_sayisi: int = 60
    baslangic_tarihi: date | None = None
    bitis_tarihi: date | None = None
    izin_verilen_gorunumler: tuple[str, ...] = (
        TUM_GORUNUMLER
    )

    def __post_init__(self) -> None:
        if self.minimum_bar_sayisi <= 0:
            raise ValueError(
                "Minimum bar sayısı pozitif olmalıdır."
            )

        if (
            self.baslangic_tarihi is not None
            and self.bitis_tarihi is not None
            and self.baslangic_tarihi
            > self.bitis_tarihi
        ):
            raise ValueError(
                "Başlangıç tarihi bitiş tarihinden "
                "sonra olamaz."
            )

        if not self.izin_verilen_gorunumler:
            raise ValueError(
                "En az bir teknik görünüm seçilmelidir."
            )

        gecersiz_gorunumler = set(
            self.izin_verilen_gorunumler
        ).difference(TUM_GORUNUMLER)

        if gecersiz_gorunumler:
            raise ValueError(
                "Geçersiz teknik görünüm: "
                + ", ".join(
                    sorted(gecersiz_gorunumler)
                )
            )


@dataclass(frozen=True)
class SkippedHistoricalSignal:
    """Sinyal üretilemeyen tarih ve nedenidir."""

    sembol: str
    tarih: date
    neden: str


@dataclass(frozen=True)
class HistoricalSignalGenerationResult:
    """Geçmiş sinyal üretiminin sonucudur."""

    sinyaller: tuple[BacktestSignal, ...]
    atlanan_gunler: tuple[
        SkippedHistoricalSignal,
        ...
    ]
    degerlendirilen_gun_sayisi: int

    @property
    def sinyal_sayisi(self) -> int:
        return len(self.sinyaller)

    @property
    def atlanan_gun_sayisi(self) -> int:
        return len(self.atlanan_gunler)


class HistoricalSignalGenerator:
    """
    Fiyat verisini tarih boyunca ilerleterek sinyal üretir.

    Analiz fonksiyonuna her değerlendirme tarihinde yalnızca
    o tarihe kadar oluşmuş fiyat verisi gönderilir. Son fiyat
    barı değerlendirilmez; çünkü backtest motorunun sonraki
    işlem gününde giriş yapabilmesi gerekir.
    """

    def __init__(
        self,
        analiz_fonksiyonu: AnalizFonksiyonu,
    ) -> None:
        if not callable(analiz_fonksiyonu):
            raise TypeError(
                "Analiz fonksiyonu çağrılabilir olmalıdır."
            )

        self._analiz_fonksiyonu = analiz_fonksiyonu

    def uret(
        self,
        sembol: str,
        fiyat_verisi: pd.DataFrame,
        yapilandirma: (
            HistoricalSignalGeneratorConfig | None
        ) = None,
    ) -> HistoricalSignalGenerationResult:
        ayarlar = (
            yapilandirma
            if yapilandirma is not None
            else HistoricalSignalGeneratorConfig()
        )

        temiz_sembol = sembol.strip().upper()

        if not temiz_sembol:
            raise HistoricalSignalGeneratorError(
                "Sembol boş olamaz."
            )

        veri = self._veriyi_hazirla(
            sembol=temiz_sembol,
            fiyat_verisi=fiyat_verisi,
        )

        ilk_konum = (
            ayarlar.minimum_bar_sayisi
            - 1
        )

        son_konum = len(veri) - 2

        if ilk_konum > son_konum:
            return HistoricalSignalGenerationResult(
                sinyaller=(),
                atlanan_gunler=(),
                degerlendirilen_gun_sayisi=0,
            )

        sinyaller: list[BacktestSignal] = []
        atlananlar: list[
            SkippedHistoricalSignal
        ] = []

        degerlendirilen_gun_sayisi = 0

        for konum in range(
            ilk_konum,
            son_konum + 1,
        ):
            sinyal_tarihi = veri.index[
                konum
            ].date()

            if (
                ayarlar.baslangic_tarihi
                is not None
                and sinyal_tarihi
                < ayarlar.baslangic_tarihi
            ):
                continue

            if (
                ayarlar.bitis_tarihi
                is not None
                and sinyal_tarihi
                > ayarlar.bitis_tarihi
            ):
                continue

            degerlendirilen_gun_sayisi += 1

            gecmis_penceresi = veri.iloc[
                : konum + 1
            ].copy()

            try:
                analiz = self._analiz_fonksiyonu(
                    temiz_sembol,
                    gecmis_penceresi,
                )

                skor, teknik_gorunum = (
                    self._sinyal_bilgilerini_al(
                        analiz
                    )
                )

            except Exception as hata:
                atlananlar.append(
                    SkippedHistoricalSignal(
                        sembol=temiz_sembol,
                        tarih=sinyal_tarihi,
                        neden=(
                            "Analiz başarısız: "
                            f"{type(hata).__name__}: "
                            f"{hata}"
                        ),
                    )
                )
                continue

            if (
                teknik_gorunum
                not in ayarlar.izin_verilen_gorunumler
            ):
                atlananlar.append(
                    SkippedHistoricalSignal(
                        sembol=temiz_sembol,
                        tarih=sinyal_tarihi,
                        neden=(
                            "Teknik görünüm izin verilen "
                            "grupta değil: "
                            f"{teknik_gorunum}."
                        ),
                    )
                )
                continue

            sinyaller.append(
                BacktestSignal(
                    sembol=temiz_sembol,
                    sinyal_tarihi=sinyal_tarihi,
                    skor=skor,
                    teknik_gorunum=teknik_gorunum,
                )
            )

        return HistoricalSignalGenerationResult(
            sinyaller=tuple(sinyaller),
            atlanan_gunler=tuple(
                atlananlar
            ),
            degerlendirilen_gun_sayisi=(
                degerlendirilen_gun_sayisi
            ),
        )

    def _veriyi_hazirla(
        self,
        sembol: str,
        fiyat_verisi: pd.DataFrame,
    ) -> pd.DataFrame:
        if not isinstance(
            fiyat_verisi,
            pd.DataFrame,
        ):
            raise HistoricalSignalGeneratorError(
                "Fiyat verisi pandas DataFrame olmalıdır."
            )

        eksik_sutunlar = [
            sutun
            for sutun in GEREKLI_SUTUNLAR
            if sutun not in fiyat_verisi.columns
        ]

        if eksik_sutunlar:
            raise HistoricalSignalGeneratorError(
                f"{sembol} fiyat verisinde eksik "
                "sütunlar var: "
                + ", ".join(eksik_sutunlar)
            )

        veri = fiyat_verisi.loc[
            :,
            list(GEREKLI_SUTUNLAR),
        ].copy()

        tarihler = pd.to_datetime(
            veri.index,
            errors="coerce",
        )

        if tarihler.isna().any():
            raise HistoricalSignalGeneratorError(
                f"{sembol} fiyat verisinde "
                "geçersiz tarihler var."
            )

        if tarihler.tz is not None:
            tarihler = tarihler.tz_localize(
                None
            )

        veri.index = tarihler.normalize()
        veri.index.name = "Date"

        veri = veri.sort_index()

        if veri.index.has_duplicates:
            raise HistoricalSignalGeneratorError(
                f"{sembol} fiyat verisinde "
                "tekrarlanan tarihler var."
            )

        for sutun in GEREKLI_SUTUNLAR:
            veri[sutun] = pd.to_numeric(
                veri[sutun],
                errors="coerce",
            )

        if veri.isna().any().any():
            raise HistoricalSignalGeneratorError(
                f"{sembol} fiyat verisinde "
                "boş veya sayısal olmayan değerler var."
            )

        fiyat_sutunlari = (
            "Open",
            "High",
            "Low",
            "Close",
        )

        if (
            veri.loc[
                :,
                list(fiyat_sutunlari),
            ]
            <= 0
        ).any().any():
            raise HistoricalSignalGeneratorError(
                f"{sembol} fiyat değerleri "
                "pozitif olmalıdır."
            )

        if (
            veri["Volume"] < 0
        ).any():
            raise HistoricalSignalGeneratorError(
                f"{sembol} hacim değerleri "
                "negatif olamaz."
            )

        if (
            veri["High"] < veri["Low"]
        ).any():
            raise HistoricalSignalGeneratorError(
                f"{sembol} verisinde en yüksek fiyat, "
                "en düşük fiyattan küçük olamaz."
            )

        if (
            veri["High"] < veri["Open"]
        ).any() or (
            veri["High"] < veri["Close"]
        ).any():
            raise HistoricalSignalGeneratorError(
                f"{sembol} verisinde en yüksek fiyat "
                "açılış veya kapanıştan küçük olamaz."
            )

        if (
            veri["Low"] > veri["Open"]
        ).any() or (
            veri["Low"] > veri["Close"]
        ).any():
            raise HistoricalSignalGeneratorError(
                f"{sembol} verisinde en düşük fiyat "
                "açılış veya kapanıştan büyük olamaz."
            )

        return veri

    def _sinyal_bilgilerini_al(
        self,
        analiz: object,
    ) -> tuple[int, str]:
        try:
            sinyal = getattr(
                analiz,
                "sinyal",
            )

            ham_skor = getattr(
                sinyal,
                "skor",
            )

            ham_gorunum = getattr(
                sinyal,
                "karar",
            )

        except AttributeError as hata:
            raise ValueError(
                "Analiz sonucu geçerli bir sinyal "
                "nesnesi içermiyor."
            ) from hata

        if isinstance(
            ham_skor,
            bool,
        ):
            raise ValueError(
                "Sinyal skoru sayısal olmalıdır."
            )

        try:
            skor = int(
                ham_skor
            )
        except (
            TypeError,
            ValueError,
        ) as hata:
            raise ValueError(
                "Sinyal skoru sayısal olmalıdır."
            ) from hata

        if not 0 <= skor <= 100:
            raise ValueError(
                "Sinyal skoru 0 ile 100 "
                "arasında olmalıdır."
            )

        teknik_gorunum = str(
            ham_gorunum
        ).strip()

        if not teknik_gorunum:
            raise ValueError(
                "Teknik görünüm boş olamaz."
            )

        return skor, teknik_gorunum
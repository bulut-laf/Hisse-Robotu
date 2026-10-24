from __future__ import annotations
from contextlib import closing

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from .scan_history import ScanHistoryError


@dataclass(frozen=True)
class ScanRunDetailSummary:
    """Seçilen taramanın filtrelerini ve sayılarını temsil eder."""

    tarama_id: int
    olusturma_zamani: str
    profil_adi: str
    minimum_skor: int
    minimum_hacim_orani: float
    risk_odul_gerekli: bool
    izin_verilen_gorunumler: tuple[str, ...]
    toplam_sayi: int
    aday_sayisi: int
    elenen_sayisi: int
    hatali_sayisi: int


@dataclass(frozen=True)
class ScanItemDetail:
    """Bir taramada bulunan tek bir hisse kaydını temsil eder."""

    durum: str
    sira: int | None
    sembol: str
    analiz_tarihi: str | None
    skor: int | None
    teknik_gorunum: str | None
    kapanis: float | None
    rsi14: float | None
    hacim_orani: float | None
    risk_odul_orani: float | None
    hedef_fiyat: float | None
    risk_filtresi_gecti: bool | None
    aciklama: str


@dataclass(frozen=True)
class ScanRunDetail:
    """Bir taramanın özetiyle birlikte bütün kayıtlarıdır."""

    ozet: ScanRunDetailSummary
    kayitlar: tuple[ScanItemDetail, ...]


class ScanHistoryReader:
    """SQLite veritabanındaki tarama ayrıntılarını okur."""

    def __init__(
        self,
        veritabani_yolu: str | Path,
    ) -> None:
        self._veritabani_yolu = Path(
            veritabani_yolu
        ).expanduser()

        if not self._veritabani_yolu.exists():
            raise ScanHistoryError(
                "Veritabanı dosyası bulunamadı: "
                f"{self._veritabani_yolu}"
            )

        if self._veritabani_yolu.is_dir():
            raise ScanHistoryError(
                "Veritabanı yolu bir klasör olamaz: "
                f"{self._veritabani_yolu}"
            )

    @property
    def veritabani_yolu(self) -> str:
        return str(
            self._veritabani_yolu.resolve()
        )

    def tarama_detayini_getir(
        self,
        tarama_id: int,
    ) -> ScanRunDetail:
        """Belirtilen taramanın özetini ve hisselerini getirir."""
        if tarama_id <= 0:
            raise ValueError(
                "Tarama kimliği pozitif olmalıdır."
            )

        try:
            with closing(self._baglanti_ac()) as baglanti, baglanti:
                tarama_satiri = baglanti.execute(
                    """
                    SELECT
                        id,
                        created_at,
                        profile_name,
                        minimum_score,
                        minimum_volume_ratio,
                        risk_reward_required,
                        allowed_views,
                        total_count,
                        candidate_count,
                        rejected_count,
                        error_count
                    FROM scan_runs
                    WHERE id = ?
                    """,
                    (tarama_id,),
                ).fetchone()

                if tarama_satiri is None:
                    raise ValueError(
                        f"Tarama bulunamadı: {tarama_id}"
                    )

                hisse_satirlari = baglanti.execute(
                    """
                    SELECT
                        status,
                        rank_number,
                        symbol,
                        analysis_date,
                        score,
                        technical_view,
                        closing_price,
                        rsi14,
                        volume_ratio,
                        risk_reward_ratio,
                        target_price,
                        risk_filter_passed,
                        explanation
                    FROM scan_items
                    WHERE scan_run_id = ?
                    ORDER BY
                        CASE status
                            WHEN 'Aday' THEN 1
                            WHEN 'Elendi' THEN 2
                            WHEN 'Hata' THEN 3
                            ELSE 4
                        END,
                        CASE
                            WHEN rank_number IS NULL
                            THEN 999999
                            ELSE rank_number
                        END,
                        id
                    """,
                    (tarama_id,),
                ).fetchall()

        except ValueError:
            raise

        except sqlite3.Error as hata:
            raise ScanHistoryError(
                f"Tarama ayrıntıları okunamadı: {hata}"
            ) from hata

        izin_verilen_gorunumler = (
            self._gorunumleri_coz(
                tarama_satiri["allowed_views"]
            )
        )

        ozet = ScanRunDetailSummary(
            tarama_id=int(
                tarama_satiri["id"]
            ),
            olusturma_zamani=str(
                tarama_satiri["created_at"]
            ),
            profil_adi=str(
                tarama_satiri["profile_name"]
            ),
            minimum_skor=int(
                tarama_satiri["minimum_score"]
            ),
            minimum_hacim_orani=float(
                tarama_satiri[
                    "minimum_volume_ratio"
                ]
            ),
            risk_odul_gerekli=bool(
                tarama_satiri[
                    "risk_reward_required"
                ]
            ),
            izin_verilen_gorunumler=(
                izin_verilen_gorunumler
            ),
            toplam_sayi=int(
                tarama_satiri["total_count"]
            ),
            aday_sayisi=int(
                tarama_satiri["candidate_count"]
            ),
            elenen_sayisi=int(
                tarama_satiri["rejected_count"]
            ),
            hatali_sayisi=int(
                tarama_satiri["error_count"]
            ),
        )

        kayitlar = tuple(
            self._hisse_detayi_olustur(
                satir
            )
            for satir in hisse_satirlari
        )

        return ScanRunDetail(
            ozet=ozet,
            kayitlar=kayitlar,
        )

    def _baglanti_ac(
        self,
    ) -> sqlite3.Connection:
        baglanti = sqlite3.connect(
            self._veritabani_yolu
        )

        baglanti.row_factory = sqlite3.Row
        baglanti.execute(
            "PRAGMA foreign_keys = ON"
        )

        return baglanti

    def _gorunumleri_coz(
        self,
        json_metni: str,
    ) -> tuple[str, ...]:
        try:
            deger = json.loads(
                json_metni
            )

        except (
            json.JSONDecodeError,
            TypeError,
        ) as hata:
            raise ScanHistoryError(
                "Kayıtlı teknik görünüm bilgisi "
                "okunamadı."
            ) from hata

        if not isinstance(deger, list):
            raise ScanHistoryError(
                "Kayıtlı teknik görünüm bilgisi "
                "geçerli bir liste değil."
            )

        if not all(
            isinstance(gorunum, str)
            for gorunum in deger
        ):
            raise ScanHistoryError(
                "Teknik görünüm listesindeki "
                "değerler geçersiz."
            )

        return tuple(deger)

    def _hisse_detayi_olustur(
        self,
        satir: sqlite3.Row,
    ) -> ScanItemDetail:
        risk_filtresi = satir[
            "risk_filter_passed"
        ]

        return ScanItemDetail(
            durum=str(
                satir["status"]
            ),
            sira=(
                int(satir["rank_number"])
                if satir["rank_number"] is not None
                else None
            ),
            sembol=str(
                satir["symbol"]
            ),
            analiz_tarihi=(
                str(satir["analysis_date"])
                if satir["analysis_date"] is not None
                else None
            ),
            skor=(
                int(satir["score"])
                if satir["score"] is not None
                else None
            ),
            teknik_gorunum=(
                str(satir["technical_view"])
                if satir["technical_view"] is not None
                else None
            ),
            kapanis=(
                float(satir["closing_price"])
                if satir["closing_price"] is not None
                else None
            ),
            rsi14=(
                float(satir["rsi14"])
                if satir["rsi14"] is not None
                else None
            ),
            hacim_orani=(
                float(satir["volume_ratio"])
                if satir["volume_ratio"] is not None
                else None
            ),
            risk_odul_orani=(
                float(
                    satir["risk_reward_ratio"]
                )
                if satir[
                    "risk_reward_ratio"
                ] is not None
                else None
            ),
            hedef_fiyat=(
                float(satir["target_price"])
                if satir["target_price"] is not None
                else None
            ),
            risk_filtresi_gecti=(
                bool(risk_filtresi)
                if risk_filtresi is not None
                else None
            ),
            aciklama=str(
                satir["explanation"]
            ),
        )
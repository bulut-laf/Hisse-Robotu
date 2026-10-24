from __future__ import annotations

import json
from dataclasses import asdict, replace
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable, Protocol


SINIF_SIKISMA = "E0 — Sıkışma Oluşuyor"
SINIF_HACIM_BIRIKIMI = "E1 — Hacim Birikimi Başladı"
SINIF_DIRENCE_YAKLASIYOR = "E2 — Dirence Yaklaşıyor"
SINIF_ERKEN_UYARI = "E3 — Kırılım Öncesi Erken Uyarı"
SINIF_KIRILIM = "B — Kırılım Başladı"
SINIF_ISLEME_HAZIR = "C — İşleme Hazır Aday"
SINIF_ASIRI_YUKSELMIS = "D — Aşırı Yükselmiş"
SINIF_KALICI_HAZIRLIK = "K — Kalıcı Hazırlık Adayı"
SINIF_IZLEME_DISI = "İzleme Dışı"
SINIF_ERKEN_KESIF_ESKI = "A — Erken Keşif"

HAZIRLIK_SINIFLARI = {
    SINIF_SIKISMA,
    SINIF_HACIM_BIRIKIMI,
    SINIF_DIRENCE_YAKLASIYOR,
    SINIF_ERKEN_UYARI,
    SINIF_ERKEN_KESIF_ESKI,
}
GUCLU_SINIFLAR = {SINIF_ERKEN_UYARI, SINIF_KIRILIM, SINIF_ISLEME_HAZIR}
GORUNUR_SINIFLAR = HAZIRLIK_SINIFLARI | {
    SINIF_KIRILIM,
    SINIF_ISLEME_HAZIR,
    SINIF_ASIRI_YUKSELMIS,
    SINIF_KALICI_HAZIRLIK,
}


class CandidateLike(Protocol):
    sembol: str
    analiz_tarihi: str
    kapanis: float
    sinif: str


class MomentumHistoryStore:
    """Momentum adaylarını saklar, sınıf zinciri ve kalıcı hazırlık üretir."""

    def __init__(self, kok_klasor: str | Path | None = None) -> None:
        self.kok_klasor = Path(kok_klasor).expanduser() if kok_klasor else (
            Path.home() / ".hisse_robotu" / "momentum_gecmisi"
        )

    def kaydet(self, adaylar: Iterable[CandidateLike]) -> Path:
        self.kok_klasor.mkdir(parents=True, exist_ok=True)
        zaman = datetime.now()
        yol = self.kok_klasor / f"momentum_{zaman:%Y%m%d_%H%M%S_%f}.json"
        veri = {
            "kayit_zamani": zaman.isoformat(timespec="seconds"),
            "adaylar": [asdict(aday) for aday in adaylar],
        }
        yol.write_text(json.dumps(veri, ensure_ascii=False, indent=2), encoding="utf-8")
        return yol

    def zenginlestir(self, adaylar: Iterable[object]) -> tuple[object, ...]:
        gecmis = self._gecmis_kayitlari()
        sonuc: list[object] = []
        for aday in adaylar:
            sembol = str(getattr(aday, "sembol"))
            analiz_tarihi = str(getattr(aday, "analiz_tarihi"))
            ham_sinif = str(getattr(aday, "sinif"))
            kapanis = float(getattr(aday, "kapanis"))

            ilgili = [
                kayit
                for kayit in gecmis
                if kayit.get("sembol") == sembol
                and str(kayit.get("analiz_tarihi", "")) <= analiz_tarihi
            ]
            birlesik = self._tarihe_gore_tekillestir(
                ilgili
                + [
                    {
                        "sembol": sembol,
                        "analiz_tarihi": analiz_tarihi,
                        "kapanis": kapanis,
                        "sinif": ham_sinif,
                    }
                ]
            )

            gorunur = [
                kayit
                for kayit in birlesik
                if str(kayit.get("sinif", "")) in GORUNUR_SINIFLAR
            ]
            if gorunur:
                ilk = gorunur[0]
                ilk_fiyat = float(ilk.get("kapanis", kapanis))
                ilk_tarih = str(ilk.get("analiz_tarihi", analiz_tarihi))
                gunler = {
                    str(k.get("analiz_tarihi", ""))
                    for k in gorunur
                    if k.get("analiz_tarihi")
                }
            else:
                ilk_fiyat = kapanis
                ilk_tarih = analiz_tarihi
                gunler = {analiz_tarihi}

            sinyal_gecmisi = tuple(
                f"{str(k.get('analiz_tarihi', ''))} · {str(k.get('sinif', ''))}"
                for k in birlesik[-6:]
            )
            son_hazirlik = self._son_tarih(birlesik, HAZIRLIK_SINIFLARI)
            son_guclu = self._son_tarih(birlesik, GUCLU_SINIFLAR)
            kalici = self._kalici_hazirlik_mi(
                ham_sinif=ham_sinif,
                analiz_tarihi=analiz_tarihi,
                kayitlar=birlesik,
            )
            sinif = SINIF_KALICI_HAZIRLIK if kalici else ham_sinif
            mevcut_hazirlik = str(getattr(aday, "hazirlik_durumu", ""))
            if kalici:
                mevcut_hazirlik = (
                    "Kalıcı hazırlık: yakın geçmişte birden fazla E0-E3 sinyali "
                    "oluştu; günlük sınıf zayıflasa da izleme sürdürülüyor."
                )
                gunler.add(analiz_tarihi)

            getiri = (kapanis / ilk_fiyat - 1.0) if ilk_fiyat else 0.0
            sonuc.append(
                replace(
                    aday,
                    sinif=sinif,
                    hazirlik_durumu=mevcut_hazirlik,
                    listedeki_gun=len(gunler),
                    ilk_gorulme_tarihi=ilk_tarih,
                    ilk_gorulme_fiyati=ilk_fiyat,
                    ilk_gorulmeden_getiri=getiri,
                    sinyal_gecmisi=sinyal_gecmisi,
                    kalici_hazirlik=kalici,
                    son_hazirlik_sinyali_tarihi=son_hazirlik,
                    son_guclu_sinyal_tarihi=son_guclu,
                )
            )
        return tuple(sonuc)

    @staticmethod
    def _kalici_hazirlik_mi(
        *,
        ham_sinif: str,
        analiz_tarihi: str,
        kayitlar: list[dict[str, object]],
    ) -> bool:
        if ham_sinif != SINIF_IZLEME_DISI:
            return False
        bugun = _tarih(analiz_tarihi)
        if bugun is None:
            return False
        alt_sinir = bugun - timedelta(days=30)
        hazirliklar: list[date] = []
        for kayit in kayitlar:
            if str(kayit.get("sinif", "")) not in HAZIRLIK_SINIFLARI:
                continue
            tarih = _tarih(str(kayit.get("analiz_tarihi", "")))
            if tarih is not None and alt_sinir <= tarih <= bugun:
                hazirliklar.append(tarih)
        if len(set(hazirliklar)) < 2:
            return False
        return (bugun - max(hazirliklar)).days <= 10

    @staticmethod
    def _son_tarih(
        kayitlar: list[dict[str, object]], siniflar: set[str]
    ) -> str:
        uygun = [
            str(k.get("analiz_tarihi", ""))
            for k in kayitlar
            if str(k.get("sinif", "")) in siniflar and k.get("analiz_tarihi")
        ]
        return max(uygun) if uygun else ""

    @staticmethod
    def _tarihe_gore_tekillestir(
        kayitlar: list[dict[str, object]],
    ) -> list[dict[str, object]]:
        harita: dict[str, dict[str, object]] = {}
        for kayit in kayitlar:
            tarih = str(kayit.get("analiz_tarihi", ""))
            if tarih:
                harita[tarih] = kayit
        return [harita[tarih] for tarih in sorted(harita)]

    def _gecmis_kayitlari(self) -> list[dict[str, object]]:
        if not self.kok_klasor.is_dir():
            return []
        kayitlar: list[dict[str, object]] = []
        for yol in sorted(self.kok_klasor.glob("momentum_*.json")):
            try:
                veri = json.loads(yol.read_text(encoding="utf-8"))
                adaylar = veri.get("adaylar", [])
                if isinstance(adaylar, list):
                    kayitlar.extend(k for k in adaylar if isinstance(k, dict))
            except (OSError, json.JSONDecodeError):
                continue
        return kayitlar


def _tarih(metin: str) -> date | None:
    try:
        return date.fromisoformat(metin)
    except ValueError:
        return None

from __future__ import annotations
import csv

from dataclasses import dataclass
import re

import pandas as pd

from backend.app.analysis.bist_universe import BistUniverseRepository
from backend.app.data.batch_market_data import BatchMarketDataFailure, toplu_fiyat_verisi_getir
from pathlib import Path


@dataclass(frozen=True)
class BistDailyMarketResult:
    tablo: pd.DataFrame
    evren_adi: str
    evren_sembol_sayisi: int
    veri_hazir: int
    veri_hatasi: int
    evren_kaynagi: str
    evren_tarihi: str
    kaynak_sirasi: tuple[str, ...]
    kaynak_hatalari: tuple[str, ...]
    hatalar: tuple[BatchMarketDataFailure, ...]


def _gunluk_satir(sembol: str, frame: pd.DataFrame) -> dict[str, object] | None:
    if frame is None or frame.empty or len(frame) < 2:
        return None

    x = frame.sort_index()
    son = x.iloc[-1]
    onceki = x.iloc[-2]

    close = float(son["Close"])
    prev_close = float(onceki["Close"])
    change_tl = close - prev_close
    change_pct = (100.0 * change_tl / prev_close) if prev_close else 0.0

    return {
        "Hisse": sembol.removesuffix(".IS"),
        "Son Fiyat": close,
        "Günlük Değişim %": change_pct,
        "Günlük Değişim TL": change_tl,
        "Açılış": float(son["Open"]),
        "En Düşük": float(son["Low"]),
        "En Yüksek": float(son["High"]),
        "Önceki Kapanış": prev_close,
        "Hacim": float(son["Volume"]),
        "Veri Tarihi": pd.Timestamp(x.index[-1]).date().isoformat(),
    }


def _sonuc_olustur(evren, semboller: list[str], *, evren_adi: str) -> BistDailyMarketResult:
    batch = toplu_fiyat_verisi_getir(
        semboller,
        islem_gunu=2,
        indirme_donemi="1mo",
        parca_boyutu=40,
    )

    satirlar: list[dict[str, object]] = []
    for sembol, frame in batch.veriler.items():
        satir = _gunluk_satir(sembol, frame)
        if satir is not None:
            satirlar.append(satir)

    tablo = pd.DataFrame(satirlar)
    if not tablo.empty:
        tablo = tablo.sort_values(
            ["Günlük Değişim %", "Hisse"],
            ascending=[False, True],
        ).reset_index(drop=True)

    return BistDailyMarketResult(
        tablo=tablo,
        evren_adi=evren_adi,
        evren_sembol_sayisi=len(semboller),
        veri_hazir=len(batch.veriler),
        veri_hatasi=len(batch.hatalar),
        evren_kaynagi=evren.kaynak,
        evren_tarihi=evren.tarih,
        kaynak_sirasi=batch.kaynak_sirasi,
        kaynak_hatalari=batch.kaynak_hatalari,
        hatalar=batch.hatalar,
    )


def bist_gunluk_piyasa_olustur(
    *,
    evren_adi: str = "BIST Tüm",
    internetten_guncelle: bool = False,
) -> BistDailyMarketResult:
    evren = BistUniverseRepository().evreni_yukle(
        evren_adi,
        internetten_guncelle=internetten_guncelle,
    )
    return _sonuc_olustur(evren, list(evren.semboller), evren_adi=evren.ad)


def bist_tum_sembollerini_yukle(*, internetten_guncelle: bool = False) -> tuple[object, list[str]]:
    evren = BistUniverseRepository().evreni_yukle(
        "BIST Tüm",
        internetten_guncelle=internetten_guncelle,
    )
    return evren, [str(x).upper() for x in evren.semboller]


# V11_TRACK4_COMPANY_NAME_MATCHING
def bist_tum_sirket_adlarini_yukle() -> dict[str, str]:
    # Mevcut resmi BIST bilesen CSV'sindeki sembol -> sirket adi eslemesini yukler.
    backend = Path(__file__).resolve().parents[2]
    candidates = (
        backend / "cache" / "bist_endeks_bilesenleri.csv",
        backend / "resources" / "bist_endeks_bilesenleri.csv",
    )

    for path in candidates:
        if not path.exists():
            continue
        try:
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.reader(handle, delimiter=";")
                rows = list(reader)
        except (OSError, UnicodeError, csv.Error):
            continue

        names: dict[str, str] = {}
        for row in rows:
            if len(row) < 2:
                continue
            code = str(row[0]).strip().upper()
            company_name = str(row[1]).strip()
            if not code or not company_name:
                continue
            if code in {"BILESEN KODU", "CONSTITUENT CODE"}:
                continue
            symbol = code.removesuffix(".E").removesuffix(".IS")
            if symbol:
                names.setdefault(symbol, company_name)
        if names:
            return names

    return {}


def ozel_liste_girdilerini_ayir(text: str) -> list[str]:
    parts = re.split(r"[\s,;\n\r\t]+", text or "")
    out: list[str] = []
    seen: set[str] = set()
    for raw in parts:
        token = raw.strip().upper().removesuffix(".IS")
        if token and token not in seen:
            out.append(token)
            seen.add(token)
    return out


def sembol_eslesmeleri(
    token: str,
    universe_symbols: list[str],
    *,
    company_names: dict[str, str] | None = None,
) -> list[str]:
    q = token.strip().upper().removesuffix(".IS")
    if not q:
        return []

    canonical = [s.removesuffix(".IS") for s in universe_symbols]

    exact = sorted({s for s in canonical if s == q})
    if exact:
        return exact

    starts = sorted({s for s in canonical if s.startswith(q)})
    if starts:
        return starts

    contains = sorted({s for s in canonical if q in s})
    if contains:
        return contains

    if not company_names:
        return []

    normalized_names = {
        symbol.removesuffix(".IS").upper(): str(name).strip().upper()
        for symbol, name in company_names.items()
        if str(symbol).strip() and str(name).strip()
    }

    name_exact = sorted({s for s in canonical if normalized_names.get(s) == q})
    if name_exact:
        return name_exact

    name_starts = sorted({
        s for s in canonical
        if normalized_names.get(s, "").startswith(q)
    })
    if name_starts:
        return name_starts

    return sorted({
        s for s in canonical
        if q in normalized_names.get(s, "")
    })


def bist_ozel_liste_olustur(
    semboller: list[str],
    *,
    internetten_guncelle: bool = False,
) -> BistDailyMarketResult:
    evren, universe_symbols = bist_tum_sembollerini_yukle(
        internetten_guncelle=internetten_guncelle
    )
    universe_set = set(universe_symbols)

    normalized: list[str] = []
    seen: set[str] = set()
    for symbol in semboller:
        s = str(symbol).strip().upper()
        if not s.endswith(".IS"):
            s += ".IS"
        if s in universe_set and s not in seen:
            normalized.append(s)
            seen.add(s)

    return _sonuc_olustur(evren, normalized, evren_adi="Özel Liste")

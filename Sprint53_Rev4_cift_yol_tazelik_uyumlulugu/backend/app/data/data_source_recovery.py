from __future__ import annotations

import hashlib
import io
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from urllib.parse import urlencode
from urllib.request import urlopen

import pandas as pd

from .data_freshness import gunluk_veri_tazeligini_degerlendir
from .market_data import fiyat_verisini_duzelt


class DataSourceRecoveryError(Exception):
    """Birincil, ikincil ve önbellek kaynaklarının tamamı başarısız olduğunda kullanılır."""


@dataclass(frozen=True)
class RecoveredMarketData:
    veri: pd.DataFrame
    kaynak: str
    kaynak_sirasi: tuple[str, ...]
    kaynak_hatalari: tuple[str, ...]


SecondaryLoader = Callable[[str], pd.DataFrame]
FreshnessEvaluator = Callable[[pd.DataFrame], object]


def _cache_paths(cache_root: Path, symbol: str) -> tuple[Path, Path]:
    safe = symbol.replace("^", "_").replace(".", "_").replace("/", "_")
    return cache_root / f"{safe}.csv", cache_root / f"{safe}.json"


def cache_write(cache_root: Path, symbol: str, frame: pd.DataFrame) -> None:
    cache_root.mkdir(parents=True, exist_ok=True)
    csv_path, meta_path = _cache_paths(cache_root, symbol)
    normalized = fiyat_verisini_duzelt(frame, yalnizca_tamamlanmis_gunler=True)
    csv_text = normalized.to_csv(index=True, lineterminator="\n")
    csv_path.write_text(csv_text, encoding="utf-8")
    meta = {
        "symbol": symbol,
        "rows": len(normalized),
        "first_date": str(pd.Timestamp(normalized.index[0]).date()),
        "last_date": str(pd.Timestamp(normalized.index[-1]).date()),
        "sha256": hashlib.sha256(csv_text.encode("utf-8")).hexdigest(),
        "written_at": datetime.now(timezone.utc).isoformat(),
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def cache_read(cache_root: Path, symbol: str) -> pd.DataFrame:
    csv_path, meta_path = _cache_paths(cache_root, symbol)
    if not csv_path.exists() or not meta_path.exists():
        raise DataSourceRecoveryError("Yerel önbellek kaydı bulunamadı.")
    csv_text = csv_path.read_text(encoding="utf-8")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    if hashlib.sha256(csv_text.encode("utf-8")).hexdigest() != meta.get("sha256"):
        raise DataSourceRecoveryError("Yerel önbellek bütünlük doğrulamasını geçemedi.")
    frame = pd.read_csv(io.StringIO(csv_text), index_col=0, parse_dates=True)
    frame = fiyat_verisini_duzelt(frame, yalnizca_tamamlanmis_gunler=True)
    if len(frame) != int(meta.get("rows", -1)):
        raise DataSourceRecoveryError("Yerel önbellek satır sayısı doğrulanamadı.")
    freshness = gunluk_veri_tazeligini_degerlendir(frame)
    if freshness.kilitli:
        raise DataSourceRecoveryError("Yerel önbellek güncel değil: " + freshness.aciklama)
    return frame


def alpha_vantage_daily_loader(symbol: str) -> pd.DataFrame:
    api_key = os.getenv("HISSE_ROBOTU_ALPHA_VANTAGE_API_KEY", "").strip()
    if not api_key:
        raise DataSourceRecoveryError("Alpha Vantage API anahtarı tanımlı değil.")
    raw_map = os.getenv("HISSE_ROBOTU_ALPHA_VANTAGE_SYMBOL_MAP", "{}")
    try:
        symbol_map = json.loads(raw_map)
    except json.JSONDecodeError as exc:
        raise DataSourceRecoveryError("Alpha Vantage sembol eşleme JSON'u geçersiz.") from exc
    provider_symbol = str(symbol_map.get(symbol, symbol))
    query = urlencode({
        "function": "TIME_SERIES_DAILY",
        "symbol": provider_symbol,
        "outputsize": "full",
        "datatype": "csv",
        "apikey": api_key,
    })
    try:
        with urlopen("https://www.alphavantage.co/query?" + query, timeout=30) as response:
            payload = response.read()
    except Exception as exc:
        raise DataSourceRecoveryError(f"Alpha Vantage bağlantı hatası: {exc}") from exc
    frame = pd.read_csv(io.BytesIO(payload))
    required = {"timestamp", "open", "high", "low", "close", "volume"}
    if not required.issubset(frame.columns):
        message = payload.decode("utf-8", errors="replace")[:300]
        raise DataSourceRecoveryError("Alpha Vantage beklenen OHLCV yanıtını üretmedi: " + message)
    frame = frame.rename(columns={
        "timestamp": "Date", "open": "Open", "high": "High",
        "low": "Low", "close": "Close", "volume": "Volume",
    })
    frame["Date"] = pd.to_datetime(frame["Date"])
    return fiyat_verisini_duzelt(
        frame.set_index("Date").sort_index(),
        yalnizca_tamamlanmis_gunler=True,
    )


def recover_daily_market_data(
    symbol: str,
    *,
    primary_loader: Callable[[], pd.DataFrame],
    secondary_loader: SecondaryLoader | None = None,
    cache_root: Path | None = None,
    freshness_evaluator: FreshnessEvaluator | None = None,
) -> RecoveredMarketData:
    cache_root = cache_root or Path("backend/cache/market_data")
    evaluator = freshness_evaluator or gunluk_veri_tazeligini_degerlendir
    order: list[str] = []
    failures: list[str] = []

    order.append("birincil")
    try:
        frame = fiyat_verisini_duzelt(primary_loader(), yalnizca_tamamlanmis_gunler=True)
        freshness = evaluator(frame)
        if freshness.kilitli:
            raise DataSourceRecoveryError(freshness.aciklama)
        cache_write(cache_root, symbol, frame)
        return RecoveredMarketData(frame, "birincil", tuple(order), tuple(failures))
    except Exception as exc:
        failures.append(f"birincil: {exc}")

    order.append("ikincil")
    try:
        frame = (secondary_loader or alpha_vantage_daily_loader)(symbol)
        freshness = evaluator(frame)
        if freshness.kilitli:
            raise DataSourceRecoveryError(freshness.aciklama)
        cache_write(cache_root, symbol, frame)
        return RecoveredMarketData(frame, "ikincil", tuple(order), tuple(failures))
    except Exception as exc:
        failures.append(f"ikincil: {exc}")

    order.append("önbellek")
    try:
        frame = cache_read(cache_root, symbol)
        return RecoveredMarketData(frame, "önbellek", tuple(order), tuple(failures))
    except Exception as exc:
        failures.append(f"önbellek: {exc}")

    raise DataSourceRecoveryError("Tüm veri kaynakları başarısız. " + " | ".join(failures))

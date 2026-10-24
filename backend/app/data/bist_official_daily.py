from __future__ import annotations

import csv
import io
import re
import unicodedata
import urllib.error
import urllib.request
import zipfile
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Callable, Iterable

import pandas as pd


BIST_BASE_URL = "https://www.borsaistanbul.com/data/thb"
DEFAULT_SUFFIX_CANDIDATES = ("1", "2", "3", "")
REQUIRED_PRICE_COLUMNS = ("Open", "High", "Low", "Close", "Volume")


class BistOfficialDailyError(RuntimeError):
    """Borsa İstanbul resmî günlük veri katmanı hatası."""


@dataclass(frozen=True)
class OfficialDailyBatchResult:
    islem_tarihi: date
    kaynak_url: str
    veriler: dict[str, pd.DataFrame]
    bulunamayan_semboller: tuple[str, ...]
    arsiv_dosyasi: Path | None = None
    gecersiz_semboller: tuple[str, ...] = ()


def _normalize_header(value: str) -> str:
    text = (value or "").strip()
    text = text.replace("İ", "I").replace("ı", "i")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.upper()
    return re.sub(r"[^A-Z0-9]+", "", text)


def _resolve_field(fieldnames: Iterable[str], *candidates: str) -> str | None:
    normalized = {
        _normalize_header(name): name
        for name in fieldnames
        if name
    }
    for candidate in candidates:
        match = normalized.get(_normalize_header(candidate))
        if match:
            return match
    return None


def _to_decimal(value: str | None) -> Decimal | None:
    text = (value or "").strip()
    if not text:
        return None
    try:
        return Decimal(text.replace(",", "."))
    except InvalidOperation:
        return None


def normalize_symbol(symbol: str) -> str:
    value = (symbol or "").strip().upper()
    if value.endswith(".IS"):
        value = value[:-3]
    if value.endswith(".E"):
        value = value[:-2]
    if not value:
        raise ValueError("Sembol boş olamaz.")
    return value


def yahoo_style_symbol(symbol: str) -> str:
    return f"{normalize_symbol(symbol)}.IS"


def bulletin_filename(islem_tarihi: date, suffix: str = "1") -> str:
    return f"thb{islem_tarihi:%Y%m%d}{suffix}.zip"


def bulletin_url(islem_tarihi: date, suffix: str = "1") -> str:
    return (
        f"{BIST_BASE_URL}/{islem_tarihi:%Y}/{islem_tarihi:%m}/"
        f"{bulletin_filename(islem_tarihi, suffix)}"
    )


def _default_fetch(url: str, timeout: float = 30.0) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 Hisse-Robotu-BIST-Official/1.1",
            "Accept": "application/zip,*/*",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        payload = response.read()

    if not payload.startswith(b"PK"):
        raise BistOfficialDailyError(
            f"Borsa İstanbul yanıtı ZIP değil: {url}"
        )
    return payload


def download_bulletin_zip(
    islem_tarihi: date,
    *,
    fetcher: Callable[[str], bytes] | None = None,
    suffix_candidates: Iterable[str] = DEFAULT_SUFFIX_CANDIDATES,
) -> tuple[str, bytes]:
    fetch = fetcher or _default_fetch
    errors: list[str] = []

    for suffix in suffix_candidates:
        url = bulletin_url(islem_tarihi, suffix)
        try:
            payload = fetch(url)
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                errors.append(f"{url} -> 404")
                continue
            raise BistOfficialDailyError(
                f"Borsa İstanbul HTTP hatası {exc.code}: {url}"
            ) from exc
        except FileNotFoundError:
            errors.append(f"{url} -> bulunamadı")
            continue
        except BistOfficialDailyError:
            raise
        except Exception as exc:
            if "404" in str(exc):
                errors.append(f"{url} -> 404")
                continue
            raise BistOfficialDailyError(
                f"Borsa İstanbul bülteni indirilemedi: {url}: {exc}"
            ) from exc

        if not payload.startswith(b"PK"):
            raise BistOfficialDailyError(
                f"Borsa İstanbul yanıtı ZIP değil: {url}"
            )
        return url, payload

    detail = "; ".join(errors) if errors else "aday URL yok"
    raise BistOfficialDailyError(
        f"{islem_tarihi.isoformat()} için resmî bülten ZIP'i bulunamadı. {detail}"
    )


def _read_csv_from_zip(zip_bytes: bytes) -> str:
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            csv_names = [
                name for name in zf.namelist()
                if name.lower().endswith(".csv")
                and not name.startswith("__MACOSX/")
            ]
            if not csv_names:
                raise BistOfficialDailyError("Resmî ZIP içinde CSV bulunamadı.")
            raw = zf.read(csv_names[0])
    except zipfile.BadZipFile as exc:
        raise BistOfficialDailyError("Resmî bülten ZIP dosyası bozuk.") from exc

    for encoding in ("utf-8-sig", "utf-8", "cp1254", "latin1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue

    raise BistOfficialDailyError("Resmî CSV metin kodlaması çözülemedi.")


def _resolve_required_fields(fieldnames: list[str]) -> dict[str, str]:
    candidates = {
        "date": ("TARIH",),
        "code": ("ISLEM KODU", "ISLEM  KODU"),
        "group": ("ENSTRUMAN GRUBU",),
        "open": ("ACILIS FIYATI",),
        "high": ("EN YUKSEK FIYAT", "ENYUKSEK FIYAT"),
        "low": ("EN DUSUK FIYAT", "ENDUSUK FIYAT"),
        "close": ("KAPANIS FIYATI",),
        "volume": ("TOPLAM ISLEM ADEDI",),
    }

    resolved: dict[str, str] = {}
    for key, names in candidates.items():
        field = _resolve_field(fieldnames, *names)
        if field is None:
            raise BistOfficialDailyError(
                f"Resmî CSV zorunlu kolonu bulunamadı: {key}"
            )
        resolved[key] = field
    return resolved


def _validate_ohlcv(
    symbol: str,
    open_: Decimal,
    high: Decimal,
    low: Decimal,
    close: Decimal,
    volume: Decimal,
) -> None:
    if any(value <= 0 for value in (open_, high, low, close)):
        raise BistOfficialDailyError(
            f"{symbol}: sıfır/negatif OHLC değeri."
        )
    if volume < 0:
        raise BistOfficialDailyError(
            f"{symbol}: negatif hacim."
        )
    if high < max(open_, low, close):
        raise BistOfficialDailyError(
            f"{symbol}: HIGH OHLC aralığıyla tutarsız."
        )
    if low > min(open_, high, close):
        raise BistOfficialDailyError(
            f"{symbol}: LOW OHLC aralığıyla tutarsız."
        )


def _parse_bulletin_zip_internal(
    zip_bytes: bytes,
    islem_tarihi: date,
    *,
    symbols: Iterable[str] | None = None,
    skip_invalid: bool = False,
) -> tuple[
    dict[str, pd.DataFrame],
    tuple[str, ...],
    tuple[str, ...],
]:
    text = _read_csv_from_zip(zip_bytes)
    reader = csv.DictReader(io.StringIO(text), delimiter=";")
    fieldnames = reader.fieldnames or []
    fields = _resolve_required_fields(fieldnames)

    requested_base = (
        {normalize_symbol(symbol) for symbol in symbols}
        if symbols is not None
        else None
    )

    rows_by_symbol: dict[str, tuple[float, float, float, float, float]] = {}
    invalid_symbols: set[str] = set()

    for row in reader:
        if (row.get(fields["date"]) or "").strip() != islem_tarihi.isoformat():
            continue
        if (row.get(fields["group"]) or "").strip() != "EQT":
            continue

        code = (row.get(fields["code"]) or "").strip().upper()
        if not code.endswith(".E"):
            continue

        base_symbol = normalize_symbol(code)
        if requested_base is not None and base_symbol not in requested_base:
            continue

        values = {
            "open": _to_decimal(row.get(fields["open"])),
            "high": _to_decimal(row.get(fields["high"])),
            "low": _to_decimal(row.get(fields["low"])),
            "close": _to_decimal(row.get(fields["close"])),
            "volume": _to_decimal(row.get(fields["volume"])),
        }

        missing = [key for key, value in values.items() if value is None]
        if missing:
            if skip_invalid:
                invalid_symbols.add(base_symbol)
                continue
            raise BistOfficialDailyError(
                f"{base_symbol}: eksik OHLCV alanı: {', '.join(missing)}"
            )

        open_ = values["open"]
        high = values["high"]
        low = values["low"]
        close = values["close"]
        volume = values["volume"]
        assert open_ is not None
        assert high is not None
        assert low is not None
        assert close is not None
        assert volume is not None

        try:
            _validate_ohlcv(base_symbol, open_, high, low, close, volume)
        except BistOfficialDailyError:
            if skip_invalid:
                invalid_symbols.add(base_symbol)
                continue
            raise

        if base_symbol in rows_by_symbol:
            # Tekrarlı gerçek pay satırı, sessizce atlanabilecek bir fiyat
            # problemi değil; yapısal bütünlük hatasıdır.
            raise BistOfficialDailyError(
                f"{base_symbol}: aynı gün için birden fazla EQT .E satırı."
            )

        rows_by_symbol[base_symbol] = (
            float(open_),
            float(high),
            float(low),
            float(close),
            float(volume),
        )

    result: dict[str, pd.DataFrame] = {}
    timestamp = pd.Timestamp(islem_tarihi)

    for base_symbol, values in rows_by_symbol.items():
        df = pd.DataFrame(
            [values],
            columns=list(REQUIRED_PRICE_COLUMNS),
            index=pd.DatetimeIndex([timestamp], name="Date"),
        )
        result[f"{base_symbol}.IS"] = df

    if requested_base is None:
        missing_symbols: tuple[str, ...] = ()
    else:
        found_base = set(rows_by_symbol)
        missing_symbols = tuple(
            sorted(f"{symbol}.IS" for symbol in requested_base - found_base)
        )

    invalid = tuple(sorted(f"{symbol}.IS" for symbol in invalid_symbols))
    return result, missing_symbols, invalid


def parse_bulletin_zip(
    zip_bytes: bytes,
    islem_tarihi: date,
    *,
    symbols: Iterable[str] | None = None,
) -> tuple[dict[str, pd.DataFrame], tuple[str, ...]]:
    # Public parser katı davranışını korur. Birim testleri ve doğrudan çağrılar
    # geçersiz OHLCV'yi hata olarak görmeye devam eder.
    data, missing, _invalid = _parse_bulletin_zip_internal(
        zip_bytes,
        islem_tarihi,
        symbols=symbols,
        skip_invalid=False,
    )
    return data, missing


def _archive_zip(
    zip_bytes: bytes,
    islem_tarihi: date,
    *,
    archive_root: Path,
    source_url: str,
) -> Path:
    target_dir = (
        Path(archive_root)
        / f"{islem_tarihi:%Y}"
        / f"{islem_tarihi:%m}"
    )
    target_dir.mkdir(parents=True, exist_ok=True)

    filename = source_url.rsplit("/", 1)[-1]
    if not filename.lower().endswith(".zip"):
        filename = bulletin_filename(islem_tarihi, "1")

    target = target_dir / filename
    if not target.exists():
        target.write_bytes(zip_bytes)
    return target


def official_daily_data_get(
    symbols: Iterable[str] | None,
    islem_tarihi: date,
    *,
    archive_root: Path | str | None = None,
    fetcher: Callable[[str], bytes] | None = None,
    suffix_candidates: Iterable[str] = DEFAULT_SUFFIX_CANDIDATES,
    skip_invalid: bool = False,
) -> OfficialDailyBatchResult:
    requested = (
        None
        if symbols is None
        else tuple(yahoo_style_symbol(symbol) for symbol in symbols)
    )

    source_url, zip_bytes = download_bulletin_zip(
        islem_tarihi,
        fetcher=fetcher,
        suffix_candidates=suffix_candidates,
    )

    data, missing, invalid = _parse_bulletin_zip_internal(
        zip_bytes,
        islem_tarihi,
        symbols=requested,
        skip_invalid=skip_invalid,
    )

    archive_file = None
    if archive_root is not None:
        archive_file = _archive_zip(
            zip_bytes,
            islem_tarihi,
            archive_root=Path(archive_root),
            source_url=source_url,
        )

    return OfficialDailyBatchResult(
        islem_tarihi=islem_tarihi,
        kaynak_url=source_url,
        veriler=data,
        bulunamayan_semboller=missing,
        arsiv_dosyasi=archive_file,
        gecersiz_semboller=invalid,
    )


__all__ = [
    "BIST_BASE_URL",
    "DEFAULT_SUFFIX_CANDIDATES",
    "BistOfficialDailyError",
    "OfficialDailyBatchResult",
    "bulletin_filename",
    "bulletin_url",
    "download_bulletin_zip",
    "normalize_symbol",
    "official_daily_data_get",
    "parse_bulletin_zip",
    "yahoo_style_symbol",
]

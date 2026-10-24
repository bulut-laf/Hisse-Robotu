from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime
from hashlib import sha256
import csv
import io
import json
import math
from pathlib import Path
from typing import Iterable


GERCEK_HESAP = "Gerçek"
DENEME_HESABI = "Deneme"
HESAP_TURLERI = (GERCEK_HESAP, DENEME_HESABI)
CSV_ALANLARI = (
    "Hesap_Turu",
    "Sembol",
    "Giris_Tarihi",
    "Cikis_Tarihi",
    "Giris_Fiyati",
    "Cikis_Fiyati",
    "Lot",
    "Sermaye",
    "Stop",
    "Hedef",
    "Masraf",
    "Sinyal_Sinifi",
    "Gec_Giris",
    "Kaybedene_Ekleme",
    "Asiri_Yukselmis_Giris",
    "Notlar",
)


class TradeJournalError(Exception):
    """İşlem günlüğü okunamadığında veya yazılamadığında kullanılır."""


@dataclass(frozen=True)
class TradeRecord:
    """Tamamlanmış bir uzun işlemin analiz edilebilir günlüğü."""

    account_type: str
    symbol: str
    entry_date: date
    exit_date: date
    entry_price: float
    exit_price: float
    quantity: int
    capital_at_entry: float
    stop_loss: float | None = None
    target_price: float | None = None
    fees: float = 0.0
    signal_class: str = ""
    late_entry: bool = False
    averaging_down: bool = False
    overextended_entry: bool = False
    notes: str = ""
    record_id: str = ""
    created_at: str = ""

    def __post_init__(self) -> None:
        if self.account_type not in HESAP_TURLERI:
            raise ValueError(f"Geçersiz hesap türü: {self.account_type}")
        symbol = self.symbol.strip().upper().removeprefix("﻿")
        if not symbol:
            raise ValueError("Hisse sembolü boş olamaz.")
        if not symbol.endswith(".IS"):
            symbol += ".IS"
        object.__setattr__(self, "symbol", symbol)

        if self.exit_date < self.entry_date:
            raise ValueError("Çıkış tarihi giriş tarihinden önce olamaz.")
        for ad, deger in (
            ("Giriş fiyatı", self.entry_price),
            ("Çıkış fiyatı", self.exit_price),
            ("Sermaye", self.capital_at_entry),
        ):
            if not math.isfinite(deger) or deger <= 0:
                raise ValueError(f"{ad} sıfırdan büyük olmalıdır.")
        if self.quantity < 1:
            raise ValueError("Lot sayısı en az 1 olmalıdır.")
        if not math.isfinite(self.fees) or self.fees < 0:
            raise ValueError("Masraf negatif olamaz.")
        for ad, deger in (("Stop", self.stop_loss), ("Hedef", self.target_price)):
            if deger is not None and (not math.isfinite(deger) or deger <= 0):
                raise ValueError(f"{ad} fiyatı sıfırdan büyük olmalıdır.")

        created = self.created_at or datetime.now().isoformat(timespec="seconds")
        object.__setattr__(self, "created_at", created)
        if not self.record_id:
            raw = "|".join(
                (
                    self.account_type,
                    symbol,
                    self.entry_date.isoformat(),
                    self.exit_date.isoformat(),
                    f"{self.entry_price:.8f}",
                    f"{self.exit_price:.8f}",
                    str(self.quantity),
                    f"{self.capital_at_entry:.8f}",
                    "" if self.stop_loss is None else f"{self.stop_loss:.8f}",
                    "" if self.target_price is None else f"{self.target_price:.8f}",
                    f"{self.fees:.8f}",
                    self.signal_class.strip(),
                    str(self.late_entry),
                    str(self.averaging_down),
                    str(self.overextended_entry),
                    self.notes.strip(),
                )
            )
            object.__setattr__(self, "record_id", sha256(raw.encode("utf-8")).hexdigest()[:12])

    @property
    def position_amount(self) -> float:
        return self.entry_price * self.quantity

    @property
    def position_pct(self) -> float:
        return self.position_amount / self.capital_at_entry * 100.0

    @property
    def gross_pnl(self) -> float:
        return (self.exit_price - self.entry_price) * self.quantity

    @property
    def net_pnl(self) -> float:
        return self.gross_pnl - self.fees

    @property
    def return_pct(self) -> float:
        return self.net_pnl / self.position_amount * 100.0

    @property
    def planned_risk_amount(self) -> float | None:
        if self.stop_loss is None or self.stop_loss >= self.entry_price:
            return None
        return (self.entry_price - self.stop_loss) * self.quantity

    @property
    def planned_risk_pct(self) -> float | None:
        if self.planned_risk_amount is None:
            return None
        return self.planned_risk_amount / self.capital_at_entry * 100.0

    @property
    def planned_reward_risk(self) -> float | None:
        if (
            self.stop_loss is None
            or self.target_price is None
            or self.stop_loss >= self.entry_price
            or self.target_price <= self.entry_price
        ):
            return None
        return (self.target_price - self.entry_price) / (self.entry_price - self.stop_loss)

    @property
    def realized_r(self) -> float | None:
        if self.planned_risk_amount is None or self.planned_risk_amount <= 0:
            return None
        return self.net_pnl / self.planned_risk_amount

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["entry_date"] = self.entry_date.isoformat()
        data["exit_date"] = self.exit_date.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "TradeRecord":
        values = dict(data)
        values["entry_date"] = _date_value(values.get("entry_date"), "Giriş tarihi")
        values["exit_date"] = _date_value(values.get("exit_date"), "Çıkış tarihi")
        return cls(**values)  # type: ignore[arg-type]


class TradeJournalStore:
    """İşlem günlüğünü kullanıcı profilindeki tek JSON dosyasında saklar."""

    def __init__(self, file_path: str | Path | None = None) -> None:
        self.file_path = (
            Path(file_path).expanduser()
            if file_path is not None
            else default_trade_journal_file()
        )

    def list_records(self) -> tuple[TradeRecord, ...]:
        if not self.file_path.exists():
            return ()
        try:
            raw = json.loads(self.file_path.read_text(encoding="utf-8-sig"))
            if not isinstance(raw, list):
                raise TradeJournalError("İşlem günlüğü liste biçiminde değil.")
            records = tuple(TradeRecord.from_dict(item) for item in raw)
            return tuple(sorted(records, key=lambda x: (x.exit_date, x.created_at, x.record_id)))
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:
            if isinstance(error, TradeJournalError):
                raise
            raise TradeJournalError(f"İşlem günlüğü okunamadı: {error}") from error

    def save(self, record: TradeRecord) -> TradeRecord:
        records = list(self.list_records())
        records = [item for item in records if item.record_id != record.record_id]
        records.append(record)
        self._write(records)
        return record

    def save_many(self, records: Iterable[TradeRecord]) -> int:
        existing = {item.record_id: item for item in self.list_records()}
        count = 0
        for record in records:
            existing[record.record_id] = record
            count += 1
        self._write(existing.values())
        return count

    def delete(self, record_id: str) -> bool:
        records = list(self.list_records())
        filtered = [item for item in records if item.record_id != record_id]
        if len(filtered) == len(records):
            return False
        self._write(filtered)
        return True

    def _write(self, records: Iterable[TradeRecord]) -> None:
        try:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            ordered = sorted(records, key=lambda x: (x.exit_date, x.created_at, x.record_id))
            temporary = self.file_path.with_suffix(self.file_path.suffix + ".tmp")
            temporary.write_text(
                json.dumps([item.to_dict() for item in ordered], ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            temporary.replace(self.file_path)
        except OSError as error:
            raise TradeJournalError(f"İşlem günlüğü yazılamadı: {error}") from error


def default_trade_journal_file() -> Path:
    return Path.home() / ".hisse_robotu" / "islem_gunlugu" / "islemler.json"


def records_to_csv_bytes(records: Iterable[TradeRecord]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=CSV_ALANLARI, delimiter=";")
    writer.writeheader()
    for item in records:
        writer.writerow(
            {
                "Hesap_Turu": item.account_type,
                "Sembol": item.symbol.removesuffix(".IS"),
                "Giris_Tarihi": item.entry_date.isoformat(),
                "Cikis_Tarihi": item.exit_date.isoformat(),
                "Giris_Fiyati": _format_float(item.entry_price),
                "Cikis_Fiyati": _format_float(item.exit_price),
                "Lot": item.quantity,
                "Sermaye": _format_float(item.capital_at_entry),
                "Stop": "" if item.stop_loss is None else _format_float(item.stop_loss),
                "Hedef": "" if item.target_price is None else _format_float(item.target_price),
                "Masraf": _format_float(item.fees),
                "Sinyal_Sinifi": item.signal_class,
                "Gec_Giris": _bool_text(item.late_entry),
                "Kaybedene_Ekleme": _bool_text(item.averaging_down),
                "Asiri_Yukselmis_Giris": _bool_text(item.overextended_entry),
                "Notlar": item.notes,
            }
        )
    return ("\ufeff" + output.getvalue()).encode("utf-8")


def records_from_csv_bytes(content: bytes) -> tuple[TradeRecord, ...]:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise TradeJournalError("CSV dosyası UTF-8 biçiminde olmalıdır.") from error

    try:
        sample = text[:4096]
        try:
            delimiter = csv.Sniffer().sniff(sample, delimiters=";,\t").delimiter
        except csv.Error:
            delimiter = ";"
        reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
        if reader.fieldnames is None:
            raise TradeJournalError("CSV başlık satırı bulunamadı.")
        normalized = {_normalize_header(field): field for field in reader.fieldnames}
        required = {
            "hesapturu",
            "sembol",
            "giristarihi",
            "cikistarihi",
            "girisfiyati",
            "cikisfiyati",
            "lot",
            "sermaye",
        }
        missing = required - set(normalized)
        if missing:
            raise TradeJournalError("CSV zorunlu alanları eksik: " + ", ".join(sorted(missing)))

        records: list[TradeRecord] = []
        for row_number, row in enumerate(reader, start=2):
            try:
                value = lambda key: row.get(normalized.get(key, ""), "")  # noqa: E731
                records.append(
                    TradeRecord(
                        account_type=(value("hesapturu") or GERCEK_HESAP).strip(),
                        symbol=value("sembol"),
                        entry_date=_date_value(value("giristarihi"), "Giriş tarihi"),
                        exit_date=_date_value(value("cikistarihi"), "Çıkış tarihi"),
                        entry_price=_float_value(value("girisfiyati"), "Giriş fiyatı"),
                        exit_price=_float_value(value("cikisfiyati"), "Çıkış fiyatı"),
                        quantity=int(_float_value(value("lot"), "Lot")),
                        capital_at_entry=_float_value(value("sermaye"), "Sermaye"),
                        stop_loss=_optional_float(value("stop"), "Stop"),
                        target_price=_optional_float(value("hedef"), "Hedef"),
                        fees=_optional_float(value("masraf"), "Masraf") or 0.0,
                        signal_class=value("sinyalsinifi").strip(),
                        late_entry=_bool_value(value("gecgiris")),
                        averaging_down=_bool_value(value("kaybedeneekleme")),
                        overextended_entry=_bool_value(value("asiriyukselmisgiris")),
                        notes=value("notlar").strip(),
                    )
                )
            except (ValueError, TypeError) as error:
                raise TradeJournalError(f"CSV {row_number}. satır hatası: {error}") from error
        return tuple(records)
    except csv.Error as error:
        raise TradeJournalError(f"CSV okunamadı: {error}") from error


def csv_template_bytes() -> bytes:
    sample = TradeRecord(
        account_type=DENEME_HESABI,
        symbol="THYAO",
        entry_date=date(2026, 7, 1),
        exit_date=date(2026, 7, 10),
        entry_price=300.0,
        exit_price=306.0,
        quantity=10,
        capital_at_entry=100_000.0,
        stop_loss=294.0,
        target_price=312.0,
        fees=6.0,
        signal_class="E3",
        notes="Örnek satır; içe aktarmadan önce değiştirin.",
    )
    return records_to_csv_bytes((sample,))


def _normalize_header(value: str) -> str:
    table = str.maketrans({
        "Ç": "C", "Ğ": "G", "İ": "I", "Ö": "O", "Ş": "S", "Ü": "U",
        "ç": "c", "ğ": "g", "ı": "i", "ö": "o", "ş": "s", "ü": "u",
        "_": "", "-": "", " ": "",
    })
    return value.strip().translate(table).lower()


def _date_value(value: object, field: str) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{field} boş olamaz.")
    for pattern in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(text, pattern).date()
        except ValueError:
            continue
    raise ValueError(f"{field} geçersiz: {text}")


def _float_value(value: object, field: str) -> float:
    text = str(value or "").strip().replace(" ", "")
    if not text:
        raise ValueError(f"{field} boş olamaz.")
    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        text = text.replace(",", ".")
    try:
        result = float(text)
    except ValueError as error:
        raise ValueError(f"{field} sayı olmalıdır: {value}") from error
    if not math.isfinite(result):
        raise ValueError(f"{field} sonlu olmalıdır.")
    return result


def _optional_float(value: object, field: str) -> float | None:
    if value is None or not str(value).strip():
        return None
    return _float_value(value, field)


def _bool_value(value: object) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "evet", "e", "yes", "x"}


def _bool_text(value: bool) -> str:
    return "Evet" if value else "Hayır"


def _format_float(value: float) -> str:
    return f"{value:.4f}".rstrip("0").rstrip(".")

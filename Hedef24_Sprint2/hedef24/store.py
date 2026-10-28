from __future__ import annotations

import json
import os
import tempfile
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


class PortfolioValidationError(ValueError):
    """Invalid portfolio operation or data."""


class Hedef24Store:
    """Small JSON-backed portfolio store. Does not place trades or fetch prices."""

    SCHEMA_VERSION = 1
    PORTFOLIO_NAME = "Hedef 24"

    def __init__(self, path: str | Path):
        self.path = Path(path)

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _decimal(value: Any, field: str, *, allow_zero: bool = False) -> str:
        try:
            number = Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError):
            raise PortfolioValidationError(f"{field}: geçerli bir sayı olmalı.")
        if not number.is_finite() or number < 0 or (number == 0 and not allow_zero):
            raise PortfolioValidationError(f"{field}: pozitif bir sayı olmalı.")
        return format(number, "f")

    @staticmethod
    def _validate_isin(isin: str | None) -> str | None:
        if isin is None or not str(isin).strip():
            return None
        value = str(isin).strip().upper()
        if len(value) != 12 or not value.isalnum():
            raise PortfolioValidationError("ISIN 12 karakterli harf/rakam kodu olmalı.")
        return value

    @staticmethod
    def _validate_date(value: str, field: str) -> str:
        try:
            parsed = date.fromisoformat(str(value))
        except (ValueError, TypeError):
            raise PortfolioValidationError(f"{field}: YYYY-MM-DD biçiminde tarih girin.")
        return parsed.isoformat()

    def _empty(self) -> dict[str, Any]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "portfolio_name": self.PORTFOLIO_NAME,
            "execution_authority": "NONE",
            "updated_at": self._now(),
            "records": [],
            "nav_history": [],
        }

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return self._empty()
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise PortfolioValidationError(f"Portföy dosyası okunamadı: {exc}") from exc
        if not isinstance(data, dict) or not isinstance(data.get("records"), list):
            raise PortfolioValidationError("Portföy JSON şeması geçersiz.")
        data.setdefault("nav_history", [])
        return data

    def _write(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data["updated_at"] = self._now()
        # Atomic replace: do not leave a half-written JSON file.
        fd, temp_name = tempfile.mkstemp(prefix=self.path.name + ".", suffix=".tmp", dir=self.path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                json.dump(data, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, self.path)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)

    def import_seed(self, seed_path: str | Path, *, replace: bool = False) -> int:
        """Import the seed only when destination is empty unless replace=True."""
        seed_path = Path(seed_path)
        try:
            seed = json.loads(seed_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise PortfolioValidationError(f"Başlangıç dosyası okunamadı: {exc}") from exc
        records = seed.get("records") if isinstance(seed, dict) else None
        if not isinstance(records, list) or len(records) != 24:
            raise PortfolioValidationError("Başlangıç dosyası tam 24 kayıt içermeli.")
        current = self.load()
        if current["records"] and not replace:
            raise PortfolioValidationError("Portföy boş değil; içe aktarma için replace=True gerekir.")
        # Preserve reference fields and mark every record as a portfolio record.
        copied = json.loads(json.dumps(records, ensure_ascii=False))
        for index, record in enumerate(copied, start=1):
            record["slot"] = index
            record.setdefault("nav_history_count", 0)
        data = {
            "schema_version": self.SCHEMA_VERSION,
            "portfolio_name": self.PORTFOLIO_NAME,
            "execution_authority": "NONE",
            "updated_at": self._now(),
            "records": copied,
            "nav_history": current.get("nav_history", []) if not replace else [],
        }
        self._write(data)
        return len(copied)

    def list_records(self) -> list[dict[str, Any]]:
        return sorted(self.load()["records"], key=lambda item: item.get("slot", 9999))

    def _find(self, data: dict[str, Any], slot: int) -> dict[str, Any]:
        for record in data["records"]:
            if record.get("slot") == slot:
                return record
        raise PortfolioValidationError(f"{slot}. portföy kaydı bulunamadı.")

    def add_fund(self, fund_name: str = "", isin: str | None = None, block: str | None = None,
                 currency: str | None = None) -> dict[str, Any]:
        data = self.load()
        if len(data["records"]) >= 24:
            raise PortfolioValidationError("Hedef 24 dolu; önce bir kayıt çıkarın.")
        normalized_isin = self._validate_isin(isin)
        if normalized_isin and any(r.get("isin") == normalized_isin for r in data["records"]):
            raise PortfolioValidationError("Bu ISIN portföyde zaten var.")
        used = {r.get("slot") for r in data["records"]}
        slot = next(i for i in range(1, 25) if i not in used)
        record = {
            "slot": slot, "fund_name": str(fund_name).strip(), "isin": normalized_isin,
            "block": str(block).strip() if block else None,
            "currency": str(currency).strip().upper() if currency else None,
            "purchase_date": None, "purchase_nav": None, "units": None,
            "latest_nav": None, "latest_nav_date": None, "pnl_percent_reference": None,
            "action_reference": None, "signal": None, "settlement_terms": None,
            "data_status": "IDENTITY_UNVERIFIED" if not normalized_isin else "IDENTITY_PENDING_VERIFICATION",
            "notes": "Kullanıcı tarafından eklenen kayıt; resmî fon kimliği doğrulanmalı.",
        }
        data["records"].append(record)
        self._write(data)
        return record

    def update_fund(self, slot: int, **fields: Any) -> dict[str, Any]:
        allowed = {"fund_name", "isin", "block", "currency", "purchase_date", "purchase_nav", "units", "notes"}
        unknown = set(fields) - allowed
        if unknown:
            raise PortfolioValidationError(f"Desteklenmeyen alan(lar): {', '.join(sorted(unknown))}")
        data = self.load()
        record = self._find(data, slot)
        if "isin" in fields:
            normalized = self._validate_isin(fields["isin"])
            if normalized and any(r.get("slot") != slot and r.get("isin") == normalized for r in data["records"]):
                raise PortfolioValidationError("Bu ISIN başka bir portföy kaydında zaten var.")
            fields["isin"] = normalized
        if "purchase_date" in fields and fields["purchase_date"] not in (None, ""):
            fields["purchase_date"] = self._validate_date(fields["purchase_date"], "Alış tarihi")
        if "purchase_nav" in fields and fields["purchase_nav"] not in (None, ""):
            fields["purchase_nav"] = self._decimal(fields["purchase_nav"], "Alış NAV")
        if "units" in fields and fields["units"] not in (None, ""):
            fields["units"] = self._decimal(fields["units"], "Adet")
        for key, value in fields.items():
            if key in {"fund_name", "block", "currency", "notes"} and value is not None:
                value = str(value).strip()
                if key == "currency":
                    value = value.upper()
            if key in {"purchase_nav", "units"} and value in ("", None):
                value = None
            record[key] = value
        if record.get("isin"):
            record["data_status"] = "IDENTITY_PENDING_VERIFICATION"
        else:
            record["data_status"] = "IDENTITY_UNVERIFIED"
        self._write(data)
        return record

    def remove_fund(self, slot: int, *, confirm: bool = False) -> dict[str, Any]:
        if not confirm:
            raise PortfolioValidationError("Fon çıkarmak için confirm=True ile açık onay gerekli.")
        data = self.load()
        record = self._find(data, slot)
        data["records"] = [r for r in data["records"] if r.get("slot") != slot]
        self._write(data)
        return record

    def record_nav(self, slot: int, nav_date: str, nav: Any, currency: str | None = None,
                   source: str = "") -> dict[str, Any]:
        parsed_date = self._validate_date(nav_date, "NAV tarihi")
        parsed_nav = self._decimal(nav, "NAV")
        data = self.load()
        record = self._find(data, slot)
        entry = {
            "slot": slot, "isin": record.get("isin"), "fund_name": record.get("fund_name", ""),
            "date": parsed_date, "nav": parsed_nav,
            "currency": (currency or record.get("currency") or "").upper() or None,
            "source": str(source).strip() or None, "recorded_at": self._now(),
        }
        # Unique by slot/date; update that day's value instead of duplicating it.
        existing = next((i for i, row in enumerate(data["nav_history"])
                         if row.get("slot") == slot and row.get("date") == parsed_date), None)
        if existing is None:
            data["nav_history"].append(entry)
        else:
            data["nav_history"][existing] = entry
        record["latest_nav"] = parsed_nav
        record["latest_nav_date"] = parsed_date
        if entry["currency"]:
            record["currency"] = entry["currency"]
        record["nav_history_count"] = sum(1 for row in data["nav_history"] if row.get("slot") == slot)
        self._write(data)
        return entry

    def performance(self, slot: int) -> dict[str, Any]:
        record = self._find(self.load(), slot)
        if record.get("purchase_nav") in (None, "") or record.get("latest_nav") in (None, ""):
            return {"available": False, "reason": "Alış NAV veya güncel NAV eksik."}
        purchase = Decimal(str(record["purchase_nav"]))
        latest = Decimal(str(record["latest_nav"]))
        if purchase <= 0:
            return {"available": False, "reason": "Alış NAV pozitif olmalı."}
        return {
            "available": True,
            "pnl_percent": str(((latest - purchase) / purchase * Decimal("100")).quantize(Decimal("0.01"))),
            "pnl_per_unit": str((latest - purchase).quantize(Decimal("0.0001"))),
            "currency": record.get("currency"),
            "purchase_date": record.get("purchase_date"),
            "latest_nav_date": record.get("latest_nav_date"),
        }

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation


def normalize_fund_code(value: object) -> str:
    code = re.sub(r"\s+", "", str(value or "")).upper()
    if not code:
        raise ValueError("Fon kodu boş olamaz.")
    return code


def normalize_text(value: object) -> str:
    return " ".join(str(value or "").split())


def parse_decimal_tr(value: object, *, percent: bool = False) -> Decimal | None:
    """Gerçek sıfırı korur; boş/unsupported değeri None yapar."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    if isinstance(value, bool):
        raise ValueError("Boolean numeric değer değildir.")
    raw = str(value).strip().replace("%", "").replace("\u00a0", "").replace(" ", "")
    if raw in {"-", "N/A", "n/a", "null", "None"}:
        return None
    if "," in raw:
        raw = raw.replace(".", "").replace(",", ".")
    elif raw.count(".") == 1 and len(raw.rsplit(".", 1)[1]) == 3:
        # Türkçe kaynaklarda tek nokta ve üç hane binlik ayraçtır.
        raw = raw.replace(".", "")
    try:
        parsed = Decimal(raw)
    except InvalidOperation as exc:
        raise ValueError(f"Geçersiz sayısal değer: {value}") from exc
    return parsed / Decimal("100") if percent else parsed


def validate_allocation(values: dict[str, Decimal], tolerance: Decimal = Decimal("0.5")) -> None:
    if values and abs(sum(values.values(), Decimal("0")) - Decimal("100")) > tolerance:
        raise ValueError("Portföy dağılımı 100 toplam toleransını aşıyor.")

from __future__ import annotations

import re
from datetime import date

_NUMERIC_PATTERNS = (
    re.compile(r"(?<!\d)(20\d{2})[./-](0?[1-9]|1[0-2])[./-](0?[1-9]|[12]\d|3[01])(?!\d)"),
    re.compile(r"(?<!\d)(0?[1-9]|[12]\d|3[01])[./-](0?[1-9]|1[0-2])[./-](20\d{2})(?!\d)"),
)

_MONTHS = {
    "oca": 1, "ocak": 1, "şub": 2, "sub": 2, "şubat": 2, "subat": 2,
    "mar": 3, "mart": 3, "nis": 4, "nisan": 4, "may": 5, "mayıs": 5, "mayis": 5,
    "haz": 6, "haziran": 6, "tem": 7, "temmuz": 7, "ağu": 8, "agu": 8,
    "ağustos": 8, "agustos": 8, "eyl": 9, "eylül": 9, "eylul": 9,
    "eki": 10, "ekim": 10, "kas": 11, "kasım": 11, "kasim": 11,
    "ara": 12, "aralık": 12, "aralik": 12,
}

_TURKISH = re.compile(
    r"(?<!\d)(0?[1-9]|[12]\d|3[01])\s+"
    r"(oca(?:k)?|şub(?:at)?|sub(?:at)?|mar(?:t)?|nis(?:an)?|may(?:ıs|is)?|"
    r"haz(?:iran)?|tem(?:muz)?|ağu(?:stos)?|agu(?:stos)?|eyl(?:ül|ul)?|"
    r"eki(?:m)?|kas(?:ım|im)?|ara(?:lık|lik)?)\s+(20\d{2})(?!\d)",
    re.IGNORECASE,
)

def _iso(y: int, m: int, d: int) -> str | None:
    try:
        return date(y, m, d).isoformat()
    except ValueError:
        return None

def detect_report_date(text: str, *, scan_chars: int = 1800) -> str | None:
    sample = str(text or "")[:scan_chars]
    for pattern in _NUMERIC_PATTERNS:
        match = pattern.search(sample)
        if match:
            a, b, c = match.groups()
            result = _iso(int(a), int(b), int(c)) if len(a) == 4 else _iso(int(c), int(b), int(a))
            if result:
                return result

    match = _TURKISH.search(sample)
    if match:
        day = int(match.group(1))
        month = _MONTHS.get(match.group(2).casefold())
        year = int(match.group(3))
        if month:
            return _iso(year, month, day)

    return None

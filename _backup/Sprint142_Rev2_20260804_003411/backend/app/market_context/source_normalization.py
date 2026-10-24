from __future__ import annotations

import re

_SOURCE_ALIASES = {
    "icbc": "ICBC",
    "icbc yatirim": "ICBC",
    "icbc yatırım": "ICBC",
    "yf": "Yatırım Finansman",
    "yatirim finansman": "Yatırım Finansman",
    "yatırım finansman": "Yatırım Finansman",
    "yatirim finansman menkul degerler": "Yatırım Finansman",
    "yatırım finansman menkul değerler": "Yatırım Finansman",
    "kap": "KAP",
    "kap haberleri": "KAP",
}

def normalize_source_name(value: str) -> str:
    cleaned = re.sub(r"\s+", " ", str(value or "").strip())
    if not cleaned:
        return ""
    return _SOURCE_ALIASES.get(cleaned.casefold(), cleaned)

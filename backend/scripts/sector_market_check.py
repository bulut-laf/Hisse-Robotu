from __future__ import annotations

import pandas as pd

from backend.app.sector_analysis.sector_market_strength import (
    SectorMarketStrengthError,
    build_sector_market_map,
    sector_market_rows,
)


def main() -> int:
    try:
        result = build_sector_market_map()
    except SectorMarketStrengthError as exc:
        print(f"SEKTÖR ANALİZİ BAŞARISIZ: {exc}")
        return 1

    print()
    print(
        f"Sektörel piyasa gücü — XU100 karşılaştırması — "
        f"{result.analysis_date.isoformat()}"
    )
    print()

    table = pd.DataFrame(sector_market_rows(result))
    if table.empty:
        print("Güncel sektör sonucu bulunamadı.")
        return 1

    print(table.to_string(index=False))

    if result.errors:
        print()
        print("Kullanılamayan sektör endeksleri:")
        for error in result.errors:
            print(f"- {error}")

    print()
    print(
        "Not: Bu çıktı sektör bağlamı ve göreceli güç üretir; "
        "alım/satım sinyali veya aday hard filtresi değildir."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse

import pandas as pd

from backend.app.sector_analysis.sector_member_strength import (
    SectorMemberStrengthError,
    build_sector_member_strength_map,
    sector_member_strength_rows,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Resmî BIST üyeliklerinden sektör göreceli güç kontrolü."
        )
    )
    parser.add_argument(
        "--universe",
        default="BIST 100",
        choices=("BIST 30", "BIST 50", "BIST 100", "BIST 500", "BIST Tüm"),
        help="Sektör üyelerinin kesiştirileceği referans tarama evreni.",
    )
    args = parser.parse_args()

    try:
        result = build_sector_member_strength_map(
            reference_universe=args.universe,
        )
    except SectorMemberStrengthError as exc:
        print(f"SEKTÖR ÜYE ANALİZİ BAŞARISIZ: {exc}")
        return 1

    print()
    print(
        f"Sektör üye gücü — {result.reference_universe} — "
        f"XU100 karşılaştırması — {result.analysis_date.isoformat()}"
    )
    print()

    table = pd.DataFrame(sector_member_strength_rows(result))
    if table.empty:
        print("Güncel sektör sonucu bulunamadı.")
        return 1

    columns = [
        "Sıra",
        "Sektör",
        "Endeks",
        "Skor",
        "Durum",
        "Üye",
        "Güncel üye",
        "Kapsama (%)",
        "1G medyan (%)",
        "5G medyan (%)",
        "20G medyan (%)",
        "RS 1G",
        "RS 5G",
        "RS 20G",
        "Bileşik RS",
        "1G pozitif (%)",
        "EMA21 üstü (%)",
        "Momentum + (%)",
        "Medyan hacim",
    ]
    print(table[columns].to_string(index=False))

    if result.errors:
        print()
        print("Kullanılamayan / temsil gücü yetersiz sektörler:")
        for error in result.errors:
            print(f"- {error}")

    print()
    print(
        "Not: Bu katman sektör bağlamı ve göreceli güç üretir; "
        "adayları elemez ve alım/satım sinyali üretmez."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

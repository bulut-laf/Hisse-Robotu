from datetime import datetime
from zoneinfo import ZoneInfo

from backend.app.operations.scheduled_intraday_batch import fetch_scheduled_intraday_batch

ISTANBUL = ZoneInfo("Europe/Istanbul")

# lk canlı doğrulama için temsilî BIST grubu
SYMBOLS = [
    "THYAO.IS",
    "AKBNK.IS",
    "YKBNK.IS",
    "ASELS.IS",
    "BIMAS.IS",
    "TUPRS.IS",
    "EREGL.IS",
    "SISE.IS",
    "KCHOL.IS",
    "GARAN.IS",
]

def main():
    now = datetime.now(ISTANBUL)

    print("=" * 72)
    print("HISSE ROBOTU - 5M INTRADAY LIVE SMOKE TEST")
    print("=" * 72)
    print(f"Test zamanı : {now:%Y-%m-%d %H:%M:%S}")
    print(f"Sembol sayısı: {len(SYMBOLS)}")
    print()

    result = fetch_scheduled_intraday_batch(
        SYMBOLS,
        now=now,
        chunk_size=10,
    )

    snapshots = result.snapshots
    failures = result.failures

    current = [
        s for s in snapshots.values()
        if not s.locked
    ]

    preview = [
        s for s in snapshots.values()
        if s.preview_only
    ]

    locked = [
        s for s in snapshots.values()
        if s.locked
    ]

    delays = [
        s.measured_delay_minutes
        for s in snapshots.values()
    ]

    print(f"BIST test evreni        : {result.requested_count}")
    print(f"5m veri alınabilen      : {len(snapshots)}")
    print(f"Güncel/ön izleme        : {len(current)}")
    print(f"n izleme                : {len(preview)}")
    print(f"Kilitli                  : {len(locked)}")
    print(f"Veri alınamayan          : {len(failures)}")

    if delays:
        print(f"Ortalama gecikme        : {sum(delays) / len(delays):.2f} dk")
        print(f"Maksimum gecikme        : {max(delays):.2f} dk")

    if snapshots:
        latest = max(
            snapshots.values(),
            key=lambda s: s.exchange_time,
        )
        print(f"En son snapshot          : {latest.exchange_time:%H:%M:%S}")

    print()
    print("-" * 72)
    print("SNAPSHOTLAR")
    print("-" * 72)

    for symbol in SYMBOLS:
        snapshot = snapshots.get(symbol)

        if snapshot is None:
            print(f"{symbol:12} | VER YOK")
            continue

        print(
            f"{symbol:12} | "
            f"{snapshot.status:24} | "
            f"bar={snapshot.exchange_time:%H:%M:%S} | "
            f"delay={snapshot.measured_delay_minutes:5.1f} dk | "
            f"price={snapshot.last_price:10.2f} | "
            f"vol={snapshot.latest_bar_volume:,.0f} | "
            f"missing={snapshot.missing_bar_count}"
        )

    if failures:
        print()
        print("-" * 72)
        print("HATALAR")
        print("-" * 72)

        for failure in failures:
            print(f"{failure.symbol:12} | {failure.error}")

    print()
    print("=" * 72)

    coverage = (
        len(snapshots) / result.requested_count * 100
        if result.requested_count
        else 0
    )

    print(f"5m COVERAGE              : {coverage:.1f}%")
    print("=" * 72)


if __name__ == "__main__":
    main()



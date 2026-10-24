from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(r"D:\Projects\Hisse-Robotu")
sys.path.insert(0, str(ROOT))

from backend.app.funds.tefas_adapter import (
    fetch_tefas_fund_detail_rows,
    fetch_tefas_fund_history_rows,
    fetch_tefas_universe_rows,
)


print("LIVE_A=UNIVERSE_START", flush=True)

universe = fetch_tefas_universe_rows(timeout_seconds=10)

print(f"LIVE_A_ROWS={len(universe)}", flush=True)

if not universe:
    raise RuntimeError("LIVE_UNIVERSE_EMPTY")


codes = []

for row in universe:
    code = str(row.get("fonKodu") or "").strip().upper()

    if code and code not in codes:
        codes.append(code)

    if len(codes) >= 5:
        break


if not codes:
    raise RuntimeError("LIVE_DYNAMIC_FUND_NOT_FOUND")


confirmed = None
last_error = None

for fund_code in codes:
    print(f"CANDIDATE={fund_code}", flush=True)

    try:
        time.sleep(2)

        print("LIVE_B=DETAIL_START", flush=True)

        detail = fetch_tefas_fund_detail_rows(
            fund_code,
            timeout_seconds=10,
        )

        print(f"LIVE_B_ROWS={len(detail)}", flush=True)

        if not detail:
            raise RuntimeError("DETAIL_EMPTY")

        detail_keys = set(detail[0].keys())

        required_detail = {
            "fonKodu",
            "fonUnvan",
            "sonFiyat",
        }

        missing_detail = required_detail - detail_keys

        if missing_detail:
            raise RuntimeError(
                "DETAIL_KEYS_MISSING:"
                + ",".join(sorted(missing_detail))
            )

        time.sleep(2)

        print("LIVE_C=HISTORY_START", flush=True)

        history = fetch_tefas_fund_history_rows(
            fund_code,
            period=1,
            timeout_seconds=10,
        )

        print(f"LIVE_C_ROWS={len(history)}", flush=True)

        if not history:
            raise RuntimeError("HISTORY_EMPTY")

        history_keys = set(history[0].keys())

        required_history = {
            "fonKodu",
            "fonUnvan",
            "tarih",
            "fiyat",
        }

        missing_history = required_history - history_keys

        if missing_history:
            raise RuntimeError(
                "HISTORY_KEYS_MISSING:"
                + ",".join(sorted(missing_history))
            )

        confirmed = fund_code
        break

    except Exception as exc:
        last_error = exc
        print(
            f"CANDIDATE_REJECTED={fund_code}:{type(exc).__name__}:{exc}",
            flush=True,
        )


if confirmed is None:
    raise RuntimeError(
        f"NO_DYNAMIC_CANDIDATE_CONFIRMED:{last_error}"
    )


print(f"DYNAMIC_PROBE_FUND={confirmed}", flush=True)
print("LIVE_UNIVERSE=CONFIRMED", flush=True)
print("LIVE_DETAIL=CONFIRMED", flush=True)
print("LIVE_HISTORY=CONFIRMED", flush=True)
print("HARD_CODED_FUND_CODE=NO", flush=True)
print("LEGACY_BINDHISTORYINFO_CALLED=NO", flush=True)
print("SMOKE_STATUS=SUCCESS", flush=True)

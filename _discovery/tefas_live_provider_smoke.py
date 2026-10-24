from __future__ import annotations

import time

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


candidates = [
    row
    for row in universe
    if row.get("fonKodu")
    and row.get("getiri1a") not in (None, "")
]

if not candidates:
    candidates = [
        row
        for row in universe
        if row.get("fonKodu")
    ]

if not candidates:
    raise RuntimeError("LIVE_DYNAMIC_FUND_NOT_FOUND")


probe = candidates[0]
fund_code = str(probe["fonKodu"]).strip().upper()

print(f"DYNAMIC_PROBE_FUND={fund_code}", flush=True)

time.sleep(2)

print("LIVE_B=DETAIL_START", flush=True)

detail = fetch_tefas_fund_detail_rows(
    fund_code,
    timeout_seconds=10,
)

print(f"LIVE_B_ROWS={len(detail)}", flush=True)

if not detail:
    raise RuntimeError("LIVE_DETAIL_EMPTY")

detail_keys = set(detail[0].keys())

required_detail = {
    "fonKodu",
    "fonUnvan",
    "sonFiyat",
}

missing_detail = required_detail - detail_keys

if missing_detail:
    raise RuntimeError(
        "LIVE_DETAIL_KEYS_MISSING:"
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
    raise RuntimeError("LIVE_HISTORY_EMPTY")

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
        "LIVE_HISTORY_KEYS_MISSING:"
        + ",".join(sorted(missing_history))
    )


print(
    "LIVE_CONTRACT="
    "UNIVERSE+DETAIL+HISTORY_CONFIRMED",
    flush=True,
)

print("HARD_CODED_FUND_CODE=NO", flush=True)
print("LEGACY_ENDPOINT_CALLED=NO", flush=True)
print("SMOKE_STATUS=SUCCESS", flush=True)

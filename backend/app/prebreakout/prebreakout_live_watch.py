from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Iterable, Mapping

from backend.app.prebreakout.prebreakout_models import PreBreakoutResult
from backend.app.prebreakout.prebreakout_threshold_policy import (
    PreBreakoutThresholdPolicy,
)

LIVE_WATCH_SCHEMA_VERSION = 1
LIVE_WATCH_STAGES = frozenset({"E2", "E3", "E4"})
DEFAULT_LIVE_WATCH_PATH = Path("backend/data/prebreakout_live_watch.jsonl")


@dataclass(frozen=True)
class PreBreakoutLiveSignal:
    schema_version: int
    signal_id: str
    symbol: str
    signal_date: str
    recorded_at_utc: str
    stage: str
    stage_label: str
    score: int
    accepted: bool
    close: float
    minimum_momentum_score: int
    threshold_policy_enabled: bool
    threshold_policy_source: str
    features: Mapping[str, float | bool]
    reasons: tuple[str, ...]
    risks: tuple[str, ...]
    payload_sha256: str


def _canonical_payload(payload: Mapping[str, object]) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _payload_hash(payload: Mapping[str, object]) -> str:
    return sha256(_canonical_payload(payload)).hexdigest()


def _signal_id(symbol: str, signal_date: str, stage: str) -> str:
    raw = f"{symbol.upper()}|{signal_date}|{stage.upper()}".encode("utf-8")
    return sha256(raw).hexdigest()[:24]


def canli_sinyal_olustur(
    result: PreBreakoutResult,
    signal_date: date,
    policy: PreBreakoutThresholdPolicy,
    *,
    recorded_at: datetime | None = None,
) -> PreBreakoutLiveSignal | None:
    stage = result.stage.value
    if stage not in LIVE_WATCH_STAGES or result.features is None:
        return None

    features = result.features
    recorded = recorded_at or datetime.now(timezone.utc)
    if recorded.tzinfo is None:
        recorded = recorded.replace(tzinfo=timezone.utc)
    recorded = recorded.astimezone(timezone.utc)

    feature_snapshot: dict[str, float | bool] = {
        "direnc_uzaklik_pct": float(features.direnc_uzaklik_pct),
        "rsi14": float(features.rsi14),
        "rsi_egimi": float(features.rsi_egimi),
        "macd_histogram": float(features.macd_histogram),
        "macd_histogram_egimi": float(features.macd_histogram_egimi),
        "momentum_skoru": float(features.momentum_skoru),
        "hacim_orani_3_10": float(features.hacim_orani_3_10),
        "atr_daralma_orani": float(features.atr_daralma_orani),
        "son_gun_getirisi_pct": float(features.son_gun_getirisi_pct),
        "risk_odul": float(features.risk_odul),
        "late_entry": bool(result.late_entry),
    }
    signal_day = signal_date.isoformat()
    base_payload: dict[str, object] = {
        "schema_version": LIVE_WATCH_SCHEMA_VERSION,
        "signal_id": _signal_id(result.symbol, signal_day, stage),
        "symbol": result.symbol.upper(),
        "signal_date": signal_day,
        "recorded_at_utc": recorded.isoformat().replace("+00:00", "Z"),
        "stage": stage,
        "stage_label": result.stage_label,
        "score": int(result.score),
        "accepted": bool(result.accepted),
        "close": float(features.close),
        "minimum_momentum_score": int(policy.minimum_momentum_score(stage)),
        "threshold_policy_enabled": bool(policy.enabled),
        "threshold_policy_source": policy.source,
        "features": feature_snapshot,
        "reasons": tuple(result.reasons),
        "risks": tuple(result.risks),
    }
    return PreBreakoutLiveSignal(
        **base_payload,
        payload_sha256=_payload_hash(base_payload),
    )


def _record_to_payload(record: PreBreakoutLiveSignal) -> dict[str, object]:
    payload = asdict(record)
    payload["reasons"] = list(record.reasons)
    payload["risks"] = list(record.risks)
    return payload


def canli_sinyalleri_yukle(
    path: str | Path = DEFAULT_LIVE_WATCH_PATH,
) -> tuple[PreBreakoutLiveSignal, ...]:
    target = Path(path)
    if not target.exists():
        return ()

    records: list[PreBreakoutLiveSignal] = []
    for line_number, raw_line in enumerate(target.read_text(encoding="utf-8").splitlines(), 1):
        if not raw_line.strip():
            continue
        try:
            payload = json.loads(raw_line)
            expected_hash = str(payload.pop("payload_sha256"))
        except (json.JSONDecodeError, KeyError, TypeError) as error:
            raise ValueError(f"Geçersiz canlı sinyal kaydı; satır {line_number}.") from error
        if _payload_hash(payload) != expected_hash:
            raise ValueError(f"Canlı sinyal bütünlük kontrolü başarısız; satır {line_number}.")
        payload["payload_sha256"] = expected_hash
        payload["features"] = dict(payload["features"])
        payload["reasons"] = tuple(payload["reasons"])
        payload["risks"] = tuple(payload["risks"])
        records.append(PreBreakoutLiveSignal(**payload))
    return tuple(records)


def canli_sinyalleri_kaydet(
    results: Iterable[PreBreakoutResult],
    signal_date: date,
    policy: PreBreakoutThresholdPolicy,
    *,
    path: str | Path = DEFAULT_LIVE_WATCH_PATH,
    recorded_at: datetime | None = None,
    duplicate_cooldown_days: int = 5,
) -> tuple[PreBreakoutLiveSignal, ...]:
    target = Path(path)
    existing_records = canli_sinyalleri_yukle(target)
    existing_ids = {record.signal_id for record in existing_records}
    new_records: list[PreBreakoutLiveSignal] = []

    for result in results:
        record = canli_sinyal_olustur(
            result,
            signal_date,
            policy,
            recorded_at=recorded_at,
        )
        if record is None or record.signal_id in existing_ids:
            continue
        signal_day = date.fromisoformat(record.signal_date)
        repeated = any(
            previous.symbol.upper() == record.symbol.upper()
            and 0 <= (signal_day - date.fromisoformat(previous.signal_date)).days <= duplicate_cooldown_days
            for previous in existing_records
        )
        if repeated:
            continue
        existing_ids.add(record.signal_id)
        existing_records = (*existing_records, record)
        new_records.append(record)

    if not new_records:
        return ()

    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8", newline="\n") as handle:
        for record in new_records:
            handle.write(
                json.dumps(
                    _record_to_payload(record),
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
            )
            handle.write("\n")
        handle.flush()

    return tuple(new_records)

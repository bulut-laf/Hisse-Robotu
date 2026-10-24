import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("_discovery/erste_hungary")
SOURCE = ROOT / "stale4_comparison_recheck_20261013.json"
OUTPUT = ROOT / "stale4_source_freshness_classification_20261013.json"

data = json.loads(SOURCE.read_text(encoding="utf-8"))

results = []
for row in data.get("results", []):
    nav_date = row.get("nav_date")
    success = row.get("success") is True
    error = row.get("error")

    if error or not success:
        status = "SOURCE_CHECK_ERROR"
    elif not nav_date:
        status = "NAV_DATE_UNAVAILABLE"
    elif nav_date < "2026-10-01":
        status = "STALE_SOURCE_DATA"
    else:
        status = "RECENT_SOURCE_DATA"

    results.append({
        "isin": row.get("isin"),
        "name": row.get("name"),
        "nav_date": nav_date,
        "nav": row.get("nav"),
        "source_check_success": success,
        "source_error": error,
        "freshness_status": status,
        "ranking_eligible_from_freshness_check": status == "RECENT_SOURCE_DATA",
        "note": (
            "Eski kaynak tarihi; güncel performans sıralamasında kullanma."
            if status == "STALE_SOURCE_DATA"
            else "Bu rapor tek başına fonun aktifliğini veya sıralama uygunluğunu kanıtlamaz."
        ),
    })

payload = {
    "artifact_type": "ERSTE_HUNGARY_SOURCE_FRESHNESS_CLASSIFICATION",
    "created_at_utc": datetime.now(timezone.utc).isoformat(),
    "source_artifact": str(SOURCE),
    "freshness_cutoff": "2026-10-01",
    "classification_scope": "DISCOVERY_ONLY",
    "results": results,
    "summary": {
        "total": len(results),
        "stale_source_data": sum(r["freshness_status"] == "STALE_SOURCE_DATA" for r in results),
        "recent_source_data": sum(r["freshness_status"] == "RECENT_SOURCE_DATA" for r in results),
        "source_check_error": sum(r["freshness_status"] == "SOURCE_CHECK_ERROR" for r in results),
        "nav_date_unavailable": sum(r["freshness_status"] == "NAV_DATE_UNAVAILABLE" for r in results),
    },
    "rank_history_write": False,
    "production_decisions_modified": False,
    "catalog_modified": False,
    "trade_authority": "NONE",
    "forced_fill": False,
}

OUTPUT.write_text(
    json.dumps(payload, ensure_ascii=False, indent=2),
    encoding="utf-8",
)

print(json.dumps(payload["summary"], ensure_ascii=False, indent=2))
print(f"OUTPUT: {OUTPUT}")
print("RANK_HISTORY_WRITE: False")
print("PRODUCTION_DECISIONS_MODIFIED: False")
print("CATALOG_MODIFIED: False")
print("TRADE_AUTHORITY: NONE")
print("FORCED_FILL: False")

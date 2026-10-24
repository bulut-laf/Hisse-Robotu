from __future__ import annotations

from pathlib import Path
import json
import sys


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.funds.international.erste_hungary_universe import (
    fetch_live_universe,
)


def main() -> int:
    capture_dir = ROOT / "_discovery" / "erste_hungary"
    capture_dir.mkdir(parents=True, exist_ok=True)

    result = fetch_live_universe(
        timeout_seconds=40.0,
        request_delay_seconds=0.08,
    )

    payload = {
        "total_count": result.total_count,
        "discovered_isin_count": len(result.isins),
        "detail_url_count": len(result.detail_urls),
        "coverage_ratio": result.coverage_ratio,
        "pages_fetched": result.pages_fetched,
        "page_size_observed": result.page_size_observed,
        "ret_min": result.ret_min,
        "ret_max": result.ret_max,
        "list_html_length": result.list_html_length,
        "app_base_path": result.app_base_path,
        "list_endpoint": result.list_endpoint,
        "count_endpoint": result.count_endpoint,
        "isins": list(result.isins),
        "detail_urls": list(result.detail_urls),
    }

    (capture_dir / "universe_paginated_latest.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"APP_BASE_PATH={result.app_base_path}")
    print(f"REMOTE_TOTAL_COUNT={result.total_count}")
    print(f"DISCOVERED_ISIN_COUNT={len(result.isins)}")
    print(f"DETAIL_URL_COUNT={len(result.detail_urls)}")
    print(f"PAGES_FETCHED={result.pages_fetched}")
    print(f"PAGE_SIZE_OBSERVED={result.page_size_observed}")
    print(f"COVERAGE_RATIO={result.coverage_ratio:.6f}")

    for isin in result.isins[:25]:
        print(f"ISIN_SAMPLE={isin}")

    if result.total_count == len(result.isins):
        print("UNIVERSE_COVERAGE=COMPLETE_BY_ISIN_COUNT")
    elif len(result.isins) > 0:
        print("UNIVERSE_COVERAGE=PARTIAL_AFTER_PAGINATION")
    else:
        print("UNIVERSE_COVERAGE=EMPTY")

    print("CAPTURE_JSON=_discovery/erste_hungary/universe_paginated_latest.json")
    print("STORE_MUTATION=NO")
    print("ERSTE_REMOTE_MUTATION=NO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
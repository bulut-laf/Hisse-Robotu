from __future__ import annotations

from pathlib import Path
import json
import sys


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.funds.international.erste_hungary_source import (
    ERSTE_FUND_SEARCH_URL,
    discover_from_search_html,
    fetch_erste_fund_search_html,
)


def main() -> int:
    capture_dir = ROOT / "_discovery" / "erste_hungary"
    capture_dir.mkdir(parents=True, exist_ok=True)

    html = fetch_erste_fund_search_html(timeout_seconds=30.0)
    result = discover_from_search_html(html)

    (capture_dir / "fund_search_latest.html").write_text(
        html,
        encoding="utf-8",
    )
    payload = {
        "source_url": result.source_url,
        "html_length": result.html_length,
        "fund_count": result.fund_count,
        "isins": list(result.isins),
        "detail_urls": list(result.detail_urls),
        "script_urls": list(result.script_urls),
    }
    (capture_dir / "fund_search_discovery_latest.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"SOURCE_URL={ERSTE_FUND_SEARCH_URL}")
    print(f"HTML_LENGTH={result.html_length}")
    print(f"DISCOVERED_ISIN_COUNT={result.fund_count}")
    print(f"DISCOVERED_DETAIL_URL_COUNT={len(result.detail_urls)}")
    print(f"DISCOVERED_SCRIPT_URL_COUNT={len(result.script_urls)}")

    for isin in result.isins[:20]:
        print(f"ISIN_SAMPLE={isin}")

    for url in result.script_urls[:20]:
        low = url.casefold()
        if any(token in low for token in ("fund", "alap", "search", "keres", "api")):
            print(f"SCRIPT_CANDIDATE={url}")

    if result.fund_count > 0:
        print("DISCOVERY_STATE=STATIC_OR_EMBEDDED_ISINS_FOUND")
    else:
        print("DISCOVERY_STATE=DYNAMIC_LAYOUT_NO_ISINS_IN_INITIAL_HTML")

    print("CAPTURE_HTML=_discovery/erste_hungary/fund_search_latest.html")
    print("CAPTURE_JSON=_discovery/erste_hungary/fund_search_discovery_latest.json")
    print("STORE_MUTATION=NO")
    print("AL_SAT_MUTATION=NO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
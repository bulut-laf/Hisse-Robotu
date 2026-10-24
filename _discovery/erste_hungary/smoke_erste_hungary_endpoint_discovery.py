from __future__ import annotations

from pathlib import Path
import json
import sys


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.funds.international.erste_hungary_endpoint_discovery import (
    ERSTE_FUNDS_BUNDLE_URL,
    discover_endpoint_candidates,
    fetch_funds_bundle,
)


def main() -> int:
    capture_dir = ROOT / "_discovery" / "erste_hungary"
    capture_dir.mkdir(parents=True, exist_ok=True)

    javascript = fetch_funds_bundle(timeout_seconds=30.0)
    result = discover_endpoint_candidates(javascript)

    bundle_path = capture_dir / "funds_bundle_latest.js"
    json_path = capture_dir / "endpoint_discovery_latest.json"
    snippets_path = capture_dir / "endpoint_call_snippets_latest.txt"

    bundle_path.write_text(javascript, encoding="utf-8")

    payload = {
        "source_url": ERSTE_FUNDS_BUNDLE_URL,
        "bundle_length": result.bundle_length,
        "string_candidate_count": len(result.string_candidates),
        "absolute_url_candidate_count": len(result.absolute_url_candidates),
        "call_snippet_count": len(result.call_snippets),
        "string_candidates": list(result.string_candidates),
        "absolute_url_candidates": list(result.absolute_url_candidates),
    }
    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    snippets_path.write_text(
        "\n\n--- CALL ---\n\n".join(result.call_snippets),
        encoding="utf-8",
    )

    print(f"SOURCE_URL={ERSTE_FUNDS_BUNDLE_URL}")
    print(f"BUNDLE_LENGTH={result.bundle_length}")
    print(f"STRING_CANDIDATE_COUNT={len(result.string_candidates)}")
    print(f"ABSOLUTE_URL_CANDIDATE_COUNT={len(result.absolute_url_candidates)}")
    print(f"CALL_SNIPPET_COUNT={len(result.call_snippets)}")

    for value in result.string_candidates[:40]:
        print(f"STRING_CANDIDATE={value}")

    for value in result.absolute_url_candidates[:40]:
        print(f"URL_CANDIDATE={value}")

    print("CAPTURE_BUNDLE=_discovery/erste_hungary/funds_bundle_latest.js")
    print("CAPTURE_JSON=_discovery/erste_hungary/endpoint_discovery_latest.json")
    print("CAPTURE_SNIPPETS=_discovery/erste_hungary/endpoint_call_snippets_latest.txt")
    print("STORE_MUTATION=NO")
    print("ENDPOINT_MUTATION=NO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
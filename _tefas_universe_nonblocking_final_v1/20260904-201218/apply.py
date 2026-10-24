from pathlib import Path
import sys

root = Path(sys.argv[1])
dashboard = root / "backend/dashboard.py"
text = dashboard.read_text(encoding="utf-8")

import_anchor = "        from backend.app.funds.ui_live_refresh import refresh_fund_analysis_if_requested\n"
import_add = (
    import_anchor
    + "        from backend.app.funds.tefas_universe_nonblocking_refresh import (\n"
    + "            queue_tefas_universe_refresh,\n"
    + "        )\n"
)

if text.count(import_anchor) != 1:
    raise SystemExit(f"IMPORT_ANCHOR_COUNT={text.count(import_anchor)}")

start_marker = "        if auto_due and not refresh_requested:\n"
end_marker = "        if refresh_requested:\n"
start = text.find(start_marker)
end = text.find(end_marker, start)

if start < 0 or end < 0:
    raise SystemExit("AUTO_REFRESH_BLOCK_NOT_FOUND")
if text.find(start_marker, start + 1) >= 0:
    raise SystemExit("AUTO_REFRESH_BLOCK_NOT_UNIQUE")

new_block = (
    "        if auto_due and not refresh_requested:\n"
    "            refresh_state = queue_tefas_universe_refresh(\n"
    "                loader=lambda: refresh_fund_analysis_if_requested(\n"
    "                    requested=True,\n"
    "                    current_results=current_live_results,\n"
    "                ),\n"
    "                timeout_seconds=20.0,\n"
    "            )\n"
    "            if refresh_state.status == \"STARTED\":\n"
    "                st.session_state[\"fund_analysis_auto_refresh_attempt_at\"] = now_utc\n"
    "                st.caption(\n"
    "                    \"TEFAS fon evreni arka planda güncelleniyor; son iyi veri gösteriliyor.\"\n"
    "                )\n"
    "            elif refresh_state.status == \"RUNNING\":\n"
    "                st.caption(\n"
    "                    \"TEFAS fon evreni arka planda güncelleniyor; son iyi veri gösteriliyor.\"\n"
    "                )\n"
    "            elif refresh_state.status == \"DONE\" and refresh_state.result is not None:\n"
    "                refresh_outcome = refresh_state.result\n"
    "                if refresh_outcome.refreshed:\n"
    "                    st.session_state[live_results_key] = refresh_outcome.results\n"
    "                    current_live_results = refresh_outcome.results\n"
    "                    st.session_state[\"fund_analysis_auto_refresh_success_at\"] = now_utc\n"
    "                elif refresh_outcome.error_message:\n"
    "                    st.caption(\n"
    "                        \"Otomatik TEFAS yenilemesi şu anda kullanılamadı; son iyi veri korunuyor.\"\n"
    "                    )\n"
    "            elif refresh_state.status == \"FAILED\":\n"
    "                st.caption(\n"
    "                    \"Otomatik TEFAS yenilemesi izole edildi; son iyi veri korunuyor.\"\n"
    "                )\n"
    "            elif refresh_state.status == \"TIMEOUT\":\n"
    "                st.caption(\n"
    "                    \"Otomatik TEFAS yenilemesi zaman sınırını aştı; son iyi veri korunuyor.\"\n"
    "                )\n\n"
)

text = text[:start] + new_block + text[end:]
text = text.replace(import_anchor, import_add, 1)
dashboard.write_text(text, encoding="utf-8")

from __future__ import annotations

import json
from pathlib import Path

import streamlit as st


APP_TITLE = "Finansal Zekâ Paneli"
DEFAULT_SYMBOL = "TUPRS"


def _load_panel(symbol: str) -> dict:
    backend = Path(__file__).resolve().parent
    path = backend / "data" / "financial_intelligence" / f"{symbol}_financial_intelligence_panel.json"

    if not path.exists():
        raise FileNotFoundError(path)

    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise RuntimeError("FINANCIAL_INTELLIGENCE_PANEL_ARTIFACT_INVALID")
    return data


def _find(data, key, default=None):
    if isinstance(data, dict):
        if key in data:
            return data[key]
        for value in data.values():
            found = _find(value, key, default=None)
            if found is not None:
                return found
    elif isinstance(data, list):
        for value in data:
            found = _find(value, key, default=None)
            if found is not None:
                return found
    return default


def _metric(label: str, value):
    if value is None:
        value = "—"
    st.metric(label, value)


def main() -> None:
    st.set_page_config(page_title=APP_TITLE, layout="wide")
    st.title(APP_TITLE)
    st.caption("Financial Intelligence V1 — read-only decision support")

    symbol = st.sidebar.text_input("Sembol", value=DEFAULT_SYMBOL).strip().upper() or DEFAULT_SYMBOL

    try:
        panel = _load_panel(symbol)
    except FileNotFoundError:
        st.error(f"{symbol} için canonical panel artifact bulunamadı.")
        st.stop()
    except Exception as exc:
        st.error(f"Panel artifact okunamadı: {type(exc).__name__}: {exc}")
        st.stop()

    status = _find(panel, "status")
    coverage_status = _find(panel, "coverage_status")
    decision_support = _find(panel, "decision_support_status")
    health = _find(panel, "health_score")
    business_quality = _find(panel, "business_quality")
    short_term = _find(panel, "short_term_status")
    long_term = _find(panel, "long_term_status")

    st.subheader(symbol)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        _metric("Panel", status)
    with c2:
        _metric("Finansal Sağlık", health)
    with c3:
        _metric("İş Kalitesi", business_quality)
    with c4:
        _metric("Karar Desteği", decision_support)

    c1, c2, c3 = st.columns(3)
    with c1:
        _metric("Kısa Vade", short_term)
    with c2:
        _metric("Uzun Vade", long_term)
    with c3:
        _metric("Canonical Coverage", coverage_status)

    st.divider()
    st.subheader("Canonical Panel Artifact")
    st.json(panel)

    st.caption(
        "Read-only. AL/SAT, scanner, ranking ve portfolio motorlarını değiştirmez."
    )


if __name__ == "__main__":
    main()

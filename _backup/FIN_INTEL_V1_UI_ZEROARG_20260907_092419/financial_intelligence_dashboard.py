
from __future__ import annotations

from pathlib import Path
from typing import Any
import json


def _fmt(value: Any, *, decimals: int = 2, suffix: str = "") -> str:
    if value is None:
        return "—"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return f"{value}{suffix}"
    if number.is_integer():
        return f"{int(number)}{suffix}"
    return f"{number:.{decimals}f}{suffix}"


def _load_panel(project_root: Path, symbol: str) -> tuple[dict[str, Any] | None, Path]:
    path = (
        project_root
        / "backend"
        / "data"
        / "financial_intelligence"
        / f"{symbol.upper()}_financial_intelligence_panel.json"
    )
    if not path.exists():
        return None, path
    try:
        return json.loads(path.read_text(encoding="utf-8-sig")), path
    except (OSError, json.JSONDecodeError):
        return None, path


def render_financial_intelligence_dashboard(
    st: Any,
    *,
    project_root: Path,
    default_symbol: str = "TUPRS",
) -> None:
    """Read-only FIN-015 Financial Intelligence Panel."""
    st.markdown("## Finansal Zekâ Paneli")
    st.caption(
        "Finansal sağlık, değerleme, kısa/uzun vadeli kanıt ve veri kapsamını "
        "tek read-only karar destek ekranında birleştirir."
    )
    st.info(
        "Bu ekran AL/SAT, tarayıcı, sıralama veya portföy kararı üretmez ya da değiştirmez. "
        "Hazırlık ve kapsam durumları veri yeterliliğini gösterir."
    )

    symbol = st.text_input(
        "Hisse sembolü",
        value=default_symbol,
        key="financial_intelligence_panel_symbol",
    ).strip().upper()

    if not symbol:
        st.warning("Hisse sembolü girin.")
        return

    panel, path = _load_panel(project_root, symbol)
    if panel is None:
        st.warning(
            f"{symbol} için Financial Intelligence panel artifact'i bulunamadı veya okunamadı."
        )
        st.caption(str(path))
        return

    sections = panel.get("sections") or {}
    health = sections.get("financial_health") or {}
    valuation = sections.get("valuation") or {}
    short = sections.get("short_term_context") or {}
    long = sections.get("long_term_context") or {}
    coverage = sections.get("coverage_readiness") or {}
    source_health = panel.get("source_health") or {}

    status_cols = st.columns(4)
    status_cols[0].metric("Panel Durumu", str(panel.get("status") or "—"))
    status_cols[1].metric(
        "Coverage",
        str(coverage.get("coverage_status") or "—"),
    )
    status_cols[2].metric(
        "Decision Support",
        str(coverage.get("decision_support_status") or "—"),
    )
    status_cols[3].metric(
        "Kaynak Sağlığı",
        "COMPLETE" if source_health.get("complete") else "PARTIAL",
    )

    st.divider()

    st.markdown("### Finansal Sağlık")
    cols = st.columns(4)
    cols[0].metric("Financial Health", _fmt(health.get("score"), suffix="/100"))
    cols[1].metric("Cash Quality", _fmt(health.get("cash_quality_score"), suffix="/100"))
    cols[2].metric(
        "Capital Efficiency",
        _fmt(health.get("capital_efficiency_score")),
    )
    cols[3].metric("Risk", str(health.get("risk_status") or "—"))

    st.markdown("### Değerleme")
    cols = st.columns(4)
    cols[0].metric("Bear", _fmt(valuation.get("bear")))
    cols[1].metric("Base", _fmt(valuation.get("base")))
    cols[2].metric("Bull", _fmt(valuation.get("bull")))
    cols[3].metric("Güncel Fiyat", _fmt(valuation.get("current_price")))

    cols = st.columns(3)
    cols[0].metric("Margin of Safety", _fmt(valuation.get("margin_of_safety")))
    cols[1].metric("Cazip Giriş Fiyatı", _fmt(valuation.get("attractive_entry_price")))
    cols[2].metric("Değerleme Durumu", str(valuation.get("status") or "—"))

    short_tab, long_tab, quality_tab = st.tabs(
        ["Kısa Vadeli Bağlam", "Uzun Vadeli Bağlam", "Veri Kalitesi"]
    )

    with short_tab:
        st.caption(f"As-of: {short.get('as_of_date') or '—'}")
        cols = st.columns(3)
        cols[0].metric("Technical Trend", _fmt(short.get("technical_trend")))
        cols[1].metric("Relative Strength", _fmt(short.get("relative_strength")))
        cols[2].metric("Volume / Liquidity", _fmt(short.get("volume_liquidity")))
        st.write("Durum:", short.get("status") or "—")
        st.write("Data Quality:", short.get("data_quality") or "—")
        blockers = short.get("blockers") or []
        warnings = short.get("warnings") or []
        if blockers:
            st.error("Blockers: " + ", ".join(map(str, blockers)))
        if warnings:
            st.warning("Warnings: " + ", ".join(map(str, warnings)))

    with long_tab:
        st.caption(f"As-of: {long.get('as_of_date') or '—'}")
        cols = st.columns(4)
        cols[0].metric("Business Quality", _fmt(long.get("business_quality")))
        cols[1].metric("Governance", _fmt(long.get("governance")))
        cols[2].metric("Growth Durability", _fmt(long.get("growth_durability")))
        cols[3].metric("Capital Efficiency", _fmt(long.get("capital_efficiency")))
        st.write("Durum:", long.get("status") or "—")
        st.write("Coverage:", long.get("coverage") if long.get("coverage") is not None else "—")
        st.write("Data Quality:", long.get("data_quality") or "—")
        blockers = long.get("blockers") or []
        warnings = long.get("warnings") or []
        if blockers:
            st.error("Blockers: " + ", ".join(map(str, blockers)))
        if warnings:
            st.warning("Warnings: " + ", ".join(map(str, warnings)))

    with quality_tab:
        missing = source_health.get("missing_sources") or []
        if not missing:
            st.success("Tüm gerekli panel kaynakları mevcut.")
        else:
            st.warning("Eksik panel kaynakları var.")
            st.dataframe(missing, width="stretch", hide_index=True)

        unresolved = coverage.get("unresolved_blockers") or []
        if unresolved:
            st.error("Unresolved blockers: " + ", ".join(map(str, unresolved)))
        else:
            st.success("Unresolved blocker yok.")

        st.caption(f"Artifact: {path}")


from __future__ import annotations

from pathlib import Path
from typing import Any
import json

from app.analysis.financial_intelligence_bank_official_bundle_record import (
    build_bank_official_bundle_record,
)
from app.analysis.financial_intelligence_daily_context import (
    build_financial_intelligence_daily_context,
)
from app.analysis.financial_intelligence_bank_historical_trend import (
    build_bank_historical_trend,
)


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


def _load_dashboard_panel(
    project_root: Path,
    symbol: str,
) -> tuple[dict[str, Any] | None, Path]:
    normalized_symbol = str(symbol).strip().upper()

    fi_dir = (
        project_root
        / "backend"
        / "data"
        / "financial_intelligence"
    )

    bundle_paths = sorted(
        fi_dir.glob(
            f"{normalized_symbol}_*_OFFICIAL_EVIDENCE_BUNDLE.json"
        )
    )

    accepted: list[
        tuple[str, str, dict[str, Any], Path]
    ] = []

    for bundle_path in bundle_paths:
        record = build_bank_official_bundle_record(
            bundle_path
        )

        if record is None:
            continue

        if str(record.get("symbol", "")).strip().upper() != normalized_symbol:
            continue

        context = build_financial_intelligence_daily_context(
            project_root,
            normalized_symbol,
            bank_record=record,
        )

        bank = context.bank

        if bank is None:
            continue

        sections = dict(
            context.panel.get("sections") or {}
        )

        bank_section = sections.get(
            "bank_production"
        )

        if not isinstance(bank_section, dict):
            continue

        if bank_section.get("production_evidence") is not True:
            continue

        if bank_section.get("activation_ready") is not True:
            continue

        accepted.append(
            (
                bank.as_of,
                bank.publication_date,
                dict(context.panel),
                bundle_path,
            )
        )

    if accepted:
        accepted.sort(
            key=lambda item: (
                item[0],
                item[1],
                str(item[3]),
            )
        )

        _, _, panel, source_path = accepted[-1]

        return panel, source_path

    return _load_panel(
        project_root,
        normalized_symbol,
    )

def _build_bank_historical_rows(
    project_root: Path,
    symbol: str,
) -> list[dict[str, Any]]:
    trend = build_bank_historical_trend(
        project_root,
        symbol,
    )

    rows: list[dict[str, Any]] = []

    for snapshot in trend.snapshots:
        facts = snapshot.canonical_facts

        rows.append(
            {
                "Dönem": snapshot.period_end,
                "Yayın Tarihi": snapshot.publication_date,
                "BANK Skoru": round(
                    snapshot.total_score,
                    2,
                ),
                "CAR %": facts.get(
                    "CAPITAL_ADEQUACY.capital_adequacy_ratio"
                ),
                "Tier1 %": facts.get(
                    "CAPITAL_ADEQUACY.tier1_capital_ratio"
                ),
                "NPL %": facts.get(
                    "ASSET_QUALITY.npl_ratio"
                ),
                "NPL Coverage %": facts.get(
                    "ASSET_QUALITY.npl_coverage_ratio"
                ),
                "ROE %": facts.get(
                    "PROFITABILITY.roe"
                ),
                "ROA %": facts.get(
                    "PROFITABILITY.roa"
                ),
                "NIM %": facts.get(
                    "PROFITABILITY.net_interest_margin"
                ),
                "Loan / Deposit %": facts.get(
                    "FUNDING_LIQUIDITY.loan_to_deposit_ratio"
                ),
                "Liquidity %": facts.get(
                    "FUNDING_LIQUIDITY.liquidity_ratio"
                ),
                "Cost / Income %": facts.get(
                    "EFFICIENCY.cost_to_income_ratio"
                ),
                "Loan Growth %": facts.get(
                    "GROWTH_QUALITY.loan_growth"
                ),
                "Deposit Growth %": facts.get(
                    "GROWTH_QUALITY.deposit_growth"
                ),
                "Net Income Growth %": facts.get(
                    "GROWTH_QUALITY.net_income_growth"
                ),
            }
        )

    return rows

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

    panel, path = _load_dashboard_panel(
        project_root,
        symbol,
    )
    if panel is None:
        st.warning(
            f"{symbol} için Financial Intelligence panel artifact'i bulunamadı veya okunamadı."
        )
        st.caption(str(path))
        return

    sections = panel.get("sections") or {}
    bank_production = sections.get("bank_production") or {}
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

    if bank_production:
        st.markdown("### BANK Production Durumu")
        st.caption(
            "Resmi finansal kanıta dayalı read-only BANK production görünümü. "
            "AL/SAT, sıralama, tarayıcı veya portföy yetkisi içermez."
        )

        bank_cols = st.columns(2)

        bank_cols[0].metric(
            "BANK Durumu",
            str(bank_production.get("status") or "—"),
        )
        bank_cols[1].metric(
            "Sembol",
            str(bank_production.get("symbol") or "—"),
        )

        bank_cols = st.columns(2)

        bank_cols[0].metric(
            "As-of",
            str(bank_production.get("as_of") or "—"),
        )
        bank_cols[1].metric(
            "Yayın Tarihi",
            str(
                bank_production.get(
                    "publication_date"
                )
                or "—"
            ),
        )

        bank_cols = st.columns(2)

        bank_cols[0].metric(
            "Canonical Input",
            "READY"
            if bank_production.get(
                "canonical_input_ready"
            )
            is True
            else "NOT READY",
        )
        bank_cols[1].metric(
            "Scoring",
            "READY"
            if bank_production.get(
                "scoring_ready"
            )
            is True
            else "NOT READY",
        )

        bank_cols = st.columns(2)

        bank_cols[0].metric(
            "Production Evidence",
            "YES"
            if bank_production.get(
                "production_evidence"
            )
            is True
            else "NO",
        )
        bank_cols[1].metric(
            "Activation",
            "READY"
            if bank_production.get(
                "activation_ready"
            )
            is True
            else "NOT READY",
        )

        st.caption(
            "Kaynak tipi: "
            + str(
                bank_production.get(
                    "source_type"
                )
                or "—"
            )
        )

        historical_rows = _build_bank_historical_rows(
            project_root,
            symbol,
        )

        if historical_rows:
            st.markdown("#### Geçmiş Dönemler")
            st.caption(
                "Yalnız production gate'i geçen resmi BANK "
                "dönemleri gösterilir."
            )
            st.dataframe(
                historical_rows,
                width="stretch",
                hide_index=True,
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

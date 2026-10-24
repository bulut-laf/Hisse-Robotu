from __future__ import annotations

from typing import Any

from backend.app.analysis.research_profiles import ProfileState
from backend.app.analysis.research_profiles_daily import (
    DailyResearchProfileBundle,
    daily_research_profile_rows,
    daily_research_profile_summary,
)


PROFILE_LABELS = {
    "BABY_QUALITY_CAPEX": "Baby Quality + Capex",
    "CAPEX_TO_EARNINGS": "Capex → Earnings",
    "EARNINGS_INFLECTION": "Earnings Inflection",
}


def research_profiles_table_rows(
    bundle: DailyResearchProfileBundle,
) -> tuple[dict[str, object], ...]:
    rows = []
    for row in daily_research_profile_rows(bundle):
        item = dict(row)
        item["Profil"] = PROFILE_LABELS.get(str(item["Profil"]), str(item["Profil"]))
        rows.append(item)
    return tuple(rows)


def render_research_profiles_panel(
    st: Any,
    bundle: DailyResearchProfileBundle,
) -> None:
    st.subheader("Research Profiles")
    st.caption(
        "Aynı günlük BIST taramasının read-only fundamental araştırma görünümüdür. "
        "Yeni tarama, yeni skor veya AL/SAT kararı üretmez."
    )

    summary = daily_research_profile_summary(bundle)
    cols = st.columns(5)
    metrics = (
        ("Kapsanan hisse", f"{bundle.covered_symbol_count}/{bundle.successful_symbol_count}"),
        ("MATCH", str(summary[ProfileState.MATCH.value])),
        ("WATCH", str(summary[ProfileState.WATCH.value])),
        ("BLOCKED", str(summary[ProfileState.BLOCKED.value])),
        ("INSUFFICIENT", str(summary[ProfileState.INSUFFICIENT.value])),
    )
    for column, (label, value) in zip(cols, metrics):
        column.metric(label, value)

    rows = research_profiles_table_rows(bundle)
    profile_options = ("Tümü",) + tuple(PROFILE_LABELS.values())
    selected_profile = st.selectbox(
        "Research Profile",
        options=profile_options,
        index=0,
        key="rpv1_profile_filter",
    )
    selected_states = st.multiselect(
        "Profil durumu",
        options=tuple(state.value for state in ProfileState),
        default=(ProfileState.MATCH.value, ProfileState.WATCH.value, ProfileState.BLOCKED.value),
        key="rpv1_state_filter",
    )
    filtered = [
        row
        for row in rows
        if (selected_profile == "Tümü" or row["Profil"] == selected_profile)
        and row["Durum"] in selected_states
    ]

    if filtered:
        st.dataframe(
            filtered,
            width="stretch",
            hide_index=True,
        )
    else:
        st.info("Seçili Research Profile filtrelerinde gösterilecek kayıt yok.")

    if (
        summary[ProfileState.MATCH.value] == 0
        and summary[ProfileState.WATCH.value] == 0
        and summary[ProfileState.INSUFFICIENT.value] > 0
    ):
        st.info(
            "Research Profile kapsamı henüz yetersiz. Eksik fundamental/market-cap/"
            "free-float/capex verisi profil başarısızlığı sayılmaz; INSUFFICIENT olarak "
            "korunur."
        )

    st.caption(
        f"Profil değerlendirme tarihi: {bundle.as_of.isoformat()} · "
        "MATCH ≠ AL · profile exit ≠ SAT."
    )

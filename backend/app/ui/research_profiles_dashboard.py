
from __future__ import annotations

from typing import Any

from backend.app.analysis.research_profiles import ProfileState
from backend.app.analysis.research_profiles_daily import (
    DailyResearchProfileBundle,
    daily_research_profile_rows,
    daily_research_profile_summary,
)
from backend.app.analysis.research_profile_memory import (
    RESEARCH_PROFILE_MEMORY_ACTIVATION_DATE,
    load_profile_memory_context,
)

PROFILE_LABELS = {
    "BABY_QUALITY_CAPEX": "Baby Quality + Capex",
    "CAPEX_TO_EARNINGS": "Capex → Earnings",
    "EARNINGS_INFLECTION": "Earnings Inflection",
}


def research_profiles_table_rows(bundle: DailyResearchProfileBundle):
    try:
        lifecycle_map, rank_map = load_profile_memory_context(bundle)
    except (OSError, ValueError, TypeError, KeyError):
        lifecycle_map, rank_map = {}, {}

    rows = []
    for row in daily_research_profile_rows(bundle):
        item = dict(row)
        profile_code = str(item["Profil"])
        symbol = str(item["Hisse"]).strip().upper()

        item["Profil"] = PROFILE_LABELS.get(profile_code, profile_code)
        lifecycle = lifecycle_map.get((symbol, profile_code))
        rank = rank_map.get(symbol)

        item["İlk MATCH"] = lifecycle.first_match if lifecycle else None
        item["Son MATCH"] = lifecycle.last_match if lifecycle else None
        item["MATCH serisi"] = lifecycle.consecutive_match_sessions if lifecycle else 0
        item["Profil yaşı (S)"] = lifecycle.profile_age_sessions if lifecycle else 0
        item["Profil olayı"] = lifecycle.event if lifecycle else None

        item["Ana Research sıra"] = rank.current_rank if rank else None
        item["Sıra yolu"] = rank.rank_path if rank else "Ana Research sıralamasında değil"
        item["1S Δ"] = rank.gain_1s if rank else None
        item["3S Δ"] = rank.gain_3s if rank else None
        item["5S Δ"] = rank.gain_5s if rank else None
        item["Ranking lifecycle"] = rank.lifecycle if rank else None
        item["Early Visibility"] = (
            "WARMING UP" if rank is None or rank.warming_up else "COMPARABLE"
        )
        rows.append(item)
    return tuple(rows)


def render_research_profiles_panel(st: Any, bundle: DailyResearchProfileBundle) -> None:
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
    selected_profile = st.selectbox(
        "Research Profile",
        options=("Tümü",) + tuple(PROFILE_LABELS.values()),
        index=0,
        key="rpv1_profile_filter",
    )
    selected_states = st.multiselect(
        "Profil durumu",
        options=tuple(state.value for state in ProfileState),
        default=(
            ProfileState.MATCH.value,
            ProfileState.WATCH.value,
            ProfileState.BLOCKED.value,
        ),
        key="rpv1_state_filter",
    )
    filtered = [
        row for row in rows
        if (selected_profile == "Tümü" or row["Profil"] == selected_profile)
        and row["Durum"] in selected_states
    ]

    if filtered:
        st.dataframe(filtered, width="stretch", hide_index=True)
    else:
        st.info("Seçili Research Profile filtrelerinde gösterilecek kayıt yok.")

    if bundle.as_of < RESEARCH_PROFILE_MEMORY_ACTIVATION_DATE:
        st.info(
            "Profile Memory WARMING UP: bu taramanın analiz tarihi forward-only "
            "aktivasyon tarihinden önce. Geçmiş profile sonucu backfill edilmeyecek."
        )
    elif (
        summary[ProfileState.MATCH.value] == 0
        and summary[ProfileState.WATCH.value] == 0
        and summary[ProfileState.INSUFFICIENT.value] > 0
    ):
        st.info(
            "Eksik fundamental/market-cap/free-float/capex verisi profil başarısızlığı "
            "sayılmaz; INSUFFICIENT olarak korunur."
        )

    st.caption(
        f"Profil değerlendirme tarihi: {bundle.as_of.isoformat()} · "
        "Profile Memory forward-only: 2026-08-26 → · MATCH ≠ AL · profile exit ≠ SAT."
    )

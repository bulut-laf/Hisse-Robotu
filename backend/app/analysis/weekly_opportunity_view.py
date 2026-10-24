from __future__ import annotations

from backend.app.analysis.weekly_opportunity import WeeklyOpportunityResult


def weekly_opportunity_rows(result: WeeklyOpportunityResult) -> tuple[dict[str, object], ...]:
    rows = []
    for x in result.candidates:
        p = x.price_plan
        rows.append({
            "Hisse": x.symbol,
            "Weekly Stage": x.stage.value,
            "Durum": x.state.value,
            "Research Rank": x.research_rank,
            "Evidence": ", ".join(x.evidence_families),
            "Next-Day": x.next_day_status,
            "Güncel": p.current_price,
            "Alım Bölgesi Alt": p.entry_zone_low,
            "Alım Bölgesi Üst": p.entry_zone_high,
            "İdeal Giriş": p.ideal_entry,
            "Zarar Kes": p.stop_loss,
            "Hedef 1": p.target_1,
            "Hedef 2": p.target_2,
            "Risk/Ödül": p.risk_reward,
            "Geç Giriş Üstü": p.late_entry_above,
            "Neden Görünür": x.why_visible_now,
            "Sonraki Teyit": x.what_must_happen_next,
            "Invalidation": x.what_invalidates_setup,
            "Pilot": x.pilot_research_status,
        })
    return tuple(rows)

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from backend.app.market_context.daily_market_briefing import (
    build_daily_market_briefing_snapshot,
    coverage_rows,
    recommendation_rows,
)


def _selected_review_date(st):
    return st.session_state.get("market_context_date", date.today())


def render_daily_market_briefing_panel(st, *, project_root: Path) -> None:
    """Seans Öncesi Bağlam için kaynak kapsama ve kurum görüşü görünümü."""

    snapshot = build_daily_market_briefing_snapshot(
        project_root,
        _selected_review_date(st),
    )

    st.markdown("### AI Günlük Piyasa Brifingi — Kaynak Kapsama")
    st.caption(
        "Bu bölüm yeni AI çağrısı yapmaz. Seçili tarih için işlenmiş rapor deposunu "
        "saydamlaştırır ve kaynakta açıkça yazılı kurum görüşlerini ayrı gösterir. "
        "Kurum görüşleri Hisse Robotu'nun AL/SAT kararı değildir ve teknik skoru değiştirmez."
    )

    left, middle, right = st.columns(3)
    left.metric("İşlenmiş rapor", str(snapshot.report_count))
    middle.metric("Benzersiz kaynak", str(len(snapshot.source_names)))
    right.metric("Açık kurum görüşü", str(snapshot.recommendation_count))

    if not snapshot.reports:
        st.info(
            f"{snapshot.review_date} için market_context_processed deposunda okunabilir "
            "rapor bulunamadı. Önce içeriği işleyip kaydedin."
        )
        return

    st.caption(
        "Kapsama kontrolü: aşağıdaki kayıtların ham metni seçili günün işlenmiş rapor "
        "deposunda mevcut. Bu sayı, AI toplu değerlendirmesinde eksik kaynak olup olmadığını "
        "kontrol etmek için kullanılabilir."
    )

    with st.expander(
        f"İşlenmiş rapor kapsaması · {snapshot.report_count}/{snapshot.report_count}",
        expanded=False,
    ):
        st.dataframe(
            pd.DataFrame(coverage_rows(snapshot)),
            width="stretch",
            hide_index=True,
        )

    st.markdown("#### Aracı kurum / kaynak görüşleri")
    if snapshot.recommendations:
        st.dataframe(
            pd.DataFrame(recommendation_rows(snapshot)),
            width="stretch",
            hide_index=True,
            column_config={
                "Hedef fiyat": st.column_config.NumberColumn(format="%.2f"),
                "Potansiyel (%)": st.column_config.NumberColumn(format="%.2f"),
                "Kaynak satırı": st.column_config.TextColumn(width="large"),
            },
        )
        st.caption(
            "Yalnız kaynak metninde açık AL/TUT/SAT/NÖTR veya endeks-göreli görüş bulunan "
            "satırlar gösterilir. Sistem eksik tavsiyeyi tahmin etmez ve yeni tavsiye üretmez."
        )
    else:
        st.info(
            "İşlenmiş raporlarda güvenli kuralla yakalanabilen açık AL/TUT/SAT/NÖTR "
            "kurum görüşü bulunmadı. Hedef fiyat tek başına Hisse Robotu tavsiyesine dönüştürülmez."
        )

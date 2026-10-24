from datetime import date

from backend.app.prebreakout.prebreakout_backtest import (
    PreBreakoutForwardPerformance,
    PreBreakoutReplayResult,
)
from backend.app.prebreakout.prebreakout_models import (
    PreBreakoutResult,
    PreBreakoutStage,
)
from backend.app.prebreakout.prebreakout_report import (
    replay_sonuclarini_tabloya_cevir,
)


def test_rapor_performans_etiketini_icerir() -> None:
    analysis = PreBreakoutResult(
        symbol="TEST.IS",
        score=65,
        stage=PreBreakoutStage.E2,
        stage_label="Dirence yaklaşıyor",
        features=None,
        component_scores=None,
        late_entry=False,
        accepted=True,
        reasons=(),
        risks=(),
    )
    result = PreBreakoutReplayResult(
        symbol="TEST.IS",
        cutoff_date=date(2026, 7, 1),
        analysis=analysis,
        entry_close=100.0,
        forward=(
            PreBreakoutForwardPerformance(
                horizon=10,
                close_return_pct=6.0,
                max_return_pct=8.0,
                min_return_pct=-2.0,
                available=True,
            ),
        ),
    )

    table = replay_sonuclarini_tabloya_cevir([result])

    assert table.loc[0, "performance_label"] == "Başarılı"

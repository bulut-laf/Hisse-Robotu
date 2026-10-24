from datetime import date

from backend.app.prebreakout.prebreakout_backtest import (
    PreBreakoutForwardPerformance,
    PreBreakoutReplayResult,
)
from backend.app.prebreakout.prebreakout_models import (
    PreBreakoutResult,
    PreBreakoutStage,
)
from backend.app.ui.prebreakout_dashboard import replay_sonuc_satiri


def test_dashboard_tarihsel_satirinda_performans_etiketi_var() -> None:
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
    replay = PreBreakoutReplayResult(
        symbol="TEST.IS",
        cutoff_date=date(2026, 7, 1),
        analysis=analysis,
        entry_close=100.0,
        forward=(
            PreBreakoutForwardPerformance(
                horizon=5,
                close_return_pct=-7.0,
                max_return_pct=1.0,
                min_return_pct=-8.0,
                available=True,
            ),
        ),
    )

    row = replay_sonuc_satiri(replay)

    assert row["Performans etiketi"] == "Yanlış pozitif"

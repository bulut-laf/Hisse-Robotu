from datetime import date
from pathlib import Path

from backend.app.prebreakout.prebreakout_backtest import (
    PreBreakoutForwardPerformance,
    PreBreakoutReplayResult,
)
from backend.app.prebreakout.prebreakout_models import (
    PreBreakoutResult,
    PreBreakoutStage,
)
from backend.app.ui.prebreakout_dashboard import (
    replay_sonuc_satiri,
    sembolleri_hazirla,
)


def test_semboller_duzeltilir_ve_tekrarlar_atilir() -> None:
    assert sembolleri_hazirla(
        "thyao, ASELS.IS, thyao\nTUPRS"
    ) == ("THYAO.IS", "ASELS.IS", "TUPRS.IS")


def test_hazirlik_ekrani_evren_ve_sonuc_limiti_sunar() -> None:
    source = Path(
        "backend/app/ui/prebreakout_dashboard.py"
    ).read_text(encoding="utf-8")
    assert '"Evren"' in source
    assert '"Gösterilecek sonuç"' in source
    assert "ON_YUKSELIS_EVRENLERI" in source


def test_replay_satiri_ileri_performansi_icerir() -> None:
    analysis = PreBreakoutResult(
        symbol="THYAO.IS",
        score=64,
        stage=PreBreakoutStage.E2,
        stage_label="Dirence yaklaşıyor",
        features=None,
        component_scores=None,
        late_entry=False,
        accepted=True,
        reasons=("Momentum toparlanıyor.",),
        risks=(),
    )
    replay = PreBreakoutReplayResult(
        symbol="THYAO.IS",
        cutoff_date=date(2026, 7, 1),
        analysis=analysis,
        entry_close=300.0,
        forward=(
            PreBreakoutForwardPerformance(
                horizon=5,
                close_return_pct=2.0,
                max_return_pct=5.0,
                min_return_pct=-1.0,
                available=True,
            ),
        ),
    )

    row = replay_sonuc_satiri(replay)

    assert row["Hisse"] == "THYAO"
    assert row["Kesim tarihi"] == "2026-07-01"
    assert row["5G en yüksek %"] == 5.0

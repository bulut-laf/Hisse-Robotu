from __future__ import annotations

from datetime import date
from typing import Mapping, Sequence

from backend.app.analysis.momentum_walk_forward import (
    MomentumWalkForwardRequest,
    MomentumWalkForwardService,
    walk_forward_tablosu,
)
from backend.app.history.replay_batch_adapter import common_universe_mapper
from backend.app.ui.batch_historical_export_ui import (
    render_batch_historical_export_panel,
)


def momentum_batch_scan_day(
    cut_date: date,
    universe: str,
    *,
    minimum_skor: int,
    maksimum_aday: int,
    ozel_semboller: tuple[str, ...],
    internetten_guncelle: bool,
) -> Sequence[Mapping[str, object]]:
    """
    Sprint-135 uyumluluk fonksiyonu.
    Tek günlük Momentum Walk-Forward sonucunu batch export satırlarına dönüştürür.
    """
    request = MomentumWalkForwardRequest(
        evren=common_universe_mapper(universe),
        kesim_tarihi=cut_date.isoformat(),
        maksimum_aday=int(maksimum_aday),
        minimum_skor=int(minimum_skor),
        ozel_semboller=ozel_semboller,
        internetten_evren_guncelle=bool(internetten_guncelle),
    )
    result = MomentumWalkForwardService().calistir(request)
    return tuple(dict(row) for row in walk_forward_tablosu(result))


def render_momentum_batch_history_panel(
    st,
    *,
    minimum_skor: int,
    maksimum_aday: int,
    ozel_semboller: tuple[str, ...],
    internetten_guncelle: bool,
    default_start_date: date,
    default_end_date: date,
):
    """
    Sprint-135 geriye dönük uyumluluk katmanı.
    Eski testler ve olası dış çağrılar bozulmadan kalır.
    """
    def scan_day(cut_date: date, universe: str):
        return momentum_batch_scan_day(
            cut_date,
            universe,
            minimum_skor=minimum_skor,
            maksimum_aday=maksimum_aday,
            ozel_semboller=ozel_semboller,
            internetten_guncelle=internetten_guncelle,
        )

    return render_batch_historical_export_panel(
        st,
        scan_day=scan_day,
        default_start_date=default_start_date,
        default_end_date=default_end_date,
        universe_options=("BIST100", "BIST Tüm"),
    )


class ReusableMomentumBatchScanner:
    """
    Sprint-136 hızlı/dayanıklı akışında tek MomentumWalkForwardService örneğini
    tüm tarih aralığında yeniden kullanır.
    """

    def __init__(
        self,
        *,
        minimum_skor: int,
        maksimum_aday: int,
        ozel_semboller: tuple[str, ...],
        internetten_guncelle: bool,
    ) -> None:
        self.minimum_skor = int(minimum_skor)
        self.maksimum_aday = int(maksimum_aday)
        self.ozel_semboller = tuple(ozel_semboller)
        self.internetten_guncelle = bool(internetten_guncelle)
        self._service = MomentumWalkForwardService()

    def scan_day(
        self,
        cut_date: date,
        universe: str,
    ) -> Sequence[Mapping[str, object]]:
        request = MomentumWalkForwardRequest(
            evren=common_universe_mapper(universe),
            kesim_tarihi=cut_date.isoformat(),
            maksimum_aday=self.maksimum_aday,
            minimum_skor=self.minimum_skor,
            ozel_semboller=self.ozel_semboller,
            internetten_evren_guncelle=self.internetten_guncelle,
        )
        result = self._service.calistir(request)
        return tuple(dict(row) for row in walk_forward_tablosu(result))

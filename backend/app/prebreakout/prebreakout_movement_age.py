from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from enum import Enum

class MovementPhase(str, Enum):
    YETERSIZ="Yetersiz veri"; ERKEN="Erken"; GELISIYOR="Gelişiyor"; GUCLU="Güçlü"; OLGUN="Olgun"; YORULUYOR="Yoruluyor"

class EarlyRadarState(str, Enum):
    YOK="Yok"; IZLE="İzle"; YUKSEK_ONCELIK="Yüksek öncelik"

class MaturityWarning(str, Enum):
    YOK="Yok"; OLGUNLASIYOR="Olgunlaşıyor"; KAR_KORUMA="Kâr koruma"

@dataclass(frozen=True)
class RankingSnapshot:
    observation_date: date
    rank: int | None
    score: float
    price: float
    momentum: float | None = None
    atr_distance: float | None = None
    stage: str | None = None
    def __post_init__(self):
        if self.rank is not None and self.rank < 1: raise ValueError("rank 1 veya daha büyük olmalıdır.")
        if not 0 <= self.score <= 100: raise ValueError("score 0-100 arasında olmalıdır.")
        if self.price <= 0: raise ValueError("price pozitif olmalıdır.")

@dataclass(frozen=True)
class MovementAgeReport:
    first_seen_date: date | None
    first_top30_date: date | None
    first_top10_date: date | None
    first_top5_date: date | None
    sessions_since_first_seen: int
    rank_velocity: float | None
    score_velocity: float | None
    momentum_velocity: float | None
    realized_move_pct: float
    phase: MovementPhase
    early_radar: EarlyRadarState
    maturity_warning: MaturityWarning
    reasons: tuple[str,...]

def _first_date(history, max_rank):
    for x in history:
        if x.rank is not None and x.rank <= max_rank:
            return x.observation_date
    return None

def _velocity(values):
    if len(values) < 2: return None
    return (values[-1]-values[0])/(len(values)-1)

def _rank_velocity(history, window=4):
    ranked=[x for x in history if x.rank is not None][-window:]
    if len(ranked)<2: return None
    return (ranked[0].rank-ranked[-1].rank)/(len(ranked)-1)

def analyze_movement_age(history: tuple[RankingSnapshot,...], *, early_rank_low=11, early_rank_high=30,
                         maturity_min_sessions=6, maturity_move_pct=18.0, peak_score_drop=3.0):
    if not history:
        return MovementAgeReport(None,None,None,None,0,None,None,None,0.0,MovementPhase.YETERSIZ,
                                 EarlyRadarState.YOK,MaturityWarning.YOK,("Geçmiş gözlem yok.",))
    ordered=tuple(sorted(history,key=lambda x:x.observation_date))
    seen=[x for x in ordered if x.rank is not None]
    first_seen=seen[0].observation_date if seen else None
    sessions=len(seen)
    rv=_rank_velocity(ordered)
    recent_scores=[x.score for x in ordered[-4:]]
    sv=_velocity(recent_scores)
    recent_m=[float(x.momentum) for x in ordered[-4:] if x.momentum is not None]
    mv=_velocity(recent_m)
    move=(ordered[-1].price/ordered[0].price-1)*100
    cur=ordered[-1]
    reasons=[]

    in_band=cur.rank is not None and early_rank_low <= cur.rank <= early_rank_high
    rank_up=rv is not None and rv>0
    score_up=sv is not None and sv>0
    mom_up=mv is not None and mv>0

    if in_band and rank_up and (score_up or mom_up):
        radar=EarlyRadarState.YUKSEK_ONCELIK
        reasons.append("11-30 bandında ve sıralama ivmesi yukarı.")
    elif in_band:
        radar=EarlyRadarState.IZLE
        reasons.append("11-30 bandında erken radar adayı.")
    else:
        radar=EarlyRadarState.YOK

    if cur.rank is not None and cur.rank <= 5:
        if sessions >= maturity_min_sessions or move >= maturity_move_pct:
            warning=MaturityWarning.KAR_KORUMA
            reasons.append("İlk 5'e geldiğinde hareket yaşı veya gerçekleşmiş getiri yüksek.")
        else:
            warning=MaturityWarning.OLGUNLASIYOR
            reasons.append("İlk 5 teknik gücü teyit ediyor; hareket olgunlaşma kontrolünde.")
    else:
        warning=MaturityWarning.YOK

    # Zirve sonrası bozulmayı toplam eğimden ayrı ele al.
    recent_peak=max(recent_scores) if recent_scores else cur.score
    peak_drop=recent_peak-cur.score
    post_peak_decline = warning is MaturityWarning.KAR_KORUMA and peak_drop >= peak_score_drop

    if post_peak_decline:
        phase=MovementPhase.YORULUYOR
        reasons.append("Skor zirvesinden anlamlı geri çekilme var.")
    elif warning is MaturityWarning.KAR_KORUMA:
        phase=MovementPhase.OLGUN
    elif sessions <= 2:
        phase=MovementPhase.ERKEN
    elif radar is EarlyRadarState.YUKSEK_ONCELIK:
        phase=MovementPhase.GELISIYOR
    elif cur.rank is not None and cur.rank <= 10:
        phase=MovementPhase.GUCLU
    else:
        phase=MovementPhase.GELISIYOR

    return MovementAgeReport(
        first_seen,_first_date(ordered,30),_first_date(ordered,10),_first_date(ordered,5),
        sessions,rv,sv,mv,move,phase,radar,warning,tuple(reasons)
    )

def top5_forward_performance(*, entry_price: float, future_closes: tuple[float,...]):
    if entry_price <= 0: raise ValueError("entry_price pozitif olmalıdır.")
    out={"1d":None,"3d":None,"5d":None}
    for label,idx in (("1d",0),("3d",2),("5d",4)):
        if len(future_closes)>idx:
            out[label]=(future_closes[idx]/entry_price-1)*100
    return out

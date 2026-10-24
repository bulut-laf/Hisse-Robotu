from dataclasses import dataclass
from enum import Enum


class EodDecisionState(str, Enum):
    ALIS_ADAYI = "ALIS_ADAYI"
    BEKLE = "BEKLE"
    ELENDI = "ELENDI"


@dataclass(frozen=True)
class EodDecision:
    state: EodDecisionState
    reason: str


def decide_eod_candidate(validation, freshness, evidence, close) -> EodDecision:

    if freshness.state in {"DATA_KILITLI", "DATA_YETERSIZ"}:
        return EodDecision(
            EodDecisionState.BEKLE,
            "Seans sonu verisi karar için yeterli değil.",
        )

    if validation.state == "VERI_YETERSIZ":
        return EodDecision(
            EodDecisionState.BEKLE,
            "Intraday doğrulama verisi yetersiz.",
        )

    if validation.state != "ADAY_DESTEKLENIYOR":
        return EodDecision(
            EodDecisionState.ELENDI,
            "Intraday hareket adayı desteklemiyor.",
        )

    if close.close_state == "NEGATIF_KAPANIS":
        return EodDecision(
            EodDecisionState.ELENDI,
            "Negatif kapanış davranışı.",
        )

    if close.close_state == "ZAYIF_KAPANIS":
        return EodDecision(
            EodDecisionState.BEKLE,
            "Kapanış gücü yetersiz.",
        )

    if (
        close.close_state == "POZITIF_KAPANIS"
        and evidence.volume_state == "ZAYIF"
    ):
        return EodDecision(
            EodDecisionState.BEKLE,
            "Pozitif kapanış hacim tarafından desteklenmiyor.",
        )

    if close.close_state == "POZITIF_KAPANIS":
        return EodDecision(
            EodDecisionState.ALIS_ADAYI,
            "Intraday hareket destekliyor, kapanış pozitif.",
        )

    return EodDecision(
        EodDecisionState.BEKLE,
        "Seans sonu koşulları yeterince güçlü değil.",
    )


def evaluate_eod_decision(validation, freshness, evidence, close) -> EodDecision:
    return decide_eod_candidate(
        validation=validation,
        freshness=freshness,
        evidence=evidence,
        close=close,
    )


from dataclasses import dataclass


@dataclass(frozen=True)
class LongTermPatternIntelligenceState:
    symbol: str
    historical_case_state: str
    cross_period_state: str
    pattern_state: str
    source: str = "EARLY_VISIBILITY"


def build_long_term_pattern_intelligence_state(symbol: str):
    return LongTermPatternIntelligenceState(
        symbol=str(symbol).upper(),
        historical_case_state="PREPARED",
        cross_period_state="OBSERVED",
        pattern_state="FOUNDATION",
    )

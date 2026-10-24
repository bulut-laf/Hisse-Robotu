from dataclasses import dataclass

from backend.app.analysis.eod_decision_gate import EodDecisionState


@dataclass(frozen=True)
class EodCandidateOutput:
    symbols: tuple[str, ...]

    @property
    def count(self) -> int:
        return len(self.symbols)


def build_eod_candidate_output(
    candidate_symbols,
    eod_decisions,
) -> EodCandidateOutput:
    selected: list[str] = []

    for symbol in candidate_symbols:
        decision = eod_decisions.get(symbol)

        if decision is None:
            continue

        if decision.state == EodDecisionState.ALIS_ADAYI:
            selected.append(symbol)

    return EodCandidateOutput(
        symbols=tuple(selected),
    )


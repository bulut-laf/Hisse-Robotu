import type { CefrLearningJourneyView } from "./CefrLearningJourneyView";

export interface CefrLearnerInsightView {
  readonly currentFocus: string;
  readonly evidenceVisibility: string;
  readonly continuityHint: string;
  readonly practiceOpportunity: string;
  readonly nextLearningAction: string;
}

export function createCefrLearnerInsightView(
  journey: CefrLearningJourneyView,
  evidenceSummary: string,
  guidanceHint: string,
): CefrLearnerInsightView {
  return {
    currentFocus: journey.currentPositionLabel,
    evidenceVisibility: evidenceSummary,
    continuityHint: guidanceHint,
    practiceOpportunity:
      "Mevcut öğrenme odağınızı destekleyen pratiklere devam edin.",
    nextLearningAction: journey.nextActionLabel,
  };
}

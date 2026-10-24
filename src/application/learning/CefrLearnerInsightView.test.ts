import { describe, expect, it } from "vitest";
import { createCefrLearnerInsightView } from "./CefrLearnerInsightView";

describe("CefrLearnerInsightView", () => {
  it("creates learner-facing insight without adding authority", () => {
    const result = createCefrLearnerInsightView(
      {
        title: "LAF CEFR Öğrenme Yolu",
        levels: [],
        currentLevelCode: "A1",
        currentPositionLabel: "A1 — Yanıt Ver",
        currentPositionDetail: "detail",
        nextActionLabel: "Öğrenme planına devam edin.",
        progressLabel: "İlerleme yeterlik değildir.",
        advanceLabel: "Kanıt gerekir.",
        ctaLabel: "Devam",
        ctaSelector: ".test",
      },
      "Gerçek evidence görünürlüğü",
      "Devam önerisi",
    );

    expect(result.currentFocus).toBe("A1 — Yanıt Ver");
    expect(result.evidenceVisibility).toBe("Gerçek evidence görünürlüğü");
    expect(result.continuityHint).toBe("Devam önerisi");
    expect(result.nextLearningAction).toBe("Öğrenme planına devam edin.");
  });
});

Financial Intelligence V1.3
AKBNK Tier1 Selection and Canonical Gate V1

Purpose:
- Consume the already-generated AKBNK Tier1 exact-evidence probe JSON.
- Accept only the exact semantic evidence:
  "Konsolide Ana Sermaye Yeterliliği Oranı (%) 13,33% 15,45%"
- Select current-period CAPITAL_ADEQUACY.tier1_capital_ratio = 13.33.
- Merge only already-proven dotted-key metrics.
- Re-run the BANK canonical adapter fail-closed.
- Surface the next missing BANK canonical metric automatically.

Safety:
- No missing->0.
- No future publication.
- No scoring activation.
- No production/store/AL-SAT/scanner/ranking/portfolio mutation.
- No INDUSTRIAL threshold reuse.
- No full regression; targeted block gate only.

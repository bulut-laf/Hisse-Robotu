HISSE ROBOTU - FUND ANALYSIS UI BRIDGE V1

Scope
- Existing Fon Analiz Merkezi is preserved.
- Existing append-only portfolio snapshot store is connected read-only to the UI.
- Current portfolio, dated portfolio changes, new entries, full exits,
  confirmed increases/reductions, and stock-level accumulation/distribution breadth are displayed.
- Fon/FDO + liquidation + three observational pressure scores have a UI read-model surface.
- No AL/SAT authority and no canonical ranking mutation.

Safety
- Standard git patch only.
- git apply --check runs before mutation.
- If already applied, reverse-check detects that state and tests continue.
- Target tests run before full regression.

Important data boundary
The UI does not fabricate portfolio holdings or risk inputs. If the production
portfolio snapshot store is empty, the UI shows an explicit empty state.
Fon/FDO / liquidation / pressure rows remain empty until the corresponding
production inputs are populated.

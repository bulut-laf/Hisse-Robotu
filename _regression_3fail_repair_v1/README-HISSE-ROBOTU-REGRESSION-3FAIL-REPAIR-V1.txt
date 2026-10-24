HISSE ROBOTU - REGRESSION 3FAIL REPAIR V1

Fixes only the three observed regression causes:
1) VBTS health report now treats a missing active CSV as healthy when the registry has zero currently-active records.
2) Leading UTF-8 BOM bytes are removed from backend Python sources without changing the remaining bytes.
3) This also removes the source-compile failure that made SystemCheckReport.kullanima_hazir false.

The runner performs:
- git apply --check before the source patch
- source patch
- BOM normalization
- the exact three formerly-failing tests
- fund target tests
- full backend regression with PYTHONPATH configured for both backend.* and app.* imports

No AL/SAT or canonical ranking mutation is made by this repair.

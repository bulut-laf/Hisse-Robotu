FIN-001 — KAP Canonical Financial Import V1

Purpose:
- Parse KAP's HTML-based .xls financial statement downloads deterministically.
- Preserve raw source labels and periods.
- Map a conservative core set to canonical metric codes.
- Do NOT fabricate missing EBITDA, share count, valuation, or sector facts.
- Do NOT mutate existing Fundamental V1 scoring / scanner / AL-SAT behavior.

Install:
1) Extract package.
2) Run INSTALL-FIN-001.ps1 in PowerShell.
3) Expect: FIN-001 INSTALL PASS

After installation, full regression remains required before closeout:
.\.venv\Scripts\python.exe -m pytest -q

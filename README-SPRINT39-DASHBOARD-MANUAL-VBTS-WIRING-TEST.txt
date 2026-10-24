HISSE ROBOTU - SPRINT 39 DASHBOARD MANUEL VBTS BAGLANTI TESTI

ZIP'i doğrudan şu klasöre ayıklayın:
D:\Projects\Hisse-Robotu

Eklenen dosya:
backend\tests\test_dashboard_manual_vbts_wiring.py

Test:
python -m pytest .\backend\tests\test_dashboard_manual_vbts_wiring.py -q

Beklenen ilk sonuç:
3 failed

Amaç:
- Dashboard yeni VBTS kaynak fabrikasını import etmeli.
- Eski KAP tarama fabrikası doğrudan kullanılmamalı.
- Toplu Tarama yeni build_dashboard_market_scanner çağrısıyla başlamalı.

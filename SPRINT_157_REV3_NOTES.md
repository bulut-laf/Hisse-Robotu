# Sprint-157 Rev3 — Seans Öncesi Bağlam Görsel Girdi Desteği

## Rev3 uyumluluk düzeltmesi

Rev2'nin wrapper yaklaşımı doğru çalıştı ancak tam regresyonda eski
`test_sprint137e2_dashboard_wiring.py` testi, `backend/dashboard.py`
içindeki orijinal import satırının aynen kalmasını bekledi.

Rev3 bu eski sözleşmeyi korur:

- Orijinal import satırı aynen kalır:
  `from backend.app.ui.market_context_dashboard import render_market_context_dashboard`
- Sprint-157 wrapper ayrı bir alias ile import edilir.
- Hemen ardından `render_market_context_dashboard` adı wrapper alias'ına yönlendirilir.
- Seans Öncesi Bağlam route kodu değiştirilmez.
- `market_context_dashboard.py` yine hiç değiştirilmez.

Bu sayede hem eski Sprint-137E2 wiring testi hem de Sprint-157 görsel girdi
katmanı aynı anda korunur.

## Görsel akışı

1. JPG/JPEG/PNG yüklenir.
2. Dosya uzantısı, MIME türü ve gerçek dosya imzası doğrulanır.
3. Orijinal görsel SHA-256 kimliğiyle arşivlenir.
4. Kullanıcı isterse Gemini ile yalnız metin çıkarımı yapılır.
5. Metin kullanıcı tarafından kontrol edilir/düzeltilir.
6. Kullanıcı açıkça onayladıktan sonra onaylı metin gösterilir.
7. Onaylı metin mevcut `Metin Yapıştır` akışıyla normal biçimde kaydedilir.

## Değiştirilmeyenler

- `backend/app/ui/market_context_dashboard.py`
- mevcut Metin/TXT/PDF parser ve kayıt zinciri
- Haber Merkezi
- teknik skor / AL-SAT karar motoru
- Gölge Portföy / Aktif Trader

# Sprint-136 Rev1 — Dayanıklı Toplu Replay + İlerleme Göstergesi

## Sorun
29.06.2026–29.07.2026 toplu tarama uzun süre koştu, ekranda yalnız spinner görüldü ve sonuç alınamadı.

## Düzeltmeler
- Aynı MomentumWalkForwardService örneği bütün günlerde yeniden kullanılır.
- Her gün için `x/y · YYYY-MM-DD çalışıyor` gösterilir.
- Tamamlanan gün için aday sayısı ve süre gösterilir.
- Bir gün hata verirse toplu işlem tamamen kaybolmaz; sonraki güne geçilir.
- Hatalı günler ayrı CSV olarak indirilebilir.
- Başarılı günlerin birleşik CSV'si korunur.
- İsteğe bağlı günlük ZIP desteği devam eder.

## Not
Bu sprint servis düzeyinde yeniden kullanım sağlar. MomentumWalkForwardService'in iç veri katmanı
ayrıca gün bazında yeniden ağ erişimi yapıyorsa, sonraki performans ölçümüne göre daha derin veri-cache
optimizasyonu yapılabilir. Ölçmeden mevcut analiz mantığı değiştirilmez.

## Rev1 regresyon düzeltmesi
Sprint-135'in public entegrasyon sözleşmesi geri getirildi:
- `momentum_batch_scan_day`
- `render_momentum_batch_history_panel`
- `render_batch_historical_export_panel` import yüzeyi

Sprint-136'nın `ReusableMomentumBatchScanner` ve dayanıklı/ilerlemeli toplu replay özellikleri aynen korunur.

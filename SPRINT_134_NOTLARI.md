# Sprint-134 — Toplu Tarihsel Export UI + Replay Adapter

## Amaç
Sprint-133 toplu export motorunu Streamlit'te kullanılabilir hale getirmek ve
mevcut tek-gün replay servisini toplu çalıştırmaya bağlamak.

## Yeni dosyalar
- backend/app/history/replay_batch_adapter.py
- backend/app/ui/batch_historical_export_ui.py
- backend/tests/test_replay_batch_adapter.py
- backend/tests/test_batch_historical_export_ui.py

## Streamlit paneli
- Başlangıç tarihi
- Bitiş tarihi
- Evren: BIST100 / BIST Tüm
- Toplu tarihsel taramayı başlat
- Birleşik CSV indir
- İsteğe bağlı günlük CSV ZIP indir
- İşlenen gün ve toplam satır metrikleri

## Entegrasyon sözleşmesi
Mevcut tek günlük tarihsel replay fonksiyonu şu biçime adapte edilir:
`scan_day(cut_date, universe) -> export satırları`

`ReplayBatchAdapter` mevcut runner'a bu köprüyü sağlar.

## Güvenlik
Ana dashboard/live_analysis_dashboard dosyası mevcut güncel içeriği görülmeden otomatik
yamalanmamıştır. Böylece çalışan üretim arayüzünde kayma/yapıştırma riski oluşturulmaz.
Bir sonraki adımda güncel UI dosyası üzerinden tek dosyalık güvenli bağlantı yapılabilir.

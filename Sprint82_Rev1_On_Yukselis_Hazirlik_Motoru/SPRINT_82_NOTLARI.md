# Sprint-82 Rev1 — Ön Yükseliş Hazırlık Motoru

## Kapsam

Bu paket yalnızca hesaplama motorunu ve birim testlerini ekler.

- OHLCV veri doğrulama
- ATR ve fiyat aralığı sıkışması
- EMA9/EMA21/EMA50 trend hazırlığı
- RSI ve MACD histogram momentum hazırlığı
- Kontrollü hacim birikimi
- 20 günlük dirence uzaklık
- Yükselen dip kontrolü
- İlk risk/ödül tahmini
- Geç giriş ve hareket başlamış filtresi
- 0–100 bileşenli hazırlık skoru
- E1–E4 aşama sınıflandırması

## Bu sprintte yok

- Streamlit ekranı
- Tarihsel yeniden oynatma
- Otomatik kayıt
- PDF/CSV raporu
- Sektör/endeks göreceli güç veri bağlantısı
- Güncel tarama menüsüne entegrasyon

## Güvenlik

Yüksek son gün veya üç günlük prim, aşırı EMA21 uzaklığı, yüksek RSI ya da
kırılmış direnç durumunda hisse erken aday yapılmaz ve
`HAREKET_BASLAMIS` olarak ayrılır.

# Sprint-35 — BIST Momentum Keşif ve Erken Uyarı Motoru

## Hedef

BIST evrenindeki güçlü prim potansiyeli oluşmaya başlayan hisseleri, yalnızca mevcut “Al/Sat” durumunu beklemeden erken aşamada bulmak.

## Ana değişiklikler

- Momentum Keşif ekranı
- 100 puanlık kesitsel momentum modeli
- A/B/C/D sınıflandırması
- Göreceli güç, fiyat ivmesi, hacim, sıkışma, kırılım, trend, likidite ve risk puanları
- İlk görülme tarihi, listede gün ve ilk görülmeden getiri
- Özel Liste kullanıcı deneyimi düzeltmesi
- UTF-8 BOM temizleme

## Kullanım ilkesi

A/B/C sınıfları araştırma ve doğrulama listesidir. Nihai karar Güncel Teknik Analiz, risk/getiri ve pozisyon planı üzerinden verilir. D sınıfı peşinden koşulmaması gereken aşırı uzamış hisseleri ayırır.

## Doğrulama

- 565/565 otomatik test başarılı.
- Sprint-35 sistem kontrolü momentum keşif zincirini sentetik veride doğrular.

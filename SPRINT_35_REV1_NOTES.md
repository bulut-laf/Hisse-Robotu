# Sprint-35 Rev1 — Kırılım Öncesi Erken Uyarı

## Amaç

GRSEL benzeri güçlü hareketleri yalnızca kırılım gerçekleştikten sonra değil, sıkışma, hacim birikimi ve direnç yaklaşımı aşamalarında araştırma adayı olarak göstermek.

## Yeni sınıflar

- E0 — Sıkışma Oluşuyor
- E1 — Hacim Birikimi Başladı
- E2 — Dirence Yaklaşıyor
- E3 — Kırılım Öncesi Erken Uyarı
- B — Kırılım Başladı
- C — İşleme Hazır Aday
- D — Aşırı Yükselmiş

## Yeni ölçümler

Yakın direnç, dirence uzaklık, göreceli güç eğimi, hacim eğimi, RSI eğimi, MACD histogram eğimi, ATR/fiyat sıkışması ve yakın EMA kesişimi.

## Tarihsel yeniden oynatma

Kesim tarihinden sonraki veriler sinyal üretiminden gizlenir. Adayların sonraki 5, 10 ve 20 günlük getirileri ile azami olumlu/ters hareketleri sonradan ölçülür.

## Doğrulama

- 571 otomatik test başarılı.
- 18 sistem kontrolü başarılı.
- 165 Python dosyası sözdizimi kontrolünden geçti.

# Sprint-114 — Günlük Aday Kalitesi ve Gerçek Erken Yakalama Performansı

## Amaç
E2–E4 canlı adaylarının gerçekten erken yakalanıp yakalanmadığını, aday üretim motorunu veya eşikleri değiştirmeden ölçmek.

## Eklenenler
- Aşama bazlı E2/E3/E4 kalite raporu.
- Tetiklenme oranı ve ortalama tetiklenme seansı.
- İlk 3 işlem seansında tetiklenme için ayrı erken-yakalama oranı.
- 20 günlük gerçek sonuçlardan başarı ve yanlış pozitif oranı.
- Ortalama 20G kapanış getirisi ve dönem içi en yüksek hareket.
- Minimum örneklem kilidi; yeterli ölçüm yoksa kesin kalite hükmü verilmez.

## Güvenlik
- Yeni indikatör yoktur.
- Aday üretim eşikleri değiştirilmez.
- Yalnız daha önce dondurulmuş canlı sinyal/yaşam döngüsü/performans kayıtları okunur.
- Gelecek veri aday üretimine geri beslenmez.

## Sonraki hedef
Sprint-115 — Kaçırılan fırsat analizi: seçilmeyen fakat sonradan güçlü yükselen hisselerin hangi filtre nedeniyle dışarıda kaldığını ölçmek.

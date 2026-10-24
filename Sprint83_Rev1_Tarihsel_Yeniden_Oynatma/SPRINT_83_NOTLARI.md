# Sprint-83 Rev1 — Ön Yükseliş Tarihsel Yeniden Oynatma

Eklenen yetenekler:

- Kesim tarihinden sonraki verileri aday analizinden ayırma
- 1/3/5/10/20 işlem günü ileri performans ölçümü
- Ufuk sonu kapanış getirisi
- Dönem içi en yüksek getiri
- Dönem içi en düşük getiri
- Eksik ileri dönem verisini güvenli işaretleme
- Toplu performans özeti
- DataFrame rapor dönüşümü
- Look-ahead bias regresyon testleri

Kritik kural:

Kesim tarihinden sonraki fiyatlar aday üretiminde kullanılmaz.
Bu fiyatlar yalnızca sonradan performans ölçümü için kullanılır.

Bu sprintte henüz yok:

- Streamlit ekranı
- BIST 100 toplu tarihsel tarama yöneticisi
- CSV/PDF dışa aktarma düğmeleri
- Otomatik eşik kalibrasyonu

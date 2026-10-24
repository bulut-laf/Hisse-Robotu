# Sprint-65 Rev1 — Temel Analiz Rapor Arşivi

Eklenenler:
- Temel analiz raporlarının yerel JSON arşivine kaydedilmesi
- Şirket, dönem ve oluşturulma zamanı içeren rapor kimliği
- Rapor içeriğinden SHA-256 veri kimliği oluşturulması
- Aynı veri kimliğinin mükerrer kaydedilmemesi
- Finansal veri değiştiğinde yeni rapor sürümü oluşturulması
- Şirket bazında geçmiş raporların yeniden eskiye listelenmesi
- Eski ve gelecek tarihli raporların dışlanması
- İki uyumlu rapor arasında toplam ve alt skor karşılaştırması
- Finansal oran, sektör sırası, sektör gücü, kaynak ve tazelik karşılaştırması
- Farklı şirket veya para birimindeki raporların karşılaştırılmaması
- Arşiv karşılaştırmasının alım/satım tavsiyesi üretmemesi

Teknik skor, BIST taraması ve VBTS güvenlik kilidi değiştirilmemiştir.

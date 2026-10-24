# Sprint-59 Rev1 — Temel Skor Deposu

Eklenenler:
- Temel kalite skorlarının JSON depoya kaydedilmesi
- Şirket ve bilanço dönemi bazlı kayıt anahtarı
- Finansal dönemlerden üretilen veri kimliği
- Aynı veri ve skor için tekrar kayıt yapılmaması
- Finansal veri değişirse skor kaydının güncellenmesi
- Eski bilanço dönemine ait kayıtlı skorun kullanılmaması
- BIST Toplu Tarama'da kayıtlı skorların otomatik okunması
- Her taramada CSV/JSON yükleme zorunluluğunun kaldırılması
- İsteğe bağlı dosya yükleme ile kayıtlı skorları güncelleme
- Teknik skor ile temel skorun ayrı kalması
- Temel filtre varsayılanının kapalı kalması
- Filtrelenmiş aday listesinin ayrıntı seçiminde kullanılması

Depo:
backend/data/fundamental_scores.json

Temel kalite skoru alım/satım sinyali değildir.
VBTS kilidi davranışı değiştirilmemiştir.

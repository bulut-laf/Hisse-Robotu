# Sprint-61 Rev1 — Finansal Oran ve Sektör Referansı

Eklenenler:
- Kullanıcı tarafından sağlanan symbol/sector referans CSV desteği
- İsteğe bağlı market_cap ile F/K ve PD/DD hesaplama
- Cari oran, borç/özsermaye, ROE, net kâr marjı ve serbest nakit akışı marjı karşılaştırması
- Aynı sektör, aynı dönem ve aynı para birimindeki şirketlerin medyanı
- Şirketin sektör medyanına göre tarafsız konum bilgisi
- Eski bilanço kayıtlarının güvenli biçimde dışlanması
- Eksik piyasa değeri veya negatif kâr durumunda değerleme oranının boş bırakılması
- Sektör veya piyasa değerinin tahmin edilmemesi
- Oran karşılaştırmasının alım/satım sinyali üretmemesi

Not:
- F/K ve PD/DD yalnızca market_cap sütunu sağlanırsa hesaplanır.
- Sektör eşlemesi sistem tarafından tahmin edilmez.
- Mevcut temel skor geçmişi, teknik skor, BIST taraması ve VBTS güvenlik davranışı değiştirilmemiştir.

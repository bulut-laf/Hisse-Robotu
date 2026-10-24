# Sprint-155 — Aktif Gölge Portföy / Trader Pozisyon Yönetimi

## Amaç

Gölge Portföyü pasif "al ve bekle" izleme mantığından çıkarıp kısa vadeli trader simülasyonuna uygun aktif pozisyon yönetimiyle desteklemek.

## Eklenenler

- Manuel gün içi fiyat girişi.
- İlk stopu değiştirmeden ayrı aktif stop durumu.
- R bazlı deterministik stop yönetimi:
  - 1.0R: başa baş stopu,
  - 1.5R: kâr koruma stopu,
  - 2.0R+: yüksek su seviyesine bağlı trailing stop.
- Yükseltilmiş stopun aşağı indirilememesi.
- Teknik görünüm için manuel Pozitif / Nötr / Bozuldu işareti.
- Haber riski için Yok / İzle / Yüksek işareti.
- Varsayılan 5 günlük zaman değerlendirmesi; yeterli ilerleme yoksa çıkış incelemesi.
- TUT / İZLE / ÇIKIŞI DEĞERLENDİR / STOP-ÇIKIŞ sonuçları.
- Kullanıcı onayıyla mevcut manuel fiyat üzerinden Gölge Portföy pozisyonunu kapatma.
- Ayrı kalıcı trader durumu ve JSONL gözlem/audit geçmişi.

## Güvenlik

- Gerçek emir gönderilmez.
- Otomatik pozisyon kapatma yapılmaz; çıkış kullanıcı düğmesiyle onaylanır.
- Stop veya hedef yoksa sistem yeni teknik seviye uydurmaz.
- Orijinal Gölge Portföy veri modeli ve geçmiş kayıtlar değiştirilmez.
- Haber Merkezi ve teknik skor motoru değiştirilmez.
- Canlı veri varsayılmaz; gün içi fiyat kullanıcı tarafından manuel girilir.

## Veri konumu

`~/.hisse_robotu/active_shadow_trader/`

- `state.json`: aktif stop ve yüksek su seviyesi.
- `observations.jsonl`: trader değerlendirme audit izi.

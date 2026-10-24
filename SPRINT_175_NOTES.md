# Sprint-175 — Kaynak Besleme Arayüzü Konsolidasyonu

Amaç: Yedi kontrollü resmî kaynak adapterinin Streamlit önizleme ve arşivleme
akışını tek ortak UI renderer altında toplamak.

## Neden?

Sprint-173 ortak HTTP/güvenlik çekirdeğini merkezileştirdi.
Sprint-174 adapter sağlık/tanılama katmanını ekledi.

Buna rağmen `news_center_dashboard.py` içinde KAP, TCMB, TÜİK, SPK, HMB,
Borsa İstanbul ve Resmî Gazete için aynı akış ayrı ayrı tekrar ediyordu:

- URL alanı
- ağ onayı
- önizleme düğmesi
- adapter fetch
- dry-run
- duplicate görünümü
- açık arşivleme düğmesi
- session-state önizlemesi
- URL değişikliği koruması
- başarı/hata mesajları

Bu tekrar UI bakım ve girinti regresyonu riskini artırıyordu.

## Yeni yapı

`backend/app/ui/official_source_feed_renderer.py`

- `OfficialSourceFeedUiSpec`
- `OFFICIAL_SOURCE_FEED_UI_SPECS`
- `_render_source_feed_block(...)`
- `render_official_source_feed_blocks(...)`

Yedi kaynak aynı ortak rendererı kullanır. Kaynağa özgü olarak yalnız:

- adapter sınıfı
- adapter hata tipi
- başlık/açıklama
- URL etiketi ve örneği
- buton/metinler
- preview summary formatı

metadata olarak tutulur.

## Değişmeyen güvenlik

- Adapter backend sınıfları değişmez.
- Kaynak-özel URL whitelist/parser/redirect kuralları değişmez.
- Ağ varsayılan kapalı.
- Her fetch için açık kullanıcı onayı gerekir.
- Dry-run zorunlu.
- Arşivleme ayrıca açık düğme ister.
- Duplicate koruması sürer.
- URL önizlemeden sonra değiştirilirse arşivleme öncesi yeni preview gerekir.
- Otomatik polling/toplu scraping/arka plan taraması yok.
- Yeni skor, fiyat yönü, AL/SAT, teknik skor veya AI yorumu yok.

## Mimari sonuç

`news_center_dashboard.py` artık yedi adapter sınıfını doğrudan import etmez ve
yedi ayrı kaynak besleme bloğunu taşımaz. Dashboard tek bir
`render_official_source_feed_blocks(...)` çağrısıyla kaynak besleme UI'sını açar.

Bu sprint davranış değiştiren bir özellik değil; UI bakım ve regresyon riskini
azaltan bir konsolidasyondur.

# Sprint-115 — Kaçırılan Fırsat Analizi ve Filtre Etkisi

## Amaç
Sistem tarafından seçilmeyen fakat kesim tarihinden sonra güçlü yükseliş yapan hisseleri post-hoc analiz etmek ve hangi filtrenin bu fırsatları elediğini ölçmek.

## Eklenenler
- Seçilmeyen kararlar için 20 işlem günlük güçlü hareket tespiti.
- Varsayılan güçlü hareket eşiği: dönem içi en yüksek fiyat hareketi >= %10.
- Eksik 20 seans verisi ölçüm oranlarından dışlanır.
- Elenme nedenleri: Momentum, RSI eğimi, MACD histogram eğimi, Aşama kapısı, Veri eksikliği, Diğer/Bilinmiyor.
- Filtre bazında reddedilen örnek sayısı, kaçırılan güçlü hareket sayısı ve kaçırma oranı.
- Yeterli adet + yeterli oran şartıyla yalnız “potansiyel fazla sert” etiketi; otomatik eşik değişikliği yoktur.
- Kaçırılan fırsat ve filtre etkisi için iki ayrı tablo.

## Güvenlik
- Gelecek fiyatlar yalnız sonradan performans ölçümü için kullanılır.
- Aday üretim motoru veya mevcut eşikler değiştirilmez.
- Veri eksikliği “fazla sert filtre” sayılmaz.
- Yetersiz örneklemde eşik değişikliği hakkında kesin hüküm verilmez.

## Sonraki hedef
Sprint-116 — Piyasa rejimine göre aday ve kaçırılan fırsat performansının karşılaştırılması.

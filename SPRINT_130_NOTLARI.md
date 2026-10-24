# Sprint-130 — Erken Radar + Olgunlaşma/Kâr Koruma Streamlit Görünümü

## Amaç
Sprint-129 karar çıktısını kullanıcı arayüzünde güvenli, ayrı ve test edilebilir bir panel olarak sunmak.

## Yeni UI bileşeni
`backend/app/prebreakout/prebreakout_early_radar_ui.py`

Panel iki bölümlüdür:
1. Erken Radar
2. Olgunlaşma / Kâr Koruma

## Görünen alanlar
- Hisse
- Erken Radar durumu
- Erken Fırsat Puanı
- Hareket Fazı
- Olgunlaşma durumu
- Yeni giriş mesajı
- Mevcut pozisyon mesajı
- Gerekçeler

## Mimari güvenlik
- Ana teknik skor değiştirilmez.
- Ana aday sıralaması değiştirilmez.
- Erken Radar ile Kâr Koruma adayları aynı listede karıştırılmaz.
- UI modülü karar motorundan gevşek bağlıdır.
- Mevcut büyük Streamlit ekran dosyalarına doğrudan riskli yama yapılmaz.

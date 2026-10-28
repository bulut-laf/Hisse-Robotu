# Hisse Robotu — Fon Araştırma Sprint 2

## Amaç
Kaynağı doğrulanmış NAV serilerinden temel performans ölçümleri ve bilinen ücret oranlarından şeffaf yıllık maliyet hesabı üretmek.

## İçerik
- Toplam getiri ve tarih aralığına dayalı yıllıklandırılmış getiri.
- Gözlemler yeterliyse yıllıklandırılmış oynaklık.
- NAV serisinden maksimum düşüş (max drawdown).
- Yatırılan tutara göre yıllık devam eden gider ve işlem maliyeti tahmini.
- Eksik maliyet alanı sıfır kabul edilmez; tahmin `None` ve `evidence_complete=False` döner.
- NAV verisi indirme/kanıt doğrulama, benchmark karşılaştırması, vergi, alım-satım spread'i ve döviz etkisi bu sprintin kapsamı dışındadır.

## Hedef test
`.\.venv\Scripts\python.exe -m pytest backend\tests\test_fund_research_sprint2.py -q`

## Kabul ölçütü
Hedef testler ve ardından tam regresyon başarılı olmalı. Performans ölçümleri yalnızca sağlanan NAV serisini temsil eder; farklı para birimi/sınıfı veya farklı tarih aralıkları doğrudan karşılaştırılmamalıdır.

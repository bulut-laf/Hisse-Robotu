# Sprint-177 — Günlük Haber Merkezi Operasyon Ekranı

Amaç: Haber Merkezi'nin günlük kullanımında gerekli mevcut bilgileri tek bir
çalışma masasında bir araya getirmek.

## Yeni sekme

Haber Merkezi sekmelerinin başına `Günlük Operasyon` eklenir.
Bu ekran ayrıntılı sekmelerin yerine geçmez; hızlı günlük kontrol noktasıdır.

## Gösterilen günlük metrikler

- piyasa olayı
- haber
- önem >=80 olay
- KAP olayı
- benzersiz hisse
- açık Gölge Portföy teması
- kullanılan resmî kaynak / toplam resmî kaynak
- kaynak operasyon sayısı
- kaynak operasyon hata sayısı
- Tier-1 / birincil haber sayısı
- en son arşivlenmiş yayın zamanı
- en son başarılı kaynak kullanım zamanı

## Günün öncelikli olayları

En fazla 10 olay mevcut önem skoru, Tier-1 haber sayısı, haber sayısı ve olay
zamanına göre deterministik olarak sıralanır. Yeni bir skor üretilmez.

## Resmî kaynak günlük görünümü

Yedi resmî kaynak için günlük haber, operasyon, başarılı/hatalı önizleme,
onay engeli, başarılı arşivleme, duplicate, arşiv hatası ve son başarılı kullanım
gösterilir. Tablo yeni ağ isteği göndermez.

## Portföy

Açık Gölge Portföy teması yalnız olayların mevcut `symbols` alanıyla açık
pozisyonların kesişimidir. Fiyat yönü veya işlem önerisi değildir.

## Değişmeyen sınırlar

- Yeni birleşik haber skoru yok.
- Yeni fiyat yönü yok.
- AL/SAT yok.
- Teknik skor değişikliği yok.
- AI yorumu yok.
- Otomatik polling yok.
- Toplu scraping yok.
- Arka plan taraması yok.
- Mevcut ayrıntılı Haber Merkezi sekmeleri korunur.

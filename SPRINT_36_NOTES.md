# Sprint-36 — İşlem Kayıp Analizi ve Güvenlik Kilidi

Bu sürüm, geçmiş zararları görünür kılmak ve yeni işlemlerde temel risk kurallarını zorunlu bir ön kontrolden geçirmek için hazırlanmıştır.

## Ana özellikler

- Gerçek/deneme işlem günlüğü
- Manuel kayıt ve CSV aktarımı
- Kayıp nedeni teşhisi
- Günlük/haftalık zarar ve ardışık zarar takibi
- Stop, risk/getiri, risk yüzdesi ve pozisyon büyüklüğü kilitleri
- Kaybedene ekleme ve aşırı yükselmiş giriş engeli

## Veri sınırı

Sistem aracı kurumdan otomatik işlem geçmişi çekmez. Sonuçlar yalnızca kullanıcının girdiği tamamlanmış işlemler kadar doğrudur.

## Güvenlik sınırı

Bu mod kayıpları geri kazanmayı veya gelecek işlemlerde kâr etmeyi garanti etmez. Yeni işlem ön kontrolü emir göndermez; yalnızca tanımlı disiplin kurallarını uygular.

# Sprint-74 Rev3

Düzeltme:
- Sistem kontrolü başarılı biçimde exit code 0 döndürmesine rağmen,
  Windows konsol kodlaması Türkçe karakterleri bozduğu için kapanış betiği
  metin eşleşmesinde yanlış hata veriyordu.
- Yerelleştirilmiş konsol metni artık ayrıştırılmıyor.
- Sistem kontrolünün başarı ölçütü süreç çıkış kodudur.
- Test, regresyon, compileall, snapshot, SHA-256 ve release JSON adımları
  değiştirilmedi.

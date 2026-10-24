# Sprint-53

Gerçek ikincil kaynak: Alpha Vantage günlük CSV.

PowerShell:
$env:HISSE_ROBOTU_ALPHA_VANTAGE_API_KEY = "API_KEY"

İsteğe bağlı sembol eşleme:
$env:HISSE_ROBOTU_ALPHA_VANTAGE_SYMBOL_MAP = '{"XU100.IS":"PROVIDER_SYMBOL"}'

API anahtarı veya geçerli sembol eşlemesi yoksa ikincil kaynak başarısız sayılır.
Sistem yalnızca güncel ve bütünlüğü doğrulanmış yerel önbelleği kullanır.
Eski önbellek analiz üretmez.

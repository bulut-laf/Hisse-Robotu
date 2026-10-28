import os
import time
import logging
from pathlib import Path

# Log ayarları (daily_update_job ile aynı dosyaya yazıyoruz)
log_file_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'daily_operations.log')
logging.basicConfig(filename=log_file_path, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def clean_old_files(directory_path: str, days: int = 30):
    """Belirtilen dizindeki eski dosyaları (PDF, JSON, CSV önbellekleri) temizler."""
    if not os.path.exists(directory_path):
        return

    now = time.time()
    cutoff = now - (days * 86400) # Gün sayısını saniyeye çevir
    deleted_count = 0

    for root, _, files in os.walk(directory_path):
        for file in files:
            file_path = os.path.join(root, file)
            try:
                if os.path.getmtime(file_path) < cutoff:
                    os.remove(file_path)
                    deleted_count += 1
            except Exception as e:
                logging.warning(f"Dosya silinemedi: {file_path} - {str(e)}")
    
    if deleted_count > 0:
        logging.info(f"{directory_path} dizininden {days} günden eski {deleted_count} gereksiz dosya temizlendi.")

def run_maintenance():
    logging.info("--- VERTABANI VE NBELLEK BAKIMI BAŞLADI ---")
    
    base_dir = Path(__file__).resolve().parent.parent.parent.parent
    
    # Temizlenecek potansiyel geçici dizinler
    cache_dir = base_dir / "backend" / "data" / "cache"
    temp_dir = base_dir / "backend" / "data" / "temp_pdfs"
    
    clean_old_files(str(cache_dir), days=30)
    clean_old_files(str(temp_dir), days=7) # PDF'ler çok yer kaplar, 7 günde bir temizle
    
    # Log dosyasının boyutunu kontrol et (5MB'ı geçerse sıfırla)
    if os.path.exists(log_file_path) and os.path.getsize(log_file_path) > 5 * 1024 * 1024:
        with open(log_file_path, 'w', encoding='utf-8') as f:
            f.write("--- LOG DOSYASI BOYUT SINIRI NEDENYLE SIFIRLANDI ---\n")
        logging.info("Log dosyası boyutu 5MB'ı aştığı için başarıyla kırpıldı.")
        
    logging.info("--- BAKIM VE TEMZLK KUSURSUZ TAMAMLANDI ---")

if __name__ == "__main__":
    run_maintenance()
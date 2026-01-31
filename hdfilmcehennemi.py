import cloudscraper # requests yerine bunu kullanıyoruz
from bs4 import BeautifulSoup
import json
import time
import re
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from urllib.parse import urljoin

# ============================================================================
# AYARLAR - 451 HATASINI AŞMAK İÇİN
# ============================================================================
# ÖNEMLİ: Tarayıcıda açılan GÜNCEL adresi buraya yazın (Örn: hdfilmcehennemi.tv vb.)
BASE_URL = "https://www.hdfilmcehennemi.com" 
PAGES_TO_SCRAPE = int(sys.argv[1]) if len(sys.argv) > 1 else 5
MAX_WORKERS = 3 # 451 hatası almamak için hızı düşürdük

# Cloudscraper nesnesi oluştur (Bot korumasını taklit eder)
scraper = cloudscraper.create_scraper(
    browser={
        'browser': 'chrome',
        'platform': 'windows',
        'desktop': True
    }
)

data_lock = Lock()

def slugify(text):
    tr_map = str.maketrans("ığüşöç", "igusoc")
    text = text.lower().translate(tr_map)
    return re.sub(r'[^a-z0-9]', '-', text).strip('-')

def process_page(page_num, filmler_data):
    # API yolu değişmiş olabilir, tarayıcıdan kontrol edilmeli
    api_url = f"{BASE_URL}/load/page/{page_num}/categories/film-izle-2/"
    
    try:
        # Standart requests yerine scraper.get kullanıyoruz
        response = scraper.get(api_url, timeout=20)
        
        if response.status_code == 451:
            print(f"❌ Sayfa {page_num}: Mahkeme kararıyla engelli (VPN gerekebilir veya URL güncel değil).")
            return 0
        
        if response.status_code != 200:
            print(f"❌ Sayfa {page_num} Hatası: {response.status_code}")
            return 0

        data = response.json()
        soup = BeautifulSoup(data.get('html', ''), 'html.parser')
        items = soup.select('a.poster')

        count = 0
        for item in items:
            film_adi = item.get('title') or "İsimsiz Film"
            film_link = urljoin(BASE_URL, item.get('href'))
            
            img = item.find('img')
            poster = img.get('data-src') or img.get('src') if img else ""

            film_id = slugify(film_adi)
            with data_lock:
                filmler_data[film_id] = {
                    "isim": film_adi,
                    "resim": poster,
                    "link": film_link # İlk aşamada direkt linki alıyoruz
                }
            count += 1
        
        print(f"✅ Sayfa {page_num}: {count} film çekildi.")
        return count

    except Exception as e:
        print(f"💥 Hata Sayfa {page_num}: {str(e)}")
        return 0

def main():
    print(f"🚀 Scraping Başladı: {BASE_URL}")
    all_films = {}
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(process_page, i, all_films) for i in range(1, PAGES_TO_SCRAPE + 1)]
        for f in as_completed(futures):
            f.result()

    with open("hdfilmcehennemi.json", "w", encoding="utf-8") as f:
        json.dump(all_films, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Tamamlandı! Toplam: {len(all_films)} film.")

if __name__ == "__main__":
    main()

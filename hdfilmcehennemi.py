import requests
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
# AYARLAR (Kendi Bilgisayarın İçin)
# ============================================================================
BASE_URL = "https://www.hdfilmcehennemi.nl"
PAGES_TO_SCRAPE = 10  # Kaç sayfa çekmek istiyorsan
MAX_WORKERS = 8       # Bilgisayarının hızına göre artırabilirsin

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": f"{BASE_URL}/"
}

data_lock = Lock()
session = requests.Session()

def slugify(text):
    tr_map = str.maketrans("ığüşöçİĞÜŞÖÇ", "igusocIGUSOC")
    return re.sub(r'[^a-z0-9]', '-', text.lower().translate(tr_map)).strip('-')

def process_page(sayfa, filmler_data):
    api_url = f"{BASE_URL}/load/page/{sayfa}/categories/film-izle-2/"
    try:
        response = session.get(api_url, headers=HEADERS, timeout=15)
        if response.status_code == 200:
            data = response.json()
            soup = BeautifulSoup(data.get('html', ''), 'html.parser')
            items = soup.select('a.poster')
            
            count = 0
            for a in items:
                isim = a.get('title') or a.text.strip()
                link = urljoin(BASE_URL, a.get('href'))
                img = a.find('img')
                resim = img.get('data-src') or img.get('src', '') if img else ""
                
                if resim.startswith("//"): resim = "https:" + resim

                film_id = slugify(isim)
                with data_lock:
                    filmler_data[film_id] = {
                        "isim": isim,
                        "resim": resim,
                        "link": link
                    }
                count += 1
            print(f"✅ Sayfa {sayfa}: {count} film eklendi.")
            return count
        else:
            print(f"❌ Sayfa {sayfa}: Hata {response.status_code}")
    except Exception as e:
        print(f"❌ Sayfa {sayfa} hatası: {e}")
    return 0

def main():
    print(f"🚀 Kendi Bilgisayarın Üzerinden Başlatıldı: {BASE_URL}")
    filmler_data = {}
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(process_page, i, filmler_data) for i in range(1, PAGES_TO_SCRAPE + 1)]
        for f in as_completed(futures):
            f.result()

    # JSON Olarak Kaydet
    with open("hdfilmcehennemi.json", "w", encoding="utf-8") as f:
        json.dump(filmler_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n✨ İŞLEM TAMAMLANDI! Toplam {len(filmler_data)} film.")
    print("GitHub'a yüklemek için hdfilmcehennemi.json dosyasını sürükle bırak yapabilirsin.")

if __name__ == "__main__":
    main()

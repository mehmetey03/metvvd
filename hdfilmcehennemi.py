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
# AYARLAR
# ============================================================================
BASE_URL = "https://www.hdfilmcehennemi.nl"
PAGES_TO_SCRAPE = int(sys.argv[1]) if len(sys.argv) > 1 else 10
MAX_WORKERS = 4 # Proxy kullanırken hızı düşürmek daha güvenlidir

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8",
    "Referer": "https://www.google.com/"
}

data_lock = Lock()

def slugify(text):
    tr_map = str.maketrans("ığüşöçİĞÜŞÖÇ", "igusocIGUSOC")
    return re.sub(r'[^a-z0-9]', '-', text.lower().translate(tr_map)).strip('-')

def process_page(sayfa, filmler_data):
    api_url = f"{BASE_URL}/load/page/{sayfa}/categories/film-izle-2/"
    
    # ÜCRETSİZ PROXY LİSTESİ (Çalışmazsa yenileriyle değiştirilmelidir)
    # GitHub 451 hatası veriyorsa tek çare budur.
    proxy_list = [
        "http://167.172.175.251:3128",
        "http://185.162.229.154:10005",
        "http://51.158.154.173:3128"
    ]

    for proxy_url in proxy_list:
        try:
            proxies = {"http": proxy_url, "https": proxy_url}
            # verify=False ekleyerek SSL hatalarını geçiyoruz
            response = requests.get(api_url, headers=HEADERS, proxies=proxies, timeout=15, verify=False)
            
            if response.status_code == 200:
                data = response.json()
                soup = BeautifulSoup(data.get('html', ''), 'html.parser')
                items = soup.select('a.poster')
                
                local_count = 0
                for a in items:
                    isim = a.get('title') or a.text.strip()
                    link = urljoin(BASE_URL, a.get('href'))
                    img = a.find('img')
                    resim = img.get('data-src') or img.get('src', '') if img else ""
                    
                    film_id = slugify(isim)
                    with data_lock:
                        filmler_data[film_id] = {
                            "isim": isim,
                            "resim": resim,
                            "link": link
                        }
                    local_count += 1
                
                print(f"✅ Sayfa {sayfa}: {local_count} film (Proxy: {proxy_url})")
                return local_count
            
            elif response.status_code == 451:
                print(f"⚠️ Sayfa {sayfa}: Proxy {proxy_url} da engelli çıktı.")
                continue

        except Exception as e:
            continue
            
    print(f"❌ Sayfa {sayfa}: Hiçbir proxy ile erişilemedi.")
    return 0

def main():
    print(f"🚀 Proxy Destekli Tarama Başladı: {BASE_URL}")
    filmler_data = {}
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(process_page, i, filmler_data) for i in range(1, PAGES_TO_SCRAPE + 1)]
        for f in as_completed(futures):
            f.result()

    with open("hdfilmcehennemi.json", "w", encoding="utf-8") as f:
        json.dump(filmler_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n✨ Bitti! Toplam {len(filmler_data)} film kaydedildi.")

if __name__ == "__main__":
    main()

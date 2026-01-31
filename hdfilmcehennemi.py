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
# AYARLAR VE SABİTLER (GÜNCEL)
# ============================================================================
PAGES_TO_SCRAPE = int(sys.argv[1]) if len(sys.argv) > 1 else 10
# SİTE ADRESİ BURADAN GÜNCELLENDİ
BASE_URL = "https://www.hdfilmcehennemi.nl" 
GITHUB_JSON_URL = "https://raw.githubusercontent.com/mehmetey03/metvvd/refs/heads/main/hdfilmcehennemi.json"

# Daha zengin ve insansı Header
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": f"{BASE_URL}/"
}

MAX_WORKERS = 8  
data_lock = Lock()
session = requests.Session()

# ============================================================================
# YARDIMCI FONKSİYONLAR
# ============================================================================

def slugify(text):
    tr_map = str.maketrans("ığüşöçİĞÜŞÖÇ", "igusocIGUSOC")
    text = text.lower().translate(tr_map)
    text = re.sub(r'[^a-z0-9]', '-', text)
    return re.sub(r'-+', '-', text).strip('-')

def get_video_link(film_url):
    """Film sayfasının içine girip asıl player linkini çeker"""
    try:
        res = session.get(film_url, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            soup = BeautifulSoup(res.content, "html.parser")
            iframe = soup.find('iframe', {'class': 'close'})
            if iframe:
                raw = iframe.get('data-src') or iframe.get('src')
                if "rapidrame_id=" in raw:
                    rid = raw.split("rapidrame_id=")[1].split("&")[0]
                    return f"{BASE_URL}/rplayer/{rid}"
                return raw
    except:
        pass
    return film_url

def process_page(sayfa, filmler_data):
    # Sitenin AJAX yükleme yolu
    api_url = f"{BASE_URL}/load/page/{sayfa}/categories/film-izle-2/"
    
    try:
        response = session.get(api_url, headers=HEADERS, timeout=15)
        
        if response.status_code == 451:
            print(f"⚠️ Sayfa {sayfa}: Erişim Engeli (451) - IP engellenmiş olabilir.")
            return 0
        
        if response.status_code != 200:
            return 0

        data = response.json()
        soup = BeautifulSoup(data.get('html', ''), 'html.parser')
        items = soup.select('a.poster')

        count = 0
        for item in items:
            isim = item.get('title') or "İsimsiz Film"
            link = urljoin(BASE_URL, item.get('href'))
            
            img = item.find('img')
            resim = ""
            if img:
                resim = img.get('data-src') or img.get('src', '')
                if resim.startswith("//"): resim = "https:" + resim
                if "?" in resim: resim = resim.split("?")[0]

            film_id = slugify(isim)
            with data_lock:
                filmler_data[film_id] = {
                    "isim": isim,
                    "resim": resim if resim else "https://via.placeholder.com/300x450",
                    "link": link # Daha hızlı olması için şimdilik sayfa linkini alıyoruz
                }
            count += 1
        
        print(f"✅ Sayfa {sayfa}: {count} film bulundu.")
        return count

    except Exception as e:
        print(f"❌ Sayfa {sayfa} hatası: {e}")
        return 0

# ============================================================================
# ANA ÇALIŞTIRICI
# ============================================================================

def main():
    print(f"🚀 Turbo Mod Başlatıldı: {BASE_URL}")
    filmler_data = {}
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(process_page, i, filmler_data) for i in range(1, PAGES_TO_SCRAPE + 1)]
        for f in as_completed(futures):
            f.result()

    # JSON Kaydet
    with open("hdfilmcehennemi.json", "w", encoding="utf-8") as f:
        json.dump(filmler_data, f, ensure_ascii=False, indent=2)

    total_time = time.time() - start_time
    print(f"\n✨ İşlem Tamamlandı: {len(filmler_data)} film | {total_time:.2f} sn")

    # Buradan sonra senin HTML oluşturma fonksiyonunu ekleyebilirsin
    # ...

if __name__ == "__main__":
    main()

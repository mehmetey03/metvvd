import requests
from bs4 import BeautifulSoup
import json
import time
import re
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

# ============================================================================
# AYARLAR
# ============================================================================
BASE_URL = "https://www.hdfilmcehennemi.com"
# Yeni URL yapısı: Sayfalar artık doğrudan kategori URL'si üzerinden yürüyor
PAGES_TO_SCRAPE = 5 
MAX_WORKERS = 10

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Referer": BASE_URL
}

filmler_data = {}
data_lock = Lock()
session = requests.Session()
session.headers.update(HEADERS)

def slugify(text):
    tr_map = str.maketrans("ığüşöç", "igusoc")
    text = text.lower().translate(tr_map)
    return re.sub(r'[^a-z0-9]', '-', text).strip('-')

def get_video_link(film_url):
    try:
        resp = session.get(film_url, timeout=10)
        soup = BeautifulSoup(resp.content, "html.parser")
        # Site Rapidrame veya benzeri bir iframe kullanıyor
        iframe = soup.select_one('iframe[data-src*="rapid"], iframe.close')
        if iframe:
            src = iframe.get('data-src') or iframe.get('src')
            if "rapidrame_id=" in src:
                return f"{BASE_URL}/rplayer/{src.split('rapidrame_id=')[1].split('&')[0]}"
            return src
    except:
        pass
    return ""

def process_page(page_num):
    # Sitenin yeni sayfa yapısı genellikle /page/2/ şeklinde ana dizindedir
    url = f"{BASE_URL}/page/{page_num}/"
    print(f"🔎 Sayfa {page_num} taranıyor...")
    
    try:
        response = session.get(url, timeout=15)
        soup = BeautifulSoup(response.content, "html.parser")
        
        # Güncel seçici: Sitedeki film kartlarını bulur
        items = soup.select('div.poster-container a, a.poster, article.post a')
        
        page_results = []
        for a in items:
            title = a.get('title') or (a.find('img').get('alt') if a.find('img') else "")
            link = a.get('href')
            img = a.find('img')
            
            if title and link and link.startswith('http'):
                poster = img.get('data-src') or img.get('src') or ""
                page_results.append({
                    'film_adi': title.strip(),
                    'film_link': link,
                    'poster_url': poster.split('?')[0]
                })
        return page_results
    except Exception as e:
        print(f"❌ Sayfa {page_num} hatası: {e}")
        return []

def main():
    start_time = time.time()
    all_links = []

    # 1. Aşama: Linkleri Topla
    for p in range(1, PAGES_TO_SCRAPE + 1):
        links = process_page(p)
        all_links.extend(links)
    
    # Tekilleştirme (Duplicate prevention)
    unique_links = {v['film_link']: v for v in all_links}.values()
    print(f"✅ {len(unique_links)} benzersiz film bulundu. Detaylar çekiliyor...")

    # 2. Aşama: Video Linklerini Çek (Paralel)
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_film = {executor.submit(get_video_link, f['film_link']): f for f in unique_links}
        
        for future in as_completed(future_to_film):
            film_info = future_to_film[future]
            video_url = future.result()
            
            film_id = slugify(film_info['film_adi'])
            with data_lock:
                filmler_data[film_id] = {
                    "isim": film_info['film_adi'],
                    "resim": film_info['poster_url'],
                    "link": video_url
                }

    # Dosyaları kaydet
    with open("hdfilmcehennemi.json", "w", encoding="utf-8") as f:
        json.dump(filmler_data, f, ensure_ascii=False, indent=2)
    
    print(f"🏁 Tamamlandı! Süre: {time.time() - start_time:.2f} sn. Toplam: {len(filmler_data)} film.")

if __name__ == "__main__":
    main()

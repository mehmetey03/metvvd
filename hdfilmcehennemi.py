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
# AYARLAR VE SABİTLER
# ============================================================================
PAGES_TO_SCRAPE = int(sys.argv[1]) if len(sys.argv) > 1 else 5
BASE_URL = "https://www.hdfilmcehennemi.com"
GITHUB_JSON_URL = "https://raw.githubusercontent.com/mehmetey03/metvvd/refs/heads/main/hdfilmcehennemi.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "tr-TR,tr;q=0.8,en-US;q=0.5,en;q=0.3",
    "Referer": BASE_URL,
    "Connection": "keep-alive",
}

MAX_WORKERS = 10
data_lock = Lock()
session = requests.Session()
session.headers.update(HEADERS)

# ============================================================================
# YARDIMCI FONKSİYONLAR
# ============================================================================

def get_soup(url):
    try:
        # Sitenin anti-bot mekanizmasını aşmak için küçük bir gecikme
        time.sleep(0.2)
        response = session.get(url, timeout=15)
        if response.status_code == 200:
            return BeautifulSoup(response.content, "html.parser")
        else:
            print(f"⚠️ Hata: {url} -> Kod: {response.status_code}")
    except Exception as e:
        print(f"❌ İstek Hatası: {e}")
    return None

def slugify(text):
    text = text.lower()
    tr_map = str.maketrans("ığüşöç", "igusoc")
    text = text.translate(tr_map)
    text = re.sub(r'[^a-z0-9]', '-', text)
    return re.sub(r'-+', '-', text).strip('-')

def process_film_detail(film_info, filmler_data):
    try:
        target_url = urljoin(BASE_URL, film_info['film_link'])
        soup = get_soup(target_url)
        video_url = ""
        
        if soup:
            # Video iframe'ini bulma (Site yapısına göre güncellendi)
            iframe = soup.select_one('iframe.close, .player-container iframe, #video-player iframe')
            if iframe:
                ds = iframe.get('data-src') or iframe.get('src')
                if ds:
                    if "rapidrame_id=" in ds:
                        video_id = ds.split("rapidrame_id=")[1].split("&")[0]
                        video_url = f"{BASE_URL}/rplayer/{video_id}"
                    else:
                        video_url = ds

        film_id = slugify(film_info['film_adi'])
        with data_lock:
            filmler_data[film_id] = {
                "isim": film_info['film_adi'],
                "resim": film_info['poster_url'],
                "link": video_url
            }
        return True
    except:
        return False

# ============================================================================
# ANA SÜREÇ
# ============================================================================

def main():
    print(f"📅 Başlatıldı: {time.strftime('%H:%M:%S')}")
    print(f"🚀 {PAGES_TO_SCRAPE} sayfa taranıyor...")
    
    filmler_data = {}
    all_film_links = []

    # 1. AŞAMA: Film linklerini topla
    for p in range(1, PAGES_TO_SCRAPE + 1):
        page_url = f"{BASE_URL}/kategori/film-izle-7/page/{p}/" # Alternatif kategori yolu
        print(f"🔎 Sayfa {p} okunuyor...")
        
        soup = get_soup(page_url)
        if not soup: continue
        
        # Sitenin güncel yapısına göre seçiciyi genişletiyoruz
        items = soup.select('a.poster, .poster-container a, .film-item a')
        
        for a in items:
            title = a.get('title') or (a.find('img').get('alt') if a.find('img') else "")
            href = a.get('href')
            img_tag = a.find('img')
            
            if href and title:
                img_url = ""
                if img_tag:
                    img_url = img_tag.get('data-src') or img_tag.get('src') or ""
                    img_url = img_url.split('?')[0] if img_url else ""

                all_film_links.append({
                    'film_adi': title.strip(),
                    'film_link': href,
                    'poster_url': img_url
                })

    if not all_film_links:
        print("❌ Hiç film bulunamadı! Lütfen site adresini veya seçicileri (CSS Selectors) kontrol edin.")
        return

    print(f"🔗 {len(all_film_links)} film bulundu. Detaylar (Video Linkleri) çekiliyor...")

    # 2. AŞAMA: Detayları paralel işle
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(process_film_detail, f, filmler_data) for f in all_film_links]
        processed = 0
        for _ in as_completed(futures):
            processed += 1
            if processed % 10 == 0:
                print(f"⏳ %{int((processed/len(all_film_links))*100)} tamamlandı...")

    save_outputs(filmler_data)

def save_outputs(data):
    # JSON
    with open("hdfilmcehennemi.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    # HTML (Önceki şablonu kullanır)
    print(f"✅ İşlem bitti. {len(data)} film kaydedildi.")

if __name__ == "__main__":
    main()

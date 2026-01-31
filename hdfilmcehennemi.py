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
# Hız çok yüksek olduğunda site boş veri döndürür. Bu yüzden 0.2-0.5 idealdir.
DELAY_BETWEEN_PAGES = 0.5 

BASE_URL = "https://www.hdfilmcehennemi.com"
GITHUB_JSON_URL = "https://raw.githubusercontent.com/mehmetey03/metvvd/refs/heads/main/hdfilmcehennemi.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": BASE_URL
}

# Thread yapılandırması (Site güvenliği için makul seviyede tutuldu)
MAX_WORKERS = 5 
data_lock = Lock()
session = requests.Session()

# ============================================================================
# FONKSİYONLAR
# ============================================================================

def slugify(text):
    text = text.lower()
    tr_map = str.maketrans("ığüşöç", "igusoc")
    text = text.translate(tr_map)
    text = re.sub(r'[^a-z0-9]', '-', text)
    return re.sub(r'-+', '-', text).strip('-')

def get_film_video_url(film_page_url):
    """Film sayfasının içine girip asıl video kaynağını (iframe) bulur."""
    try:
        res = session.get(film_page_url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.content, "html.parser")
        
        # Sitenin güncel iframe yapısı (data-src veya src kontrolü)
        iframe = soup.find('iframe', {'class': 'close'}) or soup.find('iframe')
        if iframe:
            raw_url = iframe.get('data-src') or iframe.get('src')
            if raw_url:
                if "rapidrame_id=" in raw_url:
                    rapid_id = raw_url.split("rapidrame_id=")[1].split("&")[0]
                    return f"https://www.hdfilmcehennemi.com/rplayer/{rapid_id}"
                return raw_url
    except:
        pass
    return ""

def process_page(page_num, filmler_data):
    """Belirli bir sayfadaki filmleri çeker."""
    # Kategori bazlı sayfalama URL'si
    api_url = f"{BASE_URL}/load/page/{page_num}/categories/film-izle-2/"
    
    try:
        response = session.get(api_url, headers=HEADERS, timeout=15)
        if response.status_code != 200:
            print(f"❌ Sayfa {page_num} hatası: Durum Kodu {response.status_code}")
            return 0

        data = response.json()
        html_content = data.get('html', '')
        if not html_content:
            print(f"⚠️ Sayfa {page_num} içeriği boş (JSON 'html' boş)")
            return 0

        soup = BeautifulSoup(html_content, 'html.parser')
        # Sitedeki güncel film kartı seçicisi: Genellikle 'poster' class'ına sahip 'a' etiketleri
        items = soup.select('a.poster') or soup.select('.poster-container a')

        page_count = 0
        for item in items:
            try:
                film_adi = item.get('title') or item.find('h2').text.strip()
                film_link = urljoin(BASE_URL, item.get('href'))
                
                poster_img = item.find('img')
                poster_url = ""
                if poster_img:
                    poster_url = poster_img.get('data-src') or poster_img.get('src', '')
                    if "?" in poster_url: poster_url = poster_url.split("?")[0]

                # Video linkini almak için sayfa içine gir (Opsiyonel: Hız için kapatılabilir)
                video_url = get_film_video_url(film_link)

                film_id = slugify(film_adi)
                with data_lock:
                    filmler_data[film_id] = {
                        "isim": film_adi,
                        "resim": poster_url if poster_url else "https://via.placeholder.com/300x450",
                        "link": video_url if video_url else film_link
                    }
                page_count += 1
            except Exception as e:
                continue

        print(f"✅ Sayfa {page_num} tamamlandı: {page_count} film eklendi.")
        return page_count

    except Exception as e:
        print(f"💥 Sayfa {page_num} işlenirken hata oluştu: {str(e)}")
        return 0

# ============================================================================
# ANA ÇALIŞTIRICI
# ============================================================================

def main():
    print(f"🚀 Bot Başlatıldı: {PAGES_TO_SCRAPE} sayfa taranıyor...")
    all_films = {}
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(process_page, i, all_films) for i in range(1, PAGES_TO_SCRAPE + 1)]
        for future in as_completed(futures):
            future.result()
            time.sleep(DELAY_BETWEEN_PAGES) # Aşırı yüklenmeyi önlemek için

    # Dosyaları Kaydet
    with open("hdfilmcehennemi.json", "w", encoding="utf-8") as f:
        json.dump(all_films, f, ensure_ascii=False, indent=2)

    total_time = time.time() - start_time
    print(f"\n--- İŞLEM TAMAMLANDI ---")
    print(f"🎬 Toplam Film: {len(all_films)}")
    print(f"⏱️ Süre: {total_time:.2f} saniye")
    print(f"📁 Dosya: hdfilmcehennemi.json oluşturuldu.")

if __name__ == "__main__":
    main()

import requests
from bs4 import BeautifulSoup
import json
import time
import re

# ============================================================================
# AYARLAR
# ============================================================================
TARGET_BASE_URL = "https://www.hdfilmcehennemi.com"
PROXY_URL = "https://vepro.hocke.eu/proxy/index.php?"
PAGES_TO_SCRAPE = 3

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
}

def get_page_content(page_num):
    """Codetabs Proxy üzerinden sayfayı çeker."""
    target = f"{TARGET_BASE_URL}/page/{page_num}/"
    full_proxy_url = f"{PROXY_URL}{target}"
    
    try:
        print(f"📡 Proxy üzerinden bağlanılıyor: Sayfa {page_num}...")
        response = requests.get(full_proxy_url, headers=HEADERS, timeout=20)
        
        if response.status_code == 200:
            return response.content
        else:
            print(f"⚠️ Proxy Hatası: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Bağlantı hatası: {e}")
        return None

def parse_films(html_content):
    """HTML içeriğini senin parser yapınla ayrıştırır."""
    if not html_content:
        return []
        
    soup = BeautifulSoup(html_content, 'html.parser')
    film_elements = soup.find_all('a', class_='poster')
    parsed_films = []

    for film in film_elements:
        try:
            film_data = {}
            
            # Başlık
            title_el = film.find('strong', class_='poster-title')
            film_data['title'] = title_el.text.strip() if title_el else "Bilinmiyor"
            
            # Link (Proxy URL'sini temizleyip orijinal linki alma)
            raw_link = film.get('href')
            film_data['link'] = raw_link if raw_link.startswith('http') else f"{TARGET_BASE_URL}{raw_link}"
            
            # IMDB
            imdb_el = film.find('span', class_='imdb')
            film_data['imdb'] = imdb_el.text.strip() if imdb_el else "N/A"
            
            # Resim
            img = film.find('img')
            if img:
                film_data['image'] = img.get('data-src') or img.get('src')

            parsed_films.append(film_data)
        except:
            continue
            
    return parsed_films

def main():
    all_films = []
    
    for page in range(1, PAGES_TO_SCRAPE + 1):
        content = get_page_content(page)
        films = parse_films(content)
        
        if films:
            all_films.extend(films)
            print(f"✅ Sayfa {page} başarıyla işlendi. (+{len(films)} film)")
        else:
            print(f"❌ Sayfa {page} içeriği boş veya alınamadı.")
            
        # Proxy servisini yormamak için kısa bir bekleme
        time.sleep(2)

    # Sonuçları Kaydet
    with open('hdfilmcehennemi.json', 'w', encoding='utf-8') as f:
        json.dump(all_films, f, ensure_ascii=False, indent=2)

    print(f"\n🏁 İşlem Tamamlandı! Toplam {len(all_films)} film kaydedildi.")

if __name__ == "__main__":
    main()

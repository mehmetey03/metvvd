import requests
from bs4 import BeautifulSoup
import json
import time
import re
import sys

# ============================================================================
# AYARLAR
# ============================================================================
BASE_URL = "https://www.hdfilmcehennemi.com"
PAGES_TO_SCRAPE = 3  # Test için 3 sayfa

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Referer": BASE_URL
}

def parse_films(html_content):
    """Senin hazırladığın mantıkla HTML'i parçalar"""
    soup = BeautifulSoup(html_content, 'html.parser')
    film_elements = soup.find_all('a', class_='poster')
    parsed_films = []

    for film in film_elements:
        try:
            film_data = {}
            
            # Başlık ve Link
            title_el = film.find('strong', class_='poster-title')
            film_data['title'] = title_el.text.strip() if title_el else "Bilinmiyor"
            film_data['link'] = film.get('href')
            
            # IMDB ve Yıl
            imdb_el = film.find('span', class_='imdb')
            film_data['imdb'] = imdb_el.text.strip() if imdb_el else "N/A"
            
            meta = film.find('div', class_='poster-meta')
            if meta:
                spans = meta.find_all('span')
                film_data['year'] = spans[0].text.strip() if len(spans) > 0 else None

            # Resim (Lazyload Desteği)
            img = film.find('img')
            if img:
                film_data['image'] = img.get('data-src') or img.get('src')

            parsed_films.append(film_data)
        except Exception as e:
            continue
    
    return parsed_films

def main():
    session = requests.Session()
    session.headers.update(HEADERS)
    all_results = []

    print(f"🚀 İşlem başladı. Hedef: {PAGES_TO_SCRAPE} sayfa.")

    for page in range(1, PAGES_TO_SCRAPE + 1):
        url = f"{BASE_URL}/page/{page}/"
        print(f"🔎 Sayfa {page} taranıyor...")
        
        try:
            # İnsan taklidi gecikmesi (451 hatasını önlemek için önemli)
            time.sleep(2)
            response = session.get(url, timeout=15)
            
            if response.status_code == 200:
                # Sayfa içeriğini parse_films fonksiyonuna gönderiyoruz
                page_films = parse_films(response.content)
                all_results.extend(page_films)
                print(f"✅ Sayfa {page} bitti: {len(page_films)} film bulundu.")
            else:
                print(f"⚠️ Sayfa {page} hatası: Durum Kodu {response.status_code}")
                
        except Exception as e:
            print(f"❌ Sayfa {page} işlenirken kritik hata: {e}")

    # JSON Kaydet
    with open('hdfilmcehennemi.json', 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    print(f"\n🏁 BİTTİ! Toplam {len(all_results)} film 'hdfilmcehennemi.json' dosyasına kaydedildi.")

if __name__ == "__main__":
    main()

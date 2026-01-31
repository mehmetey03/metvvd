import requests
from bs4 import BeautifulSoup
import json
import time
import re

# ============================================================================
# AYARLAR
# ============================================================================
BASE_URL = "https://www.hdfilmcehennemi.com"
# Site veriyi genellikle bu tip bir endpoint'ten çeker
API_ENDPOINT = f"{BASE_URL}/load/page/{{page}}/" 
PAGES_TO_SCRAPE = 5

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "X-Requested-With": "XMLHttpRequest", # Ajax isteği olduğunu belirtir (Kritik)
    "Referer": BASE_URL,
    "Accept": "application/json, text/javascript, */*; q=0.01"
}

def scrape():
    filmler_data = {}
    print(f"🚀 Scraping started via API Mode...")

    for page in range(1, PAGES_TO_SCRAPE + 1):
        # Bazı sitelerde kategori belirtmek gerekebilir (film-izle-1 vb.)
        # Eğer bu URL çalışmazsa BASE_URL + "/page/" + str(page) deneyin
        url = f"{BASE_URL}/load/page/{page}/categories/film-izle-7/" 
        
        print(f"🔎 Sayfa {page} taranıyor...", end="\r")
        try:
            response = requests.get(url, headers=HEADERS, timeout=15)
            
            # Eğer yanıt JSON ise içindeki HTML'i çekiyoruz
            if response.status_code == 200:
                data = response.json()
                html_content = data.get('html', '')
                soup = BeautifulSoup(html_content, "html.parser")
            else:
                # API başarısızsa doğrudan HTML sayfayı dene
                response = requests.get(f"{BASE_URL}/page/{page}/", headers=HEADERS)
                soup = BeautifulSoup(response.content, "html.parser")

            # Film kutularını yakala
            items = soup.find_all('a', class_='poster')
            
            for a in items:
                title = a.get('title', '').strip()
                link = a.get('href', '')
                img_tag = a.find('img')
                
                if title and link:
                    img_url = ""
                    if img_tag:
                        img_url = img_tag.get('data-src') or img_tag.get('src', '')
                    
                    film_id = re.sub(r'[^a-z0-9]', '-', title.lower())
                    filmler_data[film_id] = {
                        "isim": title,
                        "resim": img_url.split('?')[0],
                        "link": link # Daha sonra detay sayfasından video çekilebilir
                    }
        except Exception as e:
            print(f"\n❌ Sayfa {page} hatası: {e}")

    print(f"\n✅ Toplam {len(filmler_data)} film bulundu.")
    
    # Sonuçları Kaydet
    with open("hdfilmcehennemi.json", "w", encoding="utf-8") as f:
        json.dump(filmler_data, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    scrape()

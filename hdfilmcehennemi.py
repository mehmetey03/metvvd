import requests
from bs4 import BeautifulSoup
import json
import time
import re
import os
import sys
from urllib.parse import urljoin

# ============================================================================
# GÜNCEL AYARLAR
# ============================================================================
# Tarayıcıda açılan son adresi buraya sabitledik
BASE_URL = "https://www.hdfilmcehennemi.nl" 
PAGES_TO_SCRAPE = int(sys.argv[1]) if len(sys.argv) > 1 else 5

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Referer": "https://www.google.com/",
}

def slugify(text):
    tr_map = str.maketrans("ığüşöçİĞÜŞÖÇ", "igusocIGUSOC")
    text = text.lower().translate(tr_map)
    text = re.sub(r'[^a-z0-9]', '-', text)
    return re.sub(r'-+', '-', text).strip('-')

def scrape():
    filmler_data = {}
    # allow_redirects=True sayesinde .com -> .nl yönlendirmesini takip eder
    session = requests.Session()
    session.headers.update(HEADERS)
    
    print(f"🚀 {BASE_URL} üzerinden tarama başlıyor...")

    for sayfa in range(1, PAGES_TO_SCRAPE + 1):
        # Site API yolu: /load/page/X/...
        url = f"{BASE_URL}/load/page/{sayfa}/categories/film-izle-2/"
        
        try:
            # timeout'u biraz artırdık, yönlendirmeyi aktif ettik
            response = session.get(url, timeout=20, allow_redirects=True)
            
            if response.status_code != 200:
                print(f"❌ Sayfa {sayfa} hatası: Durum Kodu {response.status_code}")
                # Eğer hala 451 gelirse site adresini koda elle tekrar girmelisin
                continue

            data = response.json()
            html_chunk = data.get('html', '')
            
            if not html_chunk:
                print(f"⚠️ Sayfa {sayfa} içeriği boş geldi.")
                continue

            soup = BeautifulSoup(html_chunk, 'html.parser')
            film_kutulari = soup.select('a.poster')
            
            for a in film_kutulari:
                isim = a.get('title') or a.text.strip()
                link = urljoin(BASE_URL, a.get('href'))
                
                img = a.find('img')
                resim = ""
                if img:
                    # Sitede lazy load varsa data-src kullanılır
                    resim = img.get('data-src') or img.get('src', '')
                    if resim.startswith("//"): resim = "https:" + resim
                    if "?" in resim: resim = resim.split("?")[0]
                
                film_id = slugify(isim)
                filmler_data[film_id] = {
                    "isim": isim,
                    "resim": resim if resim else "https://via.placeholder.com/300x450",
                    "link": link
                }
            
            print(f"✅ Sayfa {sayfa} işlendi. ({len(film_kutulari)} film bulundu)")
            time.sleep(0.5) # Çok hızlı istek ban sebebidir

        except Exception as e:
            print(f"💥 Sayfa {sayfa} hatası: {e}")

    # JSON Olarak Kaydet
    with open("hdfilmcehennemi.json", "w", encoding="utf-8") as f:
        json.dump(filmler_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n✨ İşlem bitti. Toplam {len(filmler_data)} film kaydedildi.")

if __name__ == "__main__":
    scrape()

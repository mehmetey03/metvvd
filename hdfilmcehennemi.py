import requests
from bs4 import BeautifulSoup
import json
import time
import re
import os
import sys

# ============================================================================
# AYARLAR
# ============================================================================
# Sitenin en güncel adresini buraya yazın (Örn: hdfilmcehennemi.io)
BASE_URL = "https://www.hdfilmcehennemi.com" 
PAGES_TO_SCRAPE = int(sys.argv[1]) if len(sys.argv) > 1 else 3

# Cloudflare ve 451 engeli için Header'ları güçlendirelim
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://www.google.com/",
    "Connection": "keep-alive"
}

def slugify(text):
    tr_map = str.maketrans("ığüşöç", "igusoc")
    text = text.lower().translate(tr_map)
    text = re.sub(r'[^a-z0-9]', '-', text)
    return re.sub(r'-+', '-', text).strip('-')

def scrape():
    filmler_data = {}
    session = requests.Session()
    
    print(f"🚀 {BASE_URL} üzerinden tarama başlıyor...")

    for sayfa in range(1, PAGES_TO_SCRAPE + 1):
        # Site genellikle bu URL yapısını kullanır
        url = f"{BASE_URL}/load/page/{sayfa}/categories/film-izle-2/"
        
        try:
            response = session.get(url, headers=HEADERS, timeout=15)
            
            if response.status_code == 451:
                print(f"❌ Sayfa {sayfa}: Erişim Engellendi (451). Site adresi değişmiş olabilir!")
                continue
            
            if response.status_code != 200:
                print(f"❌ Sayfa {sayfa} hatası: {response.status_code}")
                continue

            # JSON yanıtını al
            data = response.json()
            html_chunk = data.get('html', '')
            soup = BeautifulSoup(html_chunk, 'html.parser')
            
            # Film kutularını bul
            film_kutulari = soup.select('a.poster')
            
            for a in film_kutulari:
                isim = a.get('title') or a.text.strip()
                link = urljoin(BASE_URL, a.get('href'))
                
                img = a.find('img')
                resim = ""
                if img:
                    resim = img.get('data-src') or img.get('src', '')
                    if "?" in resim: resim = resim.split("?")[0]
                
                film_id = slugify(isim)
                filmler_data[film_id] = {
                    "isim": isim,
                    "resim": resim if resim else "https://via.placeholder.com/300x450",
                    "link": link
                }
            
            print(f"✅ Sayfa {sayfa} işlendi. Mevcut toplam: {len(filmler_data)}")
            time.sleep(1) # Siteyi yormayalım

        except Exception as e:
            print(f"💥 Sayfa {sayfa} sırasında bir hata oluştu: {e}")

    # Kayıt
    with open("hdfilmcehennemi.json", "w", encoding="utf-8") as f:
        json.dump(filmler_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n✨ İşlem bitti. {len(filmler_data)} film kaydedildi.")

from urllib.parse import urljoin
if __name__ == "__main__":
    scrape()

import requests
from bs4 import BeautifulSoup
import json
import time
import re
import os
import sys
from urllib.parse import urljoin

# ============================================================================
# GÜNCEL AYARLAR (451 BYPASS MODU)
# ============================================================================
BASE_URL = "https://www.hdfilmcehennemi.nl"
PAGES_TO_SCRAPE = int(sys.argv[1]) if len(sys.argv) > 1 else 5

# Daha kapsamlı ve "gerçekçi" Header seti
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Cache-Control": "max-age=0",
}

def slugify(text):
    tr_map = str.maketrans("ığüşöçİĞÜŞÖÇ", "igusocIGUSOC")
    text = text.lower().translate(tr_map)
    text = re.sub(r'[^a-z0-9]', '-', text)
    return re.sub(r'-+', '-', text).strip('-')

def scrape():
    filmler_data = {}
    session = requests.Session()
    session.headers.update(HEADERS)
    
    # Önce ana sayfaya gidip çerez (cookie) alalım
    try:
        print(f"📡 Çerezler alınıyor: {BASE_URL}")
        session.get(BASE_URL, timeout=15)
    except:
        pass

    print(f"🚀 Tarama başlıyor...")

    for sayfa in range(1, PAGES_TO_SCRAPE + 1):
        # API URL'sini değiştirelim: Bazı siteler load/page yerine direkt ?page=X kullanır
        # Eğer bu URL çalışmazsa tarayıcıdan network sekmesini tekrar kontrol etmeliyiz
        url = f"{BASE_URL}/load/page/{sayfa}/categories/film-izle-2/"
        
        try:
            # allow_redirects=False yaparak 451'e düşüp düşmediğimizi kontrol edelim
            response = session.get(url, timeout=20, allow_redirects=True)
            
            if response.status_code == 451:
                print(f"❌ Sayfa {sayfa}: Sunucu IP adresini engelledi (451).")
                continue

            if response.status_code != 200:
                print(f"❌ Sayfa {sayfa} hatası: {response.status_code}")
                continue

            # Bazı durumlarda JSON yerine direkt HTML dönebilir
            try:
                data = response.json()
                html_chunk = data.get('html', '')
            except:
                html_chunk = response.text

            soup = BeautifulSoup(html_chunk, 'html.parser')
            # Seçiciyi genişletelim (hem a.poster hem de article yapılarını kontrol et)
            film_kutulari = soup.select('a.poster') or soup.select('.poster')
            
            if not film_kutulari:
                print(f"⚠️ Sayfa {sayfa}: Film bulunamadı (Seçici hatası olabilir).")
                continue

            for a in film_kutulari:
                isim = a.get('title') or a.text.strip()
                link = urljoin(BASE_URL, a.get('href'))
                
                img = a.find('img')
                resim = ""
                if img:
                    resim = img.get('data-src') or img.get('src', '')
                    if resim.startswith("//"): resim = "https:" + resim
                
                film_id = slugify(isim)
                filmler_data[film_id] = {
                    "isim": isim,
                    "resim": resim,
                    "link": link
                }
            
            print(f"✅ Sayfa {sayfa}: {len(film_kutulari)} film eklendi.")
            time.sleep(1.5) # 451'i tetiklememek için süreyi artırdık

        except Exception as e:
            print(f"💥 Sayfa {sayfa} hatası: {e}")

    # Kaydet
    with open("hdfilmcehennemi.json", "w", encoding="utf-8") as f:
        json.dump(filmler_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n✨ İşlem bitti. Toplam {len(filmler_data)} film.")

if __name__ == "__main__":
    scrape()

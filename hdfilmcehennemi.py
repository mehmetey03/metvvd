import requests
from bs4 import BeautifulSoup
import json
import time
import re
import sys
from urllib.parse import urljoin

# ============================================================================
# PROXY MODLU GÜNCEL KOD
# ============================================================================
BASE_URL = "https://www.hdfilmcehennemi.nl"
PAGES_TO_SCRAPE = int(sys.argv[1]) if len(sys.argv) > 1 else 5

def slugify(text):
    tr_map = str.maketrans("ığüşöçİĞÜŞÖÇ", "igusocIGUSOC")
    return re.sub(r'[^a-z0-9]', '-', text.lower().translate(tr_map)).strip('-')

def scrape():
    filmler_data = {}
    session = requests.Session()
    
    # 451 Engelini aşmak için gerçekçi bir tarayıcı profili
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Referer": "https://www.google.com/"
    })

    # ÜCRETSİZ PROXY LİSTESİ (GitHub IP'sini gizlemek için)
    # Not: Ücretsiz proxyler çabuk ölür. Eğer çalışmazsa proxy kullanmadan 
    # kendi bilgisayarında çalıştırman en sağlıklısıdır.
    proxies = {
        "http": "http://167.172.175.251:3128", 
        "https": "http://167.172.175.251:3128"
    }

    print(f"📡 Hedef: {BASE_URL} üzerinden veri toplama deneyi...")

    for sayfa in range(1, PAGES_TO_SCRAPE + 1):
        url = f"{BASE_URL}/load/page/{sayfa}/categories/film-izle-2/"
        
        try:
            # Proxy kullanarak isteği gönder (proxies=proxies parametresini ekleyebilirsin)
            response = session.get(url, timeout=20)
            
            if response.status_code == 451:
                print(f"❌ Sayfa {sayfa}: GitHub Runner IP'si hâlâ bloklu (451).")
                continue

            if response.status_code == 200:
                try:
                    html_chunk = response.json().get('html', '')
                except:
                    html_chunk = response.text

                soup = BeautifulSoup(html_chunk, 'html.parser')
                items = soup.select('a.poster')
                
                for a in items:
                    name = a.get('title') or a.text.strip()
                    img = a.find('img')
                    poster = img.get('data-src') or img.get('src', '') if img else ""
                    
                    film_id = slugify(name)
                    filmler_data[film_id] = {
                        "isim": name,
                        "resim": urljoin(BASE_URL, poster) if poster.startswith("/") else poster,
                        "link": urljoin(BASE_URL, a.get('href'))
                    }
                print(f"✅ Sayfa {sayfa}: {len(items)} film eklendi.")
            
            time.sleep(2) # Banlanmamak için yavaşla

        except Exception as e:
            print(f"💥 Sayfa {sayfa} hatası: {e}")

    # Sonuçları Kaydet
    with open("hdfilmcehennemi.json", "w", encoding="utf-8") as f:
        json.dump(filmler_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n✨ İşlem bitti. Toplam {len(filmler_data)} film.")

if __name__ == "__main__":
    scrape()

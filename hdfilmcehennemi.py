import requests
from bs4 import BeautifulSoup
import json
import time
import re

# ============================================================================
# AYARLAR
# ============================================================================
BASE_URL = "https://www.hdfilmcehennemi.com"
PAGES_TO_SCRAPE = 5

# Modern tarayıcı taklidi
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Cache-Control": "max-age=0",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1"
}

def get_session():
    """Çerezleri toplamak için bir oturum başlatır."""
    session = requests.Session()
    session.headers.update(HEADERS)
    try:
        # Önce ana sayfaya giderek çerezleri alalım
        print("🔑 Oturum başlatılıyor (Çerezler toplanıyor)...")
        session.get(BASE_URL, timeout=10)
        return session
    except:
        return session

def scrape():
    session = get_session()
    filmler_data = {}
    
    print(f"🚀 Scraping started with Session Mode...")

    for page in range(1, PAGES_TO_SCRAPE + 1):
        # Site yapısına göre iki farklı URL formatını da deniyoruz
        url = f"{BASE_URL}/page/{page}/"
        if page == 1:
            url = f"{BASE_URL}/"

        print(f"🔎 Sayfa {page} taranıyor... ({url})")
        
        try:
            # İnsan taklidi için küçük bir bekleme
            time.sleep(1.5)
            response = session.get(url, timeout=15)
            
            if response.status_code != 200:
                print(f"⚠️ Sayfa {page} erişilemez durumda (Kod: {response.status_code})")
                continue

            soup = BeautifulSoup(response.content, "html.parser")
            
            # Seçicileri genişletiyoruz: Sitenin farklı versiyonlarında 
            # 'poster', 'film-item' veya 'post' kullanılabilir.
            items = soup.find_all(['a', 'div'], class_=['poster', 'post-item', 'film-box'])
            
            # Eğer yukarıdaki bulamazsa direkt linkleri tara
            if not items:
                items = soup.select('div.poster-container a')

            for item in items:
                # Eğer item bir div ise içindeki a'yı bul, a ise kendisini kullan
                a_tag = item if item.name == 'a' else item.find('a')
                if not a_tag: continue
                
                title = a_tag.get('title') or a_tag.text.strip()
                link = a_tag.get('href', '')
                
                # Resim URL'sini çekme (Lazy load desteğiyle)
                img_tag = a_tag.find('img')
                img_url = ""
                if img_tag:
                    img_url = img_tag.get('data-src') or img_tag.get('src') or ""

                if title and link.startswith('http'):
                    film_id = re.sub(r'[^a-z0-9]', '-', title.lower())
                    filmler_data[film_id] = {
                        "isim": title,
                        "resim": img_url.split('?')[0],
                        "link": link
                    }
            
            print(f"✅ Sayfa {page}: {len(items)} potansiyel öğe tarandı.")

        except Exception as e:
            print(f"❌ Sayfa {page} hatası: {e}")

    print(f"\n📊 İşlem Tamamlandı. Toplam {len(filmler_data)} film veritabanına eklendi.")
    
    with open("hdfilmcehennemi.json", "w", encoding="utf-8") as f:
        json.dump(filmler_data, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    scrape()

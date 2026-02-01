import requests
from bs4 import BeautifulSoup
import json
import time
from datetime import datetime
import urllib.parse
import random

# --- AYARLAR ---
PAGES_TO_SCRAPE = 5
BASE_URL = "https://www.hdfilmcehennemi.nl"
# En stabil çalışan proxy'yi başa aldık
PROXY_URL = "https://api.codetabs.com/v1/proxy/?quest="

def scrape_optimized():
    all_films = []
    
    for page in range(1, PAGES_TO_SCRAPE + 1):
        # --- URL OLUŞTURMA (Hassas Ayar) ---
        if page == 1:
            target_url = f"{BASE_URL}/"
        else:
            # Sitenin tam istediği yapı: sonu mutlaka "/" ile bitmeli
            target_url = f"{BASE_URL}/sayfa/{page}/"
            
        full_proxy_url = PROXY_URL + urllib.parse.quote(target_url)
        
        print(f"🔍 [{page}/{PAGES_TO_SCRAPE}] Çekiliyor: {target_url}")
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/121.0.0.0 Safari/537.36',
                'Referer': BASE_URL + "/", # Siteyi "ana sayfadan geliyorum" diye ikna ediyoruz
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
            }
            
            # allow_redirects=True sayesinde yönlendirmeleri (301/302) takip ediyoruz
            response = requests.get(full_proxy_url, headers=headers, timeout=20, allow_redirects=True)
            
            if response.status_code != 200:
                print(f"❌ Sayfa {page} hatası: {response.status_code}")
                continue
                
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # --- FİLM ELEMENTLERİNİ BULMA (Daha Geniş Kapsam) ---
            # Sadece 'a.poster' değil, alternatifleri de tarayalım
            film_elements = soup.find_all('a', class_='poster')
            
            if not film_elements:
                # Alternatif: Sayfa 2+'da farklı bir yapı varsa
                film_elements = soup.select('.poster-wrapper a') or soup.select('article a.poster')

            page_films = []
            for element in film_elements:
                title_node = element.find('strong', class_='poster-title')
                title = title_node.text.strip() if title_node else element.get('title', '').strip()
                
                if not title: continue
                
                # Link
                href = element.get('href', '')
                link = f"{BASE_URL}{href}" if href.startswith('/') else href
                
                # Resim (Lazyload için data-src kontrolü kritik)
                img = element.find('img')
                img_url = ""
                if img:
                    img_url = img.get('data-src') or img.get('src') or ""
                    if img_url.startswith('/'): img_url = f"{BASE_URL}{img_url}"
                
                # IMDB ve Yıl
                imdb = element.find('span', class_='imdb').text.strip() if element.find('span', class_='imdb') else "6.0"
                meta = element.find('div', class_='poster-meta')
                year = meta.find('span').text.strip() if meta and meta.find('span') else "2025"

                page_films.append({
                    'title': title,
                    'link': link,
                    'image': img_url,
                    'imdb': imdb,
                    'year': year
                })

            if page_films:
                print(f"✅ Sayfa {page} başarılı: {len(page_films)} film bulundu.")
                all_films.extend(page_films)
            else:
                print(f"⚠️ Sayfa {page} boş döndü. HTML yapısı farklı olabilir.")
                # Hata analizi için sayfanın ilk 200 karakterini görelim
                print(f"   İçerik özeti: {response.text[:100]}...")

            # --- BEKLEME (Anti-Bot) ---
            time.sleep(random.uniform(1.5, 2.5))
            
        except Exception as e:
            print(f"❌ Hata: {e}")
            
    return all_films

# --- ÇALIŞTIR VE KAYDET ---
data = scrape_optimized()
if data:
    with open('hdfilmcehennemi.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\n🏁 TOPLAM: {len(data)} film çekildi ve JSON kaydedildi.")

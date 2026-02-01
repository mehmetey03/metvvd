import requests
from bs4 import BeautifulSoup
import json
import time
import urllib.parse

def scrape_hd_film(max_pages=5):
    all_films = []
    base_url = "https://www.hdfilmcehennemi.nl"
    proxy_prefix = "https://api.codetabs.com/v1/proxy/?quest="
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': base_url
    }

    for page in range(1, max_pages + 1):
        # Sayfa 1 için ana dizin, diğerleri için /sayfa/X/ yapısı
        target_path = "/" if page == 1 else f"/sayfa/{page}/"
        full_url = proxy_prefix + urllib.parse.quote(base_url + target_path)
        
        print(f"📡 Sayfa {page} isteniyor...")
        
        try:
            response = requests.get(full_url, headers=headers, timeout=15)
            if response.status_code != 200:
                print(f"❌ Bağlantı hatası: {response.status_code}")
                continue

            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Paylaştığın HTML'e göre en garanti seçim: 'a.poster'
            posters = soup.find_all('a', class_='poster')
            
            page_data = []
            for poster in posters:
                # Başlık çekme (strong etiketinden veya title özniteliğinden)
                title_tag = poster.find('strong', class_='poster-title')
                title = title_tag.get_text(strip=True) if title_tag else poster.get('title', 'İsimsiz')
                
                # Link çekme
                link = poster.get('href', '')
                
                # Resim çekme (Lazyload olduğu için data-src veya src)
                img_tag = poster.find('img')
                img_url = ""
                if img_tag:
                    img_url = img_tag.get('data-src') or img_tag.get('src') or ""

                # IMDB Puanı
                imdb_tag = poster.find('span', class_='imdb')
                imdb = imdb_tag.get_text(strip=True) if imdb_tag else "N/A"
                
                # Yıl (poster-meta içindeki ilk span)
                meta_tag = poster.find('div', class_='poster-meta')
                year = meta_tag.find('span').get_text(strip=True) if meta_tag else "2024"

                page_data.append({
                    "title": title,
                    "link": link,
                    "image": img_url,
                    "imdb": imdb,
                    "year": year
                })

            if page_data:
                print(f"✅ Sayfa {page} bitti: {len(page_data)} film eklendi.")
                all_films.extend(page_data)
            else:
                print(f"⚠️ Sayfa {page}'de film bulunamadı (Seçici hatası olabilir).")
            
            # Siteyi yormamak ve bloklanmamak için kısa ara
            time.sleep(1)

        except Exception as e:
            print(f"💥 Sayfa {page} işlenirken hata oluştu: {str(e)}")

    return all_films

# Çalıştır ve Kaydet
results = scrape_hd_film(5)
with open('filmler.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=4)

print(f"\n🏁 İşlem tamam! Toplam {len(results)} film kaydedildi.")

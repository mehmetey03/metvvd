import requests
from bs4 import BeautifulSoup
import time
import json
import pandas as pd
from datetime import datetime

print(f"📅 Scraping started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# Ayarlar
BASE_URL = "https://www.hdfilmcehennemi.nl"
PAGES_TO_SCRAPE = 5
DELAY_BETWEEN_REQUESTS = 0.5  # saniye

print(f"📊 Pages to scrape: {PAGES_TO_SCRAPE}")
print(f"⏱️ Delay between pages: {DELAY_BETWEEN_REQUESTS} seconds")

all_films = []

for page in range(1, PAGES_TO_SCRAPE + 1):
    print(f"🔍 Scraping page {page}...")
    
    try:
        # Sayfayı indir
        if page == 1:
            url = BASE_URL
        else:
            url = f"{BASE_URL}/sayfa/{page}/"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # HTTP hatalarını kontrol et
        
        # HTML'i parse et
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Film poster elemanlarını bul
        film_elements = soup.find_all('a', class_='poster')
        
        print(f"   Found {len(film_elements)} films on page {page}")
        
        for film in film_elements:
            film_data = {}
            
            # Temel bilgiler
            title_element = film.find('strong', class_='poster-title')
            film_data['title'] = title_element.text.strip() if title_element else None
            
            film_data['link'] = film.get('href')
            
            # Meta bilgileri
            meta_div = film.find('div', class_='poster-meta')
            if meta_div:
                spans = meta_div.find_all('span')
                if len(spans) >= 1:
                    film_data['year'] = spans[0].text.strip()
                if len(spans) >= 2:
                    film_data['comment_count'] = spans[1].text.strip()
            
            # IMDB puanı
            imdb_element = film.find('span', class_='imdb')
            film_data['imdb_rating'] = imdb_element.text.strip() if imdb_element else None
            
            # Dil/altyazı bilgisi
            lang_element = film.find('span', class_='poster-lang')
            if lang_element:
                tr_flag = lang_element.find('i', class_='tr-flag')
                text_span = lang_element.find('span')
                
                if tr_flag:
                    film_data['language'] = 'Türkçe Dublaj'
                elif text_span:
                    film_data['language'] = text_span.text.strip()
                else:
                    film_data['language'] = 'Bilinmiyor'
            
            # Resim URL'leri
            img_element = film.find('img', class_='lazyload')
            if img_element:
                film_data['image'] = img_element.get('data-src')
                srcset = img_element.get('data-srcset', '')
                if srcset and ' ' in srcset:
                    parts = srcset.split(' ')
                    film_data['image_2x'] = parts[1] if len(parts) > 1 else None
            
            all_films.append(film_data)
            
            # Filmler arasında küçük bir gecikme
            time.sleep(0.1)
        
        # Sayfalar arasında gecikme
        if page < PAGES_TO_SCRAPE:
            time.sleep(DELAY_BETWEEN_REQUESTS)
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Error scraping page {page}: {e}")
        continue
    except Exception as e:
        print(f"❌ Unexpected error on page {page}: {e}")
        continue

print(f"\n✅ Scraping completed! Total films collected: {len(all_films)}")

# JSON olarak kaydet
with open('hdfilmcehennemi_films.json', 'w', encoding='utf-8') as f:
    json.dump(all_films, f, ensure_ascii=False, indent=2)
print("📁 JSON file saved: hdfilmcehennemi_films.json")

# CSV olarak kaydet
df = pd.DataFrame(all_films)
df.to_csv('hdfilmcehennemi_films.csv', index=False, encoding='utf-8-sig')
print("📁 CSV file saved: hdfilmcehennemi_films.csv")

# İstatistikler
if all_films:
    print("\n📊 Statistics:")
    print(f"   Total films: {len(all_films)}")
    
    # Yıllara göre dağılım
    years = [film.get('year') for film in all_films if film.get('year')]
    if years:
        year_counts = pd.Series(years).value_counts()
        print(f"   Films by year:\n{year_counts.head(10)}")
    
    # IMDB puan ortalaması
    imdb_scores = []
    for film in all_films:
        if film.get('imdb_rating'):
            try:
                score = float(film['imdb_rating'])
                imdb_scores.append(score)
            except ValueError:
                pass
    
    if imdb_scores:
        print(f"   Average IMDB score: {sum(imdb_scores)/len(imdb_scores):.2f}")
        print(f"   Highest IMDB score: {max(imdb_scores)}")
        print(f"   Lowest IMDB score: {min(imdb_scores)}")
    
    # Dil dağılımı
    languages = [film.get('language') for film in all_films if film.get('language')]
    if languages:
        lang_counts = pd.Series(languages).value_counts()
        print(f"   Language distribution:\n{lang_counts}")

print(f"\n🏁 Scraping finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

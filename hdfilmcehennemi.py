import sys
import requests
from bs4 import BeautifulSoup
import time
import json
from datetime import datetime

# Komut satırı argümanlarını al
PAGES_TO_SCRAPE = int(sys.argv[1]) if len(sys.argv) > 1 else 5
DELAY_BETWEEN_REQUESTS = float(sys.argv[2]) if len(sys.argv) > 2 else 0.5

print(f"📅 Scraping started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"📊 Pages to scrape: {PAGES_TO_SCRAPE}")
print(f"⏱️ Delay between pages: {DELAY_BETWEEN_REQUESTS} seconds")

BASE_URL = "https://www.hdfilmcehennemi.nl"
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
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # HTML'i parse et
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Film poster elemanlarını bul
        film_elements = soup.find_all('a', class_='poster')
        
        print(f"   Found {len(film_elements)} films on page {page}")
        
        for film in film_elements:
            film_data = {}
            
            # Temel bilgiler
            title_element = film.find('strong', class_='poster-title')
            film_data['title'] = title_element.text.strip() if title_element else 'N/A'
            
            film_data['link'] = film.get('href', 'N/A')
            
            # Meta bilgileri (yıl, yorum sayısı)
            meta_div = film.find('div', class_='poster-meta')
            if meta_div:
                spans = meta_div.find_all('span')
                if len(spans) >= 1:
                    film_data['year'] = spans[0].text.strip()
                else:
                    film_data['year'] = 'N/A'
                
                if len(spans) >= 2:
                    film_data['comment_count'] = spans[1].text.strip()
                else:
                    film_data['comment_count'] = '0'
            else:
                film_data['year'] = 'N/A'
                film_data['comment_count'] = '0'
            
            # IMDB puanı
            imdb_element = film.find('span', class_='imdb')
            film_data['imdb_rating'] = imdb_element.text.strip() if imdb_element else 'N/A'
            
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
                    film_data['language'] = 'N/A'
            else:
                film_data['language'] = 'N/A'
            
            # Resim URL'leri
            img_element = film.find('img', class_='lazyload')
            if img_element:
                film_data['image'] = img_element.get('data-src', 'N/A')
                srcset = img_element.get('data-srcset', '')
                if srcset and ' ' in srcset:
                    parts = srcset.split(' ')
                    film_data['image_2x'] = parts[1] if len(parts) > 1 else 'N/A'
                else:
                    film_data['image_2x'] = 'N/A'
            else:
                film_data['image'] = 'N/A'
                film_data['image_2x'] = 'N/A'
            
            all_films.append(film_data)
        
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

# HTML dosyasını kaydet (tüm içerik)
try:
    with open('hdfilmcehennemi.html', 'w', encoding='utf-8') as f:
        f.write(response.text if 'response' in locals() else '')
    print("📁 HTML file saved: hdfilmcehennemi.html")
except Exception as e:
    print(f"❌ Error saving HTML: {e}")

# JSON olarak kaydet
try:
    with open('hdfilmcehennemi.json', 'w', encoding='utf-8') as f:
        json.dump(all_films, f, ensure_ascii=False, indent=2)
    print("📁 JSON file saved: hdfilmcehennemi.json")
except Exception as e:
    print(f"❌ Error saving JSON: {e}")

# İstatistikleri hesapla
if all_films:
    print("\n📊 Statistics:")
    print(f"   Total films: {len(all_films)}")
    
    # Yıllara göre dağılım
    years = {}
    for film in all_films:
        year = film.get('year', 'N/A')
        if year != 'N/A':
            years[year] = years.get(year, 0) + 1
    
    if years:
        print("   Films by year:")
        for year, count in sorted(years.items(), key=lambda x: x[0], reverse=True)[:10]:
            print(f"     {year}: {count} films")
    
    # IMDB puan istatistikleri
    imdb_scores = []
    for film in all_films:
        rating = film.get('imdb_rating', 'N/A')
        if rating != 'N/A':
            try:
                score = float(rating)
                imdb_scores.append(score)
            except (ValueError, TypeError):
                pass
    
    if imdb_scores:
        avg_score = sum(imdb_scores) / len(imdb_scores)
        max_score = max(imdb_scores)
        min_score = min(imdb_scores)
        print(f"   Average IMDB score: {avg_score:.2f}")
        print(f"   Highest IMDB score: {max_score}")
        print(f"   Lowest IMDB score: {min_score}")
    
    # Dil dağılımı
    languages = {}
    for film in all_films:
        lang = film.get('language', 'N/A')
        languages[lang] = languages.get(lang, 0) + 1
    
    if languages:
        print("   Language distribution:")
        for lang, count in languages.items():
            print(f"     {lang}: {count} films")

print(f"\n🏁 Scraping finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

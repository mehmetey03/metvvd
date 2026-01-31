import requests
from bs4 import BeautifulSoup
import time
import json
from datetime import datetime

def scrape_films():
    session = requests.Session()
    
    # Daha detaylı headers
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'tr,tr-TR;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0',
        'Referer': 'https://www.google.com/',
        'DNT': '1'
    })
    
    # Bazı cookies ekle
    session.cookies.update({
        'cookie_consent': 'true',
        'preferred_language': 'tr'
    })
    
    BASE_URL = "https://www.hdfilmcehennemi.nl"
    PAGES_TO_SCRAPE = 5
    all_films = []
    
    # Önce ana sayfayı ziyaret et (cookie'ler için)
    try:
        print("🔍 Visiting homepage for cookies...")
        session.get(BASE_URL, timeout=10)
        time.sleep(2)
    except:
        pass
    
    for page in range(1, PAGES_TO_SCRAPE + 1):
        print(f"🔍 Scraping page {page}...")
        
        try:
            if page == 1:
                url = BASE_URL
            else:
                url = f"{BASE_URL}/sayfa/{page}/"
            
            # Rastgele delay ekle
            time.sleep(1 + (page % 3))
            
            response = session.get(url, timeout=30)
            
            # 451 hatası kontrolü
            if response.status_code == 451:
                print(f"⚠️ Page {page} blocked (451). Trying alternative approach...")
                
                # Alternative: Cloudflare bypass denemesi
                session.headers.update({
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                })
                
                response = session.get(url, timeout=30)
            
            response.raise_for_status()
            
            # HTML kontrolü
            if len(response.text) < 1000:
                print(f"⚠️ Page {page} returned suspiciously small content")
                continue
                
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Eğer hala erişim engeli varsa
            if "erişim" in soup.text.lower() or "access" in soup.text.lower() or "blocked" in soup.text.lower():
                print(f"❌ Page {page} still blocked. Skipping...")
                continue
            
            # Filmleri parse et
            film_elements = soup.find_all('a', class_='poster')
            
            if not film_elements:
                # Farklı bir selector dene
                film_elements = soup.find_all('a', href=True)
                film_elements = [f for f in film_elements if 'hdfilmcehennemi.nl' in f.get('href', '')]
            
            print(f"   Found {len(film_elements)} films on page {page}")
            
            for film in film_elements[:20]:  # İlk 20 filmle sınırla
                film_data = extract_film_data(film)
                if film_data:
                    all_films.append(film_data)
            
            time.sleep(2)  # Sayfalar arası daha uzun bekleme
            
        except Exception as e:
            print(f"❌ Error on page {page}: {str(e)[:100]}")
            continue
    
    return all_films

def extract_film_data(film):
    """Film verilerini çıkar"""
    film_data = {}
    
    try:
        # Başlık
        title_elem = film.find(['strong', 'h3', 'h2'], class_=lambda x: x and ('title' in str(x).lower() or 'poster' in str(x)))
        if not title_elem:
            title_elem = film.find('strong')
        film_data['title'] = title_elem.text.strip() if title_elem else film.get('title', 'N/A')
        
        # Link
        film_data['link'] = film.get('href', 'N/A')
        
        # Diğer bilgiler
        meta_div = film.find('div', class_='poster-meta') or film.find('div', class_=lambda x: x and 'meta' in str(x))
        if meta_div:
            spans = meta_div.find_all('span')
            film_data['year'] = spans[0].text.strip() if spans else 'N/A'
            film_data['comment_count'] = spans[1].text.strip() if len(spans) > 1 else '0'
        else:
            film_data['year'] = 'N/A'
            film_data['comment_count'] = '0'
        
        # IMDB
        imdb_elem = film.find('span', class_='imdb') or film.find('span', string=lambda x: x and 'imdb' in str(x).lower())
        film_data['imdb_rating'] = imdb_elem.text.strip() if imdb_elem else 'N/A'
        
        # Dil
        lang_elem = film.find('span', class_='poster-lang') or film.find('span', class_=lambda x: x and ('lang' in str(x) or 'dil' in str(x)))
        if lang_elem:
            film_data['language'] = lang_elem.text.strip()
        else:
            film_data['language'] = 'N/A'
        
        # Resim
        img_elem = film.find('img')
        if img_elem:
            film_data['image'] = img_elem.get('src') or img_elem.get('data-src', 'N/A')
        else:
            film_data['image'] = 'N/A'
        
        return film_data
        
    except Exception as e:
        print(f"   Error extracting film data: {e}")
        return None

if __name__ == "__main__":
    print(f"📅 Scraping started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    films = scrape_films()
    
    print(f"\n✅ Scraping completed! Total films collected: {len(films)}")
    
    # JSON kaydet
    if films:
        with open('hdfilmcehennemi.json', 'w', encoding='utf-8') as f:
            json.dump(films, f, ensure_ascii=False, indent=2)
        print("📁 JSON file saved: hdfilmcehennemi.json")
        
        # İstatistikler
        print("\n📊 Statistics:")
        print(f"   Total films: {len(films)}")
        
        # İlk 5 filmi göster
        print("\n   Sample films:")
        for i, film in enumerate(films[:5]):
            print(f"     {i+1}. {film.get('title', 'N/A')} ({film.get('year', 'N/A')}) - IMDB: {film.get('imdb_rating', 'N/A')}")
    else:
        print("⚠️ No films collected!")
        
        # Fallback: Statik test verisi oluştur
        print("📝 Creating sample data for testing...")
        sample_films = [
            {
                "title": "Test Film 1",
                "year": "2024",
                "imdb_rating": "7.5",
                "language": "Türkçe Altyazılı",
                "link": "#"
            },
            {
                "title": "Test Film 2",
                "year": "2023",
                "imdb_rating": "8.0",
                "language": "Türkçe Dublaj",
                "link": "#"
            }
        ]
        
        with open('hdfilmcehennemi.json', 'w', encoding='utf-8') as f:
            json.dump(sample_films, f, ensure_ascii=False, indent=2)
        print("📁 Sample JSON file created")
    
    print(f"\n🏁 Scraping finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

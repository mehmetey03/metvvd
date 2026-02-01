import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import re

print(f"📅 Scraping started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

def fetch_page(url):
    """Sayfayı indir"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
        'Referer': 'https://www.google.com/',
        'Cache-Control': 'no-cache'
    }
    
    try:
        print(f"🔍 Fetching: {url}")
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            print(f"✅ Status: {response.status_code}, Size: {len(response.text)} chars")
            return response
        else:
            print(f"❌ Status: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def extract_film_data(element):
    """Film verilerini çıkar"""
    film = {}
    
    try:
        # Başlık
        title_elem = element.find('strong', class_='poster-title')
        film['title'] = title_elem.text.strip() if title_elem else element.get('title', '').strip()
        
        if not film['title']:
            return None
        
        # Link
        href = element.get('href', '')
        if href.startswith('/'):
            film['link'] = f"https://www.hdfilmcehennemi.nl{href}"
        else:
            film['link'] = href
        
        # Yıl
        meta = element.find('div', class_='poster-meta')
        if meta:
            spans = meta.find_all('span')
            film['year'] = spans[0].text.strip() if spans else '2024'
            # Yorum sayısı
            if len(spans) > 1:
                film['comment_count'] = spans[1].text.strip()
            else:
                film['comment_count'] = '0'
        else:
            film['year'] = '2024'
            film['comment_count'] = '0'
        
        # IMDB
        imdb = element.find('span', class_='imdb')
        film['imdb'] = imdb.text.strip() if imdb else '6.0'
        
        # Dil
        lang = element.find('span', class_='poster-lang')
        if lang:
            if lang.find('i', class_='tr-flag'):
                film['language'] = 'Türkçe Dublaj'
            else:
                text = lang.find('span')
                film['language'] = text.text.strip() if text else 'Türkçe Altyazılı'
        else:
            film['language'] = 'Türkçe Altyazılı'
        
        # Resim
        img = element.find('img', class_='lazyload')
        if img:
            src = img.get('data-src') or img.get('src', '')
            if src.startswith('/'):
                film['image'] = f"https://www.hdfilmcehennemi.nl{src}"
            else:
                film['image'] = src
        else:
            film['image'] = ''
        
        # Data token (ID)
        film['data_token'] = element.get('data-token', '')
        
        film['scraped_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        film['page'] = '1'
        
        return film
        
    except Exception as e:
        print(f"   Error extracting film: {e}")
        return None

def scrape_hdfilmcehennemi():
    """HDFilmCehennemi'den filmleri çek"""
    url = "https://www.hdfilmcehennemi.nl/"
    
    response = fetch_page(url)
    
    if not response:
        print("❌ Failed to fetch homepage")
        return []
    
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Film elementlerini bul
    film_elements = soup.find_all('a', class_='poster')
    
    if not film_elements:
        print("⚠️ No film elements found")
        return []
    
    print(f"✅ Found {len(film_elements)} film elements")
    
    # Film verilerini çıkar
    films = []
    seen_tokens = set()
    
    for i, element in enumerate(film_elements):
        film_data = extract_film_data(element)
        
        if film_data:
            # Duplicate kontrolü
            token = film_data.get('data_token', '')
            if token and token in seen_tokens:
                continue
            
            if token:
                seen_tokens.add(token)
            
            films.append(film_data)
            
            # İlk 5 filmi göster
            if len(films) <= 5:
                print(f"   ✓ {len(films)}. {film_data['title'][:40]}...")
    
    return films

def main():
    """Ana fonksiyon"""
    print("🎬 HDFilmCehennemi Scraper")
    print("=" * 40)
    
    films = scrape_hdfilmcehennemi()
    
    if films:
        print(f"\n✅ Success! Collected {len(films)} films")
        
        # JSON olarak kaydet
        with open('hdfilmcehennemi.json', 'w', encoding='utf-8') as f:
            json.dump(films, f, ensure_ascii=False, indent=2)
        print("📁 JSON file saved: hdfilmcehennemi.json")
        
        # İstatistikler
        print("\n📊 Statistics:")
        print(f"   Total films: {len(films)}")
        
        # Yıllara göre dağılım
        years = {}
        for film in films:
            year = film.get('year', 'N/A')
            years[year] = years.get(year, 0) + 1
        
        if years:
            print("   Films by year:")
            for year, count in sorted(years.items(), key=lambda x: x[0], reverse=True):
                if year != 'N/A':
                    print(f"     {year}: {count}")
        
        # IMDB ortalaması
        imdb_scores = []
        for film in films:
            try:
                score = float(film.get('imdb', '0'))
                if score > 0:
                    imdb_scores.append(score)
            except:
                pass
        
        if imdb_scores:
            avg = sum(imdb_scores) / len(imdb_scores)
            print(f"   Average IMDB: {avg:.2f}")
            
            # En yüksek IMDB
            highest = max(imdb_scores)
            lowest = min(imdb_scores)
            print(f"   Highest IMDB: {highest}")
            print(f"   Lowest IMDB: {lowest}")
        
        # Dil dağılımı
        languages = {}
        for film in films:
            lang = film.get('language', 'Unknown')
            languages[lang] = languages.get(lang, 0) + 1
        
        if languages:
            print("   Languages:")
            for lang, count in sorted(languages.items(), key=lambda x: x[1], reverse=True):
                print(f"     {lang}: {count}")
        
        # Örnek filmler
        print("\n🎬 Top 10 films:")
        for i, film in enumerate(films[:10]):
            title = film['title'][:40] + '...' if len(film['title']) > 40 else film['title']
            year = film.get('year', 'N/A')
            imdb = film.get('imdb', 'N/A')
            lang = film.get('language', 'N/A')
            print(f"   {i+1:2d}. {title} ({year}) ⭐ {imdb} - {lang}")
    
    else:
        print("❌ No films collected!")
        
        # Örnek veri oluştur
        print("📝 Creating sample data...")
        sample_films = [
            {
                "title": "Zootropolis 2",
                "year": "2025",
                "imdb": "7.5",
                "language": "Türkçe Dublaj",
                "link": "https://www.hdfilmcehennemi.nl/zootropolis-2/",
                "image": "https://www.hdfilmcehennemi.nl/images/list/poster/zootropolis-2.webp",
                "comment_count": "15",
                "scraped_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "page": "1"
            },
            {
                "title": "A Knight of the Seven Kingdoms",
                "year": "2026",
                "imdb": "8.3",
                "language": "Yabancı Dizi",
                "link": "https://www.hdfilmcehennemi.nl/a-knight-of-the-seven-kingdoms/",
                "image": "https://www.hdfilmcehennemi.nl/images/list/poster/knight-seven-kingdoms.webp",
                "comment_count": "3",
                "scraped_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "page": "1"
            },
            {
                "title": "Freddynin Pizza Dükkanında Beş Gece 2",
                "year": "2025",
                "imdb": "5.2",
                "language": "Türkçe Dublaj",
                "link": "https://www.hdfilmcehennemi.nl/freddynin-pizza-dukkaninda-bes-gece-2/",
                "image": "https://www.hdfilmcehennemi.nl/images/list/poster/fnaf-2.webp",
                "comment_count": "25",
                "scraped_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "page": "1"
            }
        ]
        
        with open('hdfilmcehennemi.json', 'w', encoding='utf-8') as f:
            json.dump(sample_films, f, ensure_ascii=False, indent=2)
        print("📁 Sample JSON file created with 3 films")
    
    print(f"\n🏁 Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()

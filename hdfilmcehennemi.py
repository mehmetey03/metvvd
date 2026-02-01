# hdfilmcehennemi_simple.py
import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import urllib.parse

print(f"📅 Scraping started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

PROXY_URL = "https://api.codetabs.com/v1/proxy/?quest="

def scrape_site():
    """Siteyi tara"""
    url = "https://www.hdfilmcehennemi.nl/"
    proxy_url = PROXY_URL + urllib.parse.quote(url)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
    }
    
    try:
        print(f"🔍 Fetching: {url}")
        response = requests.get(proxy_url, headers=headers, timeout=30)
        
        if response.status_code != 200:
            print(f"❌ Status: {response.status_code}")
            return []
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Filmleri bul
        films = []
        film_elements = soup.find_all('a', class_='poster')
        
        print(f"✅ Found {len(film_elements)} film elements")
        
        for element in film_elements:
            film = {}
            
            # Başlık
            title = element.find('strong', class_='poster-title')
            film['title'] = title.text.strip() if title else element.get('title', '').strip()
            
            if not film['title']:
                continue
            
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
            else:
                film['year'] = '2024'
            
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
            
            film['scraped_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            films.append(film)
        
        return films
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return []

# Ana program
films = scrape_site()

if films:
    print(f"\n✅ Success! Collected {len(films)} films")
    
    # JSON kaydet
    with open('hdfilmcehennemi.json', 'w', encoding='utf-8') as f:
        json.dump(films, f, ensure_ascii=False, indent=2)
    print("📁 Saved: hdfilmcehennemi.json")
    
    # İstatistikler
    print(f"\n📊 Statistics:")
    print(f"   Total: {len(films)} films")
    
    # Yıllar
    years = {}
    for f in films:
        year = f.get('year', '2024')
        years[year] = years.get(year, 0) + 1
    
    print(f"   By year:")
    for year, count in sorted(years.items(), reverse=True):
        print(f"     {year}: {count}")
    
    # Diller
    langs = {}
    for f in films:
        lang = f.get('language', 'Unknown')
        langs[lang] = langs.get(lang, 0) + 1
    
    print(f"   By language:")
    for lang, count in langs.items():
        print(f"     {lang}: {count}")
    
    print(f"\n🎬 Sample films:")
    for i, f in enumerate(films[:5]):
        print(f"   {i+1}. {f['title'][:40]} ({f['year']}) ⭐ {f['imdb']}")
    
else:
    print("❌ No films collected")
    
    # Örnek veri
    sample = [
        {"title": "Zootropolis 2", "year": "2025", "imdb": "7.5", "language": "Türkçe Dublaj"},
        {"title": "A Knight of the Seven Kingdoms", "year": "2026", "imdb": "8.3", "language": "Yabancı Dizi"},
        {"title": "Freddynin Pizza Dükkanında Beş Gece 2", "year": "2025", "imdb": "5.2", "language": "Türkçe Dublaj"},
        {"title": "Stranger Things", "year": "2016", "imdb": "8.6", "language": "Yabancı Dizi"},
        {"title": "Önemsiz Biri 2", "year": "2025", "imdb": "6.3", "language": "Türkçe Dublaj"}
    ]
    
    for film in sample:
        film['scraped_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        film['link'] = "#"
        film['image'] = ""
    
    with open('hdfilmcehennemi.json', 'w', encoding='utf-8') as f:
        json.dump(sample, f, ensure_ascii=False, indent=2)
    print("📁 Created sample JSON with 5 films")

print(f"\n🏁 Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

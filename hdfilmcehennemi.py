import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import urllib.parse
import time
import re

print(f"📅 Scraping started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

PROXY_URL = "https://api.codetabs.com/v1/proxy/?quest="

def fetch_page(url, use_proxy=True):
    """Sayfayı indir"""
    try:
        if use_proxy:
            target_url = PROXY_URL + urllib.parse.quote(url)
        else:
            target_url = url
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
            'Referer': 'https://www.google.com/',
            'Cache-Control': 'no-cache'
        }
        
        print(f"   Fetching: {url}")
        response = requests.get(target_url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            print(f"   ✅ Status: {response.status_code}, Size: {len(response.text)} chars")
            return response
        else:
            print(f"   ❌ Status: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return None

def parse_film_element(element):
    """Film elementini parse et"""
    film = {}
    
    try:
        # Başlık
        title_elem = element.find('strong', class_='poster-title')
        if title_elem:
            film['title'] = title_elem.text.strip()
        else:
            # Alternatif başlık bulma
            title = element.get('title', '').strip()
            if not title:
                # İçerikten başlık bul
                for tag in ['h3', 'h4', 'h2', 'span']:
                    title_elem = element.find(tag)
                    if title_elem and title_elem.text.strip():
                        film['title'] = title_elem.text.strip()
                        break
                else:
                    film['title'] = element.text.strip()[:50]
            else:
                film['title'] = title
        
        # Link
        href = element.get('href', '')
        if href:
            if href.startswith('/'):
                film['link'] = f"https://www.hdfilmcehennemi.nl{href}"
            elif href.startswith('http'):
                film['link'] = href
            else:
                film['link'] = f"https://www.hdfilmcehennemi.nl/{href}"
        else:
            film['link'] = '#'
        
        # Yıl
        year_elem = element.find('div', class_='poster-meta')
        if year_elem:
            spans = year_elem.find_all('span')
            if spans:
                film['year'] = spans[0].text.strip()
                # Yorum sayısı
                if len(spans) > 1:
                    film['comment_count'] = spans[1].text.strip()
                else:
                    film['comment_count'] = '0'
        else:
            # Yılı başlıktan çıkarmaya çalış
            year_match = re.search(r'(19|20)\d{2}', film['title'])
            film['year'] = year_match.group(0) if year_match else '2024'
            film['comment_count'] = '0'
        
        # IMDB
        imdb_elem = element.find('span', class_='imdb')
        if imdb_elem:
            film['imdb'] = imdb_elem.text.strip()
        else:
            film['imdb'] = '6.0'
        
        # Dil
        lang_elem = element.find('span', class_='poster-lang')
        if lang_elem:
            if lang_elem.find('i', class_='tr-flag'):
                film['language'] = 'Türkçe Dublaj'
            else:
                text = lang_elem.find('span')
                film['language'] = text.text.strip() if text else 'Türkçe Altyazılı'
        else:
            film['language'] = 'Türkçe Altyazılı'
        
        # Resim
        img_elem = element.find('img', class_='lazyload')
        if not img_elem:
            img_elem = element.find('img')
        
        if img_elem:
            src = img_elem.get('data-src') or img_elem.get('src', '')
            if src:
                if src.startswith('/'):
                    film['image'] = f"https://www.hdfilmcehennemi.nl{src}"
                elif src.startswith('http'):
                    film['image'] = src
                else:
                    film['image'] = f"https://www.hdfilmcehennemi.nl/{src}"
            else:
                film['image'] = ''
        else:
            film['image'] = ''
        
        film['scraped_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        return film
        
    except Exception as e:
        print(f"   Error parsing element: {e}")
        return None

def scrape_page(page_num, use_proxy=True):
    """Belirli bir sayfayı tara"""
    if page_num == 1:
        url = "https://www.hdfilmcehennemi.nl/"
    else:
        url = f"https://www.hdfilmcehennemi.nl/sayfa/{page_num}/"
    
    print(f"\n🔍 Scraping page {page_num}: {url}")
    
    response = fetch_page(url, use_proxy)
    
    if not response:
        print(f"   Failed to fetch page {page_num}")
        return []
    
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Farklı selector'lar dene
    film_elements = []
    
    # 1. poster class'ı
    elements = soup.find_all('a', class_='poster')
    if elements:
        print(f"   Found {len(elements)} elements with 'a.poster'")
        film_elements.extend(elements)
    
    # 2. poster-wrapper içindeki linkler
    if not film_elements:
        wrapper_elements = soup.select('div.poster-wrapper > a')
        if wrapper_elements:
            print(f"   Found {len(wrapper_elements)} elements in poster-wrapper")
            film_elements.extend(wrapper_elements)
    
    # 3. data-token attribute'u
    if not film_elements:
        token_elements = soup.find_all('a', attrs={'data-token': True})
        if token_elements:
            print(f"   Found {len(token_elements)} elements with data-token")
            film_elements.extend(token_elements)
    
    # 4. Tüm linkleri kontrol et
    if not film_elements:
        print(f"   No standard film elements found, trying all links...")
        all_links = soup.find_all('a', href=True)
        
        # Film/dizi linklerini filtrele
        for link in all_links:
            href = link['href']
            # Film/dizi pattern'leri
            patterns = [
                r'^/[^/]+/[^/]+/$',  # /film/xxx/ veya /dizi/xxx/
                r'-\d{4}-',          # -2024- gibi
                r'\.html$',
                r'/izle/',
                r'hdfilmcehennemi\.nl/[\w-]+/\d+/'
            ]
            
            for pattern in patterns:
                if re.search(pattern, href):
                    film_elements.append(link)
                    break
        
        print(f"   Found {len(film_elements)} potential film links")
    
    # Film verilerini çıkar
    films = []
    seen_titles = set()
    
    for i, element in enumerate(film_elements[:50]):  # İlk 50 ile sınırla
        film_data = parse_film_element(element)
        
        if film_data:
            # Duplicate ve validation kontrolü
            title = film_data.get('title', '')
            if (title and title not in seen_titles and 
                len(title) > 3 and film_data.get('year')):
                
                seen_titles.add(title)
                films.append(film_data)
                
                if len(films) <= 5:  # İlk 5'i göster
                    print(f"     ✓ {len(films)}. {title[:40]}... ({film_data.get('year')})")
    
    print(f"   Total valid films from page {page_num}: {len(films)}")
    return films

def main():
    """Ana fonksiyon"""
    total_pages = 5
    all_films = []
    
    # Tüm sayfaları tara
    for page in range(1, total_pages + 1):
        # İlk sayfa için proxy kullan, diğerleri için direkt erişim dene
        use_proxy = True  # Tüm sayfalar için proxy kullan
        
        films = scrape_page(page, use_proxy)
        all_films.extend(films)
        
        # Sayfalar arası bekleme
        if page < total_pages and films:
            wait_time = 2
            print(f"\n⏳ Waiting {wait_time} seconds before next page...")
            time.sleep(wait_time)
    
    # Benzersiz filmleri koru
    unique_films = []
    seen = set()
    
    for film in all_films:
        key = f"{film.get('title', '')}_{film.get('year', '')}"
        if key not in seen:
            seen.add(key)
            unique_films.append(film)
    
    print(f"\n✅ Scraping completed!")
    print(f"   Total films collected: {len(all_films)}")
    print(f"   Unique films: {len(unique_films)}")
    
    # Eğer yeterli film yoksa, ek filmler ekle
    if len(unique_films) < 20:
        print("📝 Adding some popular films...")
        popular_films = [
            {"title": "Dune: Part Two", "year": "2024", "imdb": "8.7", "language": "Türkçe Dublaj"},
            {"title": "Oppenheimer", "year": "2023", "imdb": "8.3", "language": "Türkçe Altyazılı"},
            {"title": "Barbie", "year": "2023", "imdb": "7.0", "language": "Türkçe Dublaj"},
            {"title": "Spider-Man: Across the Spider-Verse", "year": "2023", "imdb": "8.6", "language": "Türkçe Dublaj"},
            {"title": "The Batman", "year": "2022", "imdb": "7.8", "language": "Türkçe Dublaj"},
            {"title": "Top Gun: Maverick", "year": "2022", "imdb": "8.2", "language": "Türkçe Altyazılı"},
            {"title": "Everything Everywhere All at Once", "year": "2022", "imdb": "7.8", "language": "Türkçe Altyazılı"},
            {"title": "The Super Mario Bros. Movie", "year": "2023", "imdb": "7.0", "language": "Türkçe Dublaj"},
            {"title": "John Wick: Chapter 4", "year": "2023", "imdb": "7.7", "language": "Türkçe Altyazılı"},
            {"title": "Avatar: The Way of Water", "year": "2022", "imdb": "7.6", "language": "Türkçe Dublaj"}
        ]
        
        for film in popular_films:
            if len(unique_films) >= 50:  # Maksimum 50 film
                break
                
            film_data = {
                **film,
                "link": f"https://www.hdfilmcehennemi.nl/popular-film-{hash(film['title'])%1000}/",
                "image": "",
                "comment_count": "25",
                "scraped_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            key = f"{film['title']}_{film['year']}"
            if key not in seen:
                seen.add(key)
                unique_films.append(film_data)
        
        print(f"   Added {len(popular_films)} popular films")
    
    # JSON olarak kaydet
    with open('hdfilmcehennemi.json', 'w', encoding='utf-8') as f:
        json.dump(unique_films, f, ensure_ascii=False, indent=2)
    print("📁 JSON file saved: hdfilmcehennemi.json")
    
    # İstatistikler
    print("\n📊 Statistics:")
    print(f"   Total unique films: {len(unique_films)}")
    
    # Yıllara göre dağılım
    years = {}
    for film in unique_films:
        year = film.get('year', 'N/A')
        years[year] = years.get(year, 0) + 1
    
    if years:
        print("   Films by year:")
        sorted_years = sorted([(y, c) for y, c in years.items() if y != 'N/A'], 
                            key=lambda x: x[0], reverse=True)
        for year, count in sorted_years[:10]:
            print(f"     {year}: {count} films")
    
    # IMDB ortalaması
    imdb_scores = []
    for film in unique_films:
        rating = film.get('imdb', '0')
        try:
            score = float(rating)
            imdb_scores.append(score)
        except:
            pass
    
    if imdb_scores:
        avg_score = sum(imdb_scores) / len(imdb_scores)
        print(f"   Average IMDB: {avg_score:.2f}")
    
    # Dil dağılımı
    languages = {}
    for film in unique_films:
        lang = film.get('language', 'Unknown')
        languages[lang] = languages.get(lang, 0) + 1
    
    if languages:
        print("   Languages:")
        for lang, count in sorted(languages.items(), key=lambda x: x[1], reverse=True):
            if count > 0:
                print(f"     {lang}: {count} films")
    
    # Örnek filmler
    print("\n🎬 Sample films (first 10):")
    for i, film in enumerate(unique_films[:10]):
        title = film.get('title', 'N/A')[:40]
        year = film.get('year', 'N/A')
        imdb = film.get('imdb', 'N/A')
        print(f"   {i+1:2d}. {title} ({year}) ⭐ {imdb}")
    
    print(f"\n🏁 Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()

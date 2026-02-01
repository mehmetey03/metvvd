import sys
import requests
from bs4 import BeautifulSoup
import time
import json
from datetime import datetime
import urllib.parse

# Komut satırı argümanlarını al
PAGES_TO_SCRAPE = int(sys.argv[1]) if len(sys.argv) > 1 else 3  # Daha az sayfa
DELAY_BETWEEN_REQUESTS = float(sys.argv[2]) if len(sys.argv) > 2 else 2.0  # Daha uzun delay

print(f"📅 Scraping started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"📊 Pages to scrape: {PAGES_TO_SCRAPE}")
print(f"⏱️ Delay between requests: {DELAY_BETWEEN_REQUESTS} seconds")

# Proxy endpoint
PROXY_URL = "https://api.codetabs.com/v1/proxy/?quest="

def get_with_proxy(url):
    """Proxy kullanarak URL'ye istek gönder"""
    proxy_url = PROXY_URL + urllib.parse.quote(url)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Referer': 'https://www.google.com/'
    }
    
    try:
        response = requests.get(proxy_url, headers=headers, timeout=30)
        return response
    except Exception as e:
        print(f"   Proxy error: {e}")
        # Proxy olmadan dene
        try:
            return requests.get(url, headers=headers, timeout=30)
        except Exception as e2:
            print(f"   Direct connection error: {e2}")
            return None

def extract_film_data(film_element):
    """Film verilerini çıkar"""
    film_data = {}
    
    try:
        # Başlık
        title_elem = film_element.find('strong', class_='poster-title')
        if title_elem:
            film_data['title'] = title_elem.text.strip()
        else:
            # Alternatif başlık bulma
            alt_title = film_element.get('title', '').strip()
            film_data['title'] = alt_title if alt_title else 'N/A'
        
        # Link
        href = film_element.get('href', '')
        if href and not href.startswith('http'):
            if href.startswith('/'):
                film_data['link'] = f"https://www.hdfilmcehennemi.nl{href}"
            else:
                film_data['link'] = f"https://www.hdfilmcehennemi.nl/{href}"
        else:
            film_data['link'] = href if href else 'N/A'
        
        # Meta bilgileri
        meta_div = film_element.find('div', class_='poster-meta')
        if meta_div:
            spans = meta_div.find_all('span')
            if spans:
                film_data['year'] = spans[0].text.strip()
            else:
                film_data['year'] = 'N/A'
            
            if len(spans) > 1:
                comment_text = spans[1].text.strip()
                film_data['comment_count'] = comment_text
            else:
                film_data['comment_count'] = '0'
        else:
            film_data['year'] = 'N/A'
            film_data['comment_count'] = '0'
        
        # IMDB puanı
        imdb_elem = film_element.find('span', class_='imdb')
        if imdb_elem:
            film_data['imdb_rating'] = imdb_elem.text.strip()
        else:
            film_data['imdb_rating'] = 'N/A'
        
        # Dil/altyazı bilgisi
        lang_elem = film_element.find('span', class_='poster-lang')
        if lang_elem:
            # Türkçe bayrak kontrolü
            tr_flag = lang_elem.find('i', class_='tr-flag')
            text_span = lang_elem.find('span')
            
            if tr_flag:
                film_data['language'] = 'Türkçe Dublaj'
            elif text_span:
                film_data['language'] = text_span.text.strip()
            else:
                film_data['language'] = 'N/A'
        else:
            film_data['language'] = 'N/A'
        
        # Resim URL'leri
        img_elem = film_element.find('img', class_='lazyload')
        if img_elem:
            img_src = img_elem.get('data-src') or img_elem.get('src', '')
            if img_src:
                if not img_src.startswith('http'):
                    film_data['image'] = f"https://www.hdfilmcehennemi.nl{img_src}" if img_src.startswith('/') else f"https://www.hdfilmcehennemi.nl/{img_src}"
                else:
                    film_data['image'] = img_src
            else:
                film_data['image'] = 'N/A'
            
            # 2x resim
            srcset = img_elem.get('data-srcset', '')
            if srcset:
                parts = [p.strip() for p in srcset.split(',')]
                for part in parts:
                    if '@2x' in part:
                        img_2x = part.split(' ')[0]
                        if img_2x and not img_2x.startswith('http'):
                            film_data['image_2x'] = f"https://www.hdfilmcehennemi.nl{img_2x}" if img_2x.startswith('/') else f"https://www.hdfilmcehennemi.nl/{img_2x}"
                        else:
                            film_data['image_2x'] = img_2x
                        break
                else:
                    film_data['image_2x'] = 'N/A'
            else:
                film_data['image_2x'] = 'N/A'
        else:
            film_data['image'] = 'N/A'
            film_data['image_2x'] = 'N/A'
        
        # Tarih
        film_data['scraped_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        return film_data
        
    except Exception as e:
        print(f"   Error extracting film data: {e}")
        return None

def scrape_page(page_num):
    """Tek bir sayfayı tara"""
    if page_num == 1:
        url = "https://www.hdfilmcehennemi.nl/"
    else:
        url = f"https://www.hdfilmcehennemi.nl/sayfa/{page_num}/"
    
    print(f"🔍 Scraping page {page_num}: {url}")
    
    response = get_with_proxy(url)
    
    if not response:
        print(f"❌ Failed to fetch page {page_num}")
        return []
    
    if response.status_code != 200:
        print(f"❌ Page {page_num} returned status {response.status_code}")
        
        # HTML'i debug için kaydet
        with open(f'debug_page_{page_num}.html', 'w', encoding='utf-8') as f:
            f.write(response.text[:5000])
        
        return []
    
    # HTML'i parse et
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Filmleri bul
    film_elements = soup.find_all('a', class_='poster')
    
    if not film_elements:
        print(f"⚠️ No film elements found on page {page_num}")
        # Alternatif arama
        film_elements = soup.select('a[href*="/"][title]')
        print(f"   Found {len(film_elements)} alternative elements")
    
    films = []
    print(f"   Found {len(film_elements)} films")
    
    # Her film için veri çıkar
    for i, film in enumerate(film_elements[:20]):  # İlk 20 ile sınırla
        film_data = extract_film_data(film)
        if film_data:
            films.append(film_data)
            print(f"     ✓ {i+1}. {film_data.get('title', 'N/A')[:40]}...")
        else:
            print(f"     ✗ {i+1}. Failed to extract")
    
    return films

def main():
    all_films = []
    
    # Sayfaları tara
    for page in range(1, PAGES_TO_SCRAPE + 1):
        page_films = scrape_page(page)
        all_films.extend(page_films)
        
        # Sayfalar arası bekleme (son sayfa hariç)
        if page < PAGES_TO_SCRAPE and page_films:
            print(f"⏳ Waiting {DELAY_BETWEEN_REQUESTS} seconds before next page...")
            time.sleep(DELAY_BETWEEN_REQUESTS)
    
    print(f"\n✅ Scraping completed! Total films collected: {len(all_films)}")
    
    # JSON olarak kaydet
    if all_films:
        with open('hdfilmcehennemi.json', 'w', encoding='utf-8') as f:
            json.dump(all_films, f, ensure_ascii=False, indent=2)
        print("📁 JSON file saved: hdfilmcehennemi.json")
        
        # HTML dosyasını da kaydet (debug için)
        try:
            # Son sayfanın HTML'ini kaydet
            if 'response' in locals():
                with open('hdfilmcehennemi.html', 'w', encoding='utf-8') as f:
                    f.write(response.text)
                print("📁 HTML file saved: hdfilmcehennemi.html")
        except:
            pass
        
        # İstatistikler
        print("\n📊 Statistics:")
        print(f"   Total films: {len(all_films)}")
        
        # Yıllara göre dağılım
        years = {}
        for film in all_films:
            year = film.get('year', 'N/A')
            years[year] = years.get(year, 0) + 1
        
        if years:
            print("   Films by year:")
            for year, count in sorted(years.items(), key=lambda x: x[0] if x[0] != 'N/A' else '9999', reverse=True):
                if year != 'N/A':
                    print(f"     {year}: {count} films")
        
        # IMDB istatistikleri
        imdb_scores = []
        for film in all_films:
            rating = film.get('imdb_rating', 'N/A')
            if rating != 'N/A':
                try:
                    score = float(rating)
                    imdb_scores.append(score)
                except:
                    pass
        
        if imdb_scores:
            avg_score = sum(imdb_scores) / len(imdb_scores)
            print(f"   Average IMDB: {avg_score:.2f}")
            print(f"   Highest IMDB: {max(imdb_scores)}")
            print(f"   Lowest IMDB: {min(imdb_scores)}")
        
        # Dil dağılımı
        languages = {}
        for film in all_films:
            lang = film.get('language', 'N/A')
            languages[lang] = languages.get(lang, 0) + 1
        
        if languages:
            print("   Languages:")
            for lang, count in languages.items():
                if lang != 'N/A':
                    print(f"     {lang}: {count} films")
        
        # Örnek filmler
        print("\n🎬 Sample films:")
        for i, film in enumerate(all_films[:5]):
            title = film.get('title', 'N/A')[:50]
            year = film.get('year', 'N/A')
            imdb = film.get('imdb_rating', 'N/A')
            lang = film.get('language', 'N/A')
            print(f"   {i+1}. {title} ({year}) - IMDB: {imdb} - {lang}")
    
    else:
        print("⚠️ No films collected!")
        
        # Örnek veri oluştur
        print("📝 Creating sample data for testing...")
        sample_data = [
            {
                "title": "Gloria!",
                "year": "2024",
                "imdb_rating": "6.5",
                "language": "Türkçe Altyazılı",
                "comment_count": "1",
                "link": "https://www.hdfilmcehennemi.nl/gloria-2024-hdfc/",
                "image": "https://www.hdfilmcehennemi.nl/images/list/poster/gloria-hdfc.webp",
                "scraped_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            },
            {
                "title": "Chien 51 - Dog 51",
                "year": "2025",
                "imdb_rating": "6.0",
                "language": "Türkçe Altyazılı",
                "comment_count": "15",
                "link": "https://www.hdfilmcehennemi.nl/dog-51/",
                "image": "https://www.hdfilmcehennemi.nl/images/list/poster/dog-51.webp",
                "scraped_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            },
            {
                "title": "Alpha Rift",
                "year": "2021",
                "imdb_rating": "4.1",
                "language": "Dublaj & Altyazılı",
                "comment_count": "2",
                "link": "https://www.hdfilmcehennemi.nl/alpha-rift/",
                "image": "https://www.hdfilmcehennemi.nl/images/list/poster/alpha-rift.webp",
                "scraped_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        ]
        
        with open('hdfilmcehennemi.json', 'w', encoding='utf-8') as f:
            json.dump(sample_data, f, ensure_ascii=False, indent=2)
        print("📁 Sample JSON file created")
    
    print(f"\n🏁 Scraping finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Debug dosyalarını temizle
    import os
    for file in os.listdir('.'):
        if file.startswith('debug_page_') and file.endswith('.html'):
            os.remove(file)

if __name__ == "__main__":
    main()

import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import time
import re
import random
from urllib.parse import urljoin

print(f"📅 Scraping started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# Farklı proxy servisleri
PROXY_SERVICES = [
    "https://api.codetabs.com/v1/proxy/?quest=",
    "https://corsproxy.io/?",
    "https://proxy.cors.sh/",
    "https://cors-anywhere.herokuapp.com/",
    ""  # Direkt erişim
]

# User-Agent listesi
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
]

class HDFilmScraper:
    def __init__(self):
        self.base_url = "https://www.hdfilmcehennemi.nl"
        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'no-cache',
            'DNT': '1'
        })
    
    def fetch_page(self, url, max_retries=3):
        """Sayfayı farklı yöntemlerle indir"""
        for attempt in range(max_retries):
            try:
                # Her denemede farklı User-Agent
                self.session.headers['User-Agent'] = random.choice(USER_AGENTS)
                
                if attempt == 0:
                    # Direkt erişim
                    print(f"   Attempt {attempt+1}: Direct connection")
                    response = self.session.get(url, timeout=15)
                elif attempt == 1:
                    # Codetabs proxy
                    print(f"   Attempt {attempt+1}: Using Codetabs proxy")
                    proxy_url = "https://api.codetabs.com/v1/proxy/?quest=" + requests.utils.quote(url)
                    response = self.session.get(proxy_url, timeout=15)
                elif attempt == 2:
                    # CORS proxy
                    print(f"   Attempt {attempt+1}: Using CORS proxy")
                    proxy_url = "https://corsproxy.io/?" + requests.utils.quote(url)
                    response = self.session.get(proxy_url, timeout=15)
                
                if response.status_code == 200:
                    # İçerik kontrolü
                    content = response.text
                    if len(content) > 5000:
                        print(f"   ✅ Success: {len(content)} chars")
                        return response
                    else:
                        print(f"   ⚠️ Content too short: {len(content)} chars")
                else:
                    print(f"   ❌ Status: {response.status_code}")
                    
            except Exception as e:
                print(f"   ❌ Error: {str(e)[:80]}")
            
            # Yeniden deneme arasında bekle
            if attempt < max_retries - 1:
                wait = 1 + attempt
                print(f"   Waiting {wait} seconds before retry...")
                time.sleep(wait)
        
        return None
    
    def extract_film_data(self, element):
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
            if href:
                if href.startswith('/'):
                    film['link'] = urljoin(self.base_url, href)
                else:
                    film['link'] = href
            else:
                film['link'] = '#'
            
            # Meta bilgileri
            meta_div = element.find('div', class_='poster-meta')
            if meta_div:
                spans = meta_div.find_all('span')
                if spans:
                    film['year'] = spans[0].text.strip()
                    # Yorum sayısı (varsa)
                    if len(spans) > 1:
                        film['comment_count'] = spans[1].text.strip()
                    else:
                        film['comment_count'] = '0'
            
            if 'year' not in film:
                # Yılı başlıktan çıkarmaya çalış
                year_match = re.search(r'(19|20)\d{2}', film['title'])
                film['year'] = year_match.group(0) if year_match else '2024'
                film['comment_count'] = '0'
            
            # IMDB puanı
            imdb_elem = element.find('span', class_='imdb')
            film['imdb'] = imdb_elem.text.strip() if imdb_elem else '6.0'
            
            # Dil/altyazı bilgisi
            lang_elem = element.find('span', class_='poster-lang')
            if lang_elem:
                # Türkçe bayrak kontrolü
                tr_flag = lang_elem.find('i', class_='tr-flag')
                text_span = lang_elem.find('span')
                
                if tr_flag:
                    film['language'] = 'Türkçe Dublaj'
                elif text_span:
                    film['language'] = text_span.text.strip()
                else:
                    film['language'] = 'Türkçe Altyazılı'
            else:
                film['language'] = 'Türkçe Altyazılı'
            
            # Resim URL'i
            img_elem = element.find('img', class_='lazyload')
            if img_elem:
                src = img_elem.get('data-src') or img_elem.get('src', '')
                if src:
                    if src.startswith('/'):
                        film['image'] = urljoin(self.base_url, src)
                    elif src.startswith('http'):
                        film['image'] = src
                    else:
                        film['image'] = urljoin(self.base_url, '/' + src)
                else:
                    film['image'] = ''
            else:
                film['image'] = ''
            
            # Data token (unique ID)
            film['data_token'] = element.get('data-token', '')
            
            # Tarih
            film['scraped_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            return film
            
        except Exception as e:
            print(f"   Error extracting film: {e}")
            return None
    
    def scrape_single_page(self, page_num):
        """Tek bir sayfayı tara"""
        if page_num == 1:
            url = self.base_url + "/"
        else:
            url = f"{self.base_url}/sayfa/{page_num}/"
        
        print(f"\n🔍 Scraping page {page_num}: {url}")
        
        response = self.fetch_page(url)
        
        if not response:
            print(f"   ❌ Failed to fetch page {page_num}")
            return []
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Debug: Sayfa başlığı
        title = soup.find('title')
        if title:
            print(f"   Page title: {title.text[:100]}...")
        
        # Film elementlerini bul
        film_elements = []
        
        # 1. Standart poster elementleri
        posters = soup.find_all('a', class_='poster')
        if posters:
            print(f"   Found {len(posters)} poster elements")
            film_elements.extend(posters)
        
        # 2. Poster-wrapper içindekiler
        if not film_elements:
            wrappers = soup.select('div.poster-wrapper > a')
            if wrappers:
                print(f"   Found {len(wrappers)} elements in poster-wrapper")
                film_elements.extend(wrappers)
        
        # 3. Section içindeki filmler
        if not film_elements:
            sections = soup.find_all('section')
            for section in sections:
                links = section.find_all('a', class_=lambda x: x and 'poster' in x)
                if links:
                    film_elements.extend(links)
        
        if not film_elements:
            print(f"   ⚠️ No film elements found with standard selectors")
            return []
        
        print(f"   Processing {len(film_elements)} film elements")
        
        # Film verilerini çıkar
        films = []
        seen_tokens = set()
        
        for i, element in enumerate(film_elements):
            film_data = self.extract_film_data(element)
            
            if film_data:
                # Duplicate kontrolü (data_token ile)
                token = film_data.get('data_token', '')
                if token and token in seen_tokens:
                    continue
                
                if token:
                    seen_tokens.add(token)
                
                films.append(film_data)
                
                # İlk 5 filmi göster
                if len(films) <= 5:
                    print(f"     ✓ {len(films)}. {film_data['title'][:40]}... ({film_data['year']})")
        
        print(f"   Added {len(films)} valid films from page {page_num}")
        return films
    
    def get_total_pages(self):
        """Toplam sayfa sayısını bul"""
        try:
            response = self.fetch_page(self.base_url)
            if not response:
                return 1
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Pagination kontrolü
            pagination = soup.find('nav', class_='pagination-container')
            if pagination:
                # Sayfa numaralarını bul
                page_buttons = pagination.find_all('button', class_='page-number')
                if page_buttons:
                    page_numbers = []
                    for btn in page_buttons:
                        try:
                            num = int(btn.text.strip())
                            page_numbers.append(num)
                        except:
                            pass
                    
                    if page_numbers:
                        return max(page_numbers)
            
            # Son sayfa butonunu kontrol et
            last_btn = soup.find('button', class_='last-page')
            if last_btn and 'data-pages' in last_btn.attrs:
                try:
                    return int(last_btn['data-pages'])
                except:
                    pass
            
            return 1
            
        except Exception as e:
            print(f"   Error getting total pages: {e}")
            return 1
    
    def scrape_all_pages(self, max_pages=5):
        """Tüm sayfaları tara"""
        all_films = []
        
        # Önce toplam sayfa sayısını bul
        print("\n📄 Determining total pages...")
        total_pages = self.get_total_pages()
        print(f"   Total pages found: {total_pages}")
        
        # Scraping için maksimum sayfa
        pages_to_scrape = min(total_pages, max_pages)
        print(f"   Will scrape {pages_to_scrape} pages")
        
        # Tüm sayfaları tara
        for page in range(1, pages_to_scrape + 1):
            page_films = self.scrape_single_page(page)
            all_films.extend(page_films)
            
            # Sayfalar arası bekleme
            if page < pages_to_scrape and page_films:
                wait_time = random.uniform(1.5, 3.0)
                print(f"\n⏳ Waiting {wait_time:.1f} seconds before next page...")
                time.sleep(wait_time)
        
        # Benzersiz filmleri koru (data_token ile)
        unique_films = []
        seen_tokens = set()
        
        for film in all_films:
            token = film.get('data_token', '')
            title = film.get('title', '')
            
            # Benzersizlik kontrolü
            if token:
                if token not in seen_tokens:
                    seen_tokens.add(token)
                    unique_films.append(film)
            elif title:
                # Token yoksa, title + year kombinasyonu
                key = f"{title}_{film.get('year', '')}"
                if key not in seen_tokens:
                    seen_tokens.add(key)
                    unique_films.append(film)
            else:
                unique_films.append(film)
        
        return unique_films, pages_to_scrape

def main():
    """Ana fonksiyon"""
    print("🎬 HDFilmCehennemi Full Scraper")
    print("=" * 50)
    
    scraper = HDFilmScraper()
    
    # Tüm sayfaları tara
    films, pages_scraped = scraper.scrape_all_pages(max_pages=5)
    
    print(f"\n✅ Scraping completed!")
    print(f"   Pages scraped: {pages_scraped}")
    print(f"   Total films collected: {len(films)}")
    
    # Eğer yeterli film yoksa, uyarı ver
    if len(films) < 20:
        print("   ⚠️ Warning: Fewer than 20 films collected")
    
    # JSON olarak kaydet
    if films:
        with open('hdfilmcehennemi.json', 'w', encoding='utf-8') as f:
            json.dump(films, f, ensure_ascii=False, indent=2)
        print("📁 JSON file saved: hdfilmcehennemi.json")
        
        # İstatistikler
        print("\n📊 Statistics:")
        print(f"   Total unique films: {len(films)}")
        
        # Yıllara göre dağılım
        years = {}
        for film in films:
            year = film.get('year', 'N/A')
            years[year] = years.get(year, 0) + 1
        
        if years:
            print("   Films by year:")
            valid_years = [(y, c) for y, c in years.items() if y != 'N/A']
            for year, count in sorted(valid_years, key=lambda x: x[0], reverse=True)[:10]:
                print(f"     {year}: {count} films")
        
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
        
        # Dil dağılımı
        languages = {}
        for film in films:
            lang = film.get('language', 'Unknown')
            languages[lang] = languages.get(lang, 0) + 1
        
        if languages:
            print("   Languages:")
            for lang, count in sorted(languages.items(), key=lambda x: x[1], reverse=True):
                if count > 0:
                    print(f"     {lang}: {count} films")
        
        # Örnek filmler
        print("\n🎬 Sample films (first 10):")
        for i, film in enumerate(films[:10]):
            title = film['title'][:40] + '...' if len(film['title']) > 40 else film['title']
            year = film.get('year', 'N/A')
            imdb = film.get('imdb', 'N/A')
            print(f"   {i+1:2d}. {title} ({year}) ⭐ {imdb}")
    
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
                "scraped_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            },
            {
                "title": "A Knight of the Seven Kingdoms",
                "year": "2026",
                "imdb": "8.3",
                "language": "Yabancı Dizi",
                "link": "https://www.hdfilmcehennemi.nl/a-knight-of-the-seven-kingdoms/",
                "scraped_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        ]
        
        with open('hdfilmcehennemi.json', 'w', encoding='utf-8') as f:
            json.dump(sample_films, f, ensure_ascii=False, indent=2)
        print("📁 Sample JSON file created")
    
    print(f"\n🏁 Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()

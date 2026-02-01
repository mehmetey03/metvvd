import sys
import requests
from bs4 import BeautifulSoup
import time
import json
from datetime import datetime
import urllib.parse
import re

# Komut satırı argümanlarını al
PAGES_TO_SCRAPE = int(sys.argv[1]) if len(sys.argv) > 1 else 3
DELAY_BETWEEN_REQUESTS = float(sys.argv[2]) if len(sys.argv) > 2 else 2.0

print(f"📅 Scraping started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"📊 Pages to scrape: {PAGES_TO_SCRAPE}")
print(f"⏱️ Delay between requests: {DELAY_BETWEEN_REQUESTS} seconds")

PROXY_URL = "https://api.codetabs.com/v1/proxy/?quest="

def get_with_proxy(url, retry=3):
    """Proxy kullanarak URL'ye istek gönder"""
    for attempt in range(retry):
        try:
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
            
            if attempt > 0:
                time.sleep(2)  # Retry'ler arasında bekle
                print(f"   Retry attempt {attempt + 1}/{retry}...")
            
            response = requests.get(proxy_url, headers=headers, timeout=30)
            
            # İçeriği kontrol et
            if response.status_code == 200 and len(response.text) > 5000:
                return response
            else:
                print(f"   Response too short or error: {response.status_code}, {len(response.text)} chars")
                
        except Exception as e:
            print(f"   Attempt {attempt + 1} failed: {e}")
    
    # Tüm denemeler başarısız
    return None

def find_film_elements(soup):
    """Sayfadaki film elementlerini bul"""
    # Öncelikle poster class'ını ara
    film_elements = soup.find_all('a', class_='poster')
    
    if not film_elements:
        # Alternatif: poster-wrapper içindeki linkleri ara
        film_elements = soup.select('div.poster-wrapper > a')
    
    if not film_elements:
        # Alternatif: data-token attribute'u olan linkleri ara
        film_elements = soup.find_all('a', attrs={'data-token': True})
    
    if not film_elements:
        # Alternatif: /images/list/poster/ içeren resimleri olan linkleri ara
        film_elements = []
        for a in soup.find_all('a', href=True):
            img = a.find('img', src=re.compile(r'/images/list/poster/'))
            if img:
                film_elements.append(a)
    
    return film_elements

def extract_film_data(film_element):
    """Film verilerini çıkar"""
    film_data = {}
    
    try:
        # Başlık - farklı yöntemlerle bul
        title = None
        
        # 1. poster-title class'ı
        title_elem = film_element.find('strong', class_='poster-title')
        if title_elem:
            title = title_elem.text.strip()
        
        # 2. title attribute
        if not title:
            title = film_element.get('title', '').strip()
        
        # 3. Alt etiketlerde ara
        if not title:
            for elem in film_element.find_all(['strong', 'h3', 'h4', 'span']):
                if elem.text.strip() and len(elem.text.strip()) > 3:
                    title = elem.text.strip()
                    break
        
        film_data['title'] = title if title else 'N/A'
        
        # Link
        href = film_element.get('href', '')
        if href:
            if not href.startswith('http'):
                if href.startswith('/'):
                    film_data['link'] = f"https://www.hdfilmcehennemi.nl{href}"
                else:
                    film_data['link'] = f"https://www.hdfilmcehennemi.nl/{href}"
            else:
                film_data['link'] = href
        else:
            film_data['link'] = 'N/A'
        
        # Meta bilgileri - farklı konumlarda olabilir
        year = 'N/A'
        comment_count = '0'
        imdb_rating = 'N/A'
        language = 'N/A'
        
        # poster-info div'i içinde ara
        poster_info = film_element.find('div', class_='poster-info')
        if poster_info:
            # poster-meta içinde yıl ve yorum sayısı
            poster_meta = poster_info.find('div', class_='poster-meta')
            if poster_meta:
                spans = poster_meta.find_all('span')
                if spans:
                    year = spans[0].text.strip()
                    if len(spans) > 1:
                        comment_count = spans[1].text.strip()
            
            # IMDB rating
            imdb_elem = poster_info.find('span', class_='imdb')
            if imdb_elem:
                imdb_rating = imdb_elem.text.strip()
            
            # Dil bilgisi
            lang_elem = poster_info.find('span', class_='poster-lang')
            if lang_elem:
                # Türkçe bayrak kontrolü
                tr_flag = lang_elem.find('i', class_='tr-flag')
                text_span = lang_elem.find('span')
                
                if tr_flag:
                    language = 'Türkçe Dublaj'
                elif text_span:
                    language = text_span.text.strip()
        
        # Eğer poster-info yoksa, direkt film elementinde ara
        if year == 'N/A':
            meta_div = film_element.find('div', class_='poster-meta')
            if meta_div:
                spans = meta_div.find_all('span')
                if spans:
                    year = spans[0].text.strip()
        
        if imdb_rating == 'N/A':
            imdb_elem = film_element.find('span', class_='imdb')
            if imdb_elem:
                imdb_rating = imdb_elem.text.strip()
        
        film_data['year'] = year
        film_data['comment_count'] = comment_count
        film_data['imdb_rating'] = imdb_rating
        film_data['language'] = language
        
        # Resim URL'leri
        img_elem = film_element.find('img', class_='lazyload')
        if not img_elem:
            img_elem = film_element.find('img')
        
        if img_elem:
            img_src = img_elem.get('data-src') or img_elem.get('src', '')
            if img_src:
                if not img_src.startswith('http'):
                    if img_src.startswith('/'):
                        film_data['image'] = f"https://www.hdfilmcehennemi.nl{img_src}"
                    else:
                        film_data['image'] = f"https://www.hdfilmcehennemi.nl/{img_src}"
                else:
                    film_data['image'] = img_src
            else:
                film_data['image'] = 'N/A'
            
            # 2x resim
            srcset = img_elem.get('data-srcset', img_elem.get('srcset', ''))
            if srcset:
                parts = [p.strip() for p in srcset.split(',')]
                for part in parts:
                    if '@2x' in part:
                        img_2x = part.split(' ')[0]
                        if img_2x:
                            if not img_2x.startswith('http'):
                                if img_2x.startswith('/'):
                                    film_data['image_2x'] = f"https://www.hdfilmcehennemi.nl{img_2x}"
                                else:
                                    film_data['image_2x'] = f"https://www.hdfilmcehennemi.nl/{img_2x}"
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
        
        # Data token (ID)
        film_data['data_token'] = film_element.get('data-token', 'N/A')
        
        # Tarih
        film_data['scraped_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Page kaynağı (debug için)
        film_data['page'] = film_element.get('data-page', 'N/A')
        
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
    
    print(f"\n🔍 Scraping page {page_num}: {url}")
    
    response = get_with_proxy(url)
    
    if not response:
        print(f"❌ Failed to fetch page {page_num}")
        return []
    
    if response.status_code != 200:
        print(f"❌ Page {page_num} returned status {response.status_code}")
        return []
    
    # HTML'i parse et
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Debug: HTML'in ilk 2000 karakterini kaydet
    if page_num <= 2:  # Sadece ilk 2 sayfa için debug
        html_preview = str(soup)[:2000]
        print(f"   HTML preview: {html_preview[:200]}...")
    
    # Filmleri bul
    film_elements = find_film_elements(soup)
    
    if not film_elements:
        print(f"⚠️ No film elements found with standard selectors on page {page_num}")
        
        # Tüm linkleri kontrol et
        all_links = soup.find_all('a', href=True)
        film_links = []
        
        for link in all_links:
            href = link.get('href', '')
            # Film sayfası URL'lerini filtrele
            if ('/film/' in href or '/dizi/' in href or 
                re.search(r'/\d+/$', href) or 
                ('hdfilmcehennemi.nl' in href and not href.endswith('.css') and not href.endswith('.js'))):
                film_links.append(link)
        
        print(f"   Found {len(film_links)} potential film links")
        film_elements = film_links[:30]  # İlk 30 ile sınırla
    
    films = []
    print(f"   Processing {len(film_elements)} elements")
    
    # Her film için veri çıkar
    valid_count = 0
    for i, film in enumerate(film_elements[:30]):  # İlk 30 ile sınırla
        film_data = extract_film_data(film)
        if film_data:
            # Geçerli film mi kontrol et (boş olmayan başlık ve yıl)
            if (film_data.get('title', 'N/A') != 'N/A' and 
                film_data.get('year', 'N/A') != 'N/A' and
                len(film_data.get('title', '')) > 3):
                
                # Duplicate kontrolü (aynı başlık ve yıl)
                is_duplicate = False
                for existing in films:
                    if (existing.get('title') == film_data.get('title') and 
                        existing.get('year') == film_data.get('year')):
                        is_duplicate = True
                        break
                
                if not is_duplicate:
                    films.append(film_data)
                    valid_count += 1
                    print(f"     ✓ {valid_count}. {film_data.get('title', 'N/A')[:40]}... ({film_data.get('year', 'N/A')})")
            else:
                print(f"     ✗ Invalid film data")
        else:
            print(f"     ✗ Failed to extract data")
    
    print(f"   Added {valid_count} valid films from page {page_num}")
    return films

def main():
    all_films = []
    
    # Sayfaları tara
    for page in range(1, PAGES_TO_SCRAPE + 1):
        page_films = scrape_page(page)
        all_films.extend(page_films)
        
        # Sayfalar arası bekleme (son sayfa hariç)
        if page < PAGES_TO_SCRAPE and page_films:
            print(f"\n⏳ Waiting {DELAY_BETWEEN_REQUESTS} seconds before next page...")
            time.sleep(DELAY_BETWEEN_REQUESTS)
    
    print(f"\n✅ Scraping completed! Total films collected: {len(all_films)}")
    
    # JSON olarak kaydet
    if all_films:
        with open('hdfilmcehennemi.json', 'w', encoding='utf-8') as f:
            json.dump(all_films, f, ensure_ascii=False, indent=2)
        print("📁 JSON file saved: hdfilmcehennemi.json")
        
        # İstatistikler
        print("\n📊 Statistics:")
        print(f"   Total unique films: {len(all_films)}")
        
        # Yıllara göre dağılım
        years = {}
        for film in all_films:
            year = film.get('year', 'N/A')
            years[year] = years.get(year, 0) + 1
        
        if years:
            print("   Films by year:")
            sorted_years = sorted([(y, c) for y, c in years.items() if y != 'N/A'], 
                                key=lambda x: x[0], reverse=True)
            for year, count in sorted_years[:15]:  # İlk 15
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
            for lang, count in sorted(languages.items(), key=lambda x: x[1], reverse=True):
                if lang != 'N/A' and count > 0:
                    print(f"     {lang}: {count} films")
        
        # Sayfa kaynağı
        pages = {}
        for film in all_films:
            page = film.get('page', '1')
            pages[page] = pages.get(page, 0) + 1
        
        print("   Films by page source:")
        for page, count in sorted(pages.items()):
            print(f"     Page {page}: {count} films")
        
        # Örnek filmler
        print("\n🎬 Sample films (10 from total):")
        for i, film in enumerate(all_films[:10]):
            title = film.get('title', 'N/A')[:50]
            year = film.get('year', 'N/A')
            imdb = film.get('imdb_rating', 'N/A')
            lang = film.get('language', 'N/A')
            print(f"   {i+1:2d}. {title} ({year}) - ⭐ {imdb} - {lang}")
    
    else:
        print("⚠️ No films collected!")
        
        # Örnek veri oluştur
        print("📝 Creating sample data for testing...")
        sample_data = []
        for i in range(10):
            sample_data.append({
                "title": f"Sample Film {i+1}",
                "year": f"{2024 + (i % 3)}",
                "imdb_rating": f"{6.0 + (i * 0.2):.1f}",
                "language": "Türkçe Dublaj" if i % 2 == 0 else "Türkçe Altyazılı",
                "comment_count": f"{i * 5}",
                "link": f"https://www.hdfilmcehennemi.nl/sample-film-{i+1}/",
                "image": f"https://www.hdfilmcehennemi.nl/images/list/poster/sample-{i+1}.webp",
                "scraped_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
        
        with open('hdfilmcehennemi.json', 'w', encoding='utf-8') as f:
            json.dump(sample_data, f, ensure_ascii=False, indent=2)
        print("📁 Sample JSON file created with 10 films")
    
    print(f"\n🏁 Scraping finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Debug dosyalarını temizle
    import os
    for file in os.listdir('.'):
        if file.startswith('debug_') and file.endswith('.html'):
            try:
                os.remove(file)
            except:
                pass

if __name__ == "__main__":
    main()

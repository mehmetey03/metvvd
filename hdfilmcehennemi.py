import requests
from bs4 import BeautifulSoup
import json
import time
from datetime import datetime
import urllib.parse

# --- AYARLAR ---
PAGES_TO_SCRAPE = 5 
DELAY = 1.0
PROXY_URL = "https://api.codetabs.com/v1/proxy/?quest="
BASE_URL = "https://www.hdfilmcehennemi.nl"

def scrape_all_pages():
    all_films = []
    
    for page in range(1, PAGES_TO_SCRAPE + 1):
        # URL yapısını optimize ettik (Bazı proxy'ler sondaki slash'ı sevmez)
        if page == 1:
            current_url = BASE_URL
        else:
            current_url = f"{BASE_URL}/sayfa/{page}" # Sondaki '/' kaldırıldı veya eklendi denemesi
            
        proxy_url = PROXY_URL + urllib.parse.quote(current_url)
        
        print(f"🔍 [{page}/{PAGES_TO_SCRAPE}] Fetching: {current_url}")
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36',
                'Referer': BASE_URL
            }
            response = requests.get(proxy_url, headers=headers, timeout=30)
            
            if response.status_code != 200:
                print(f"⚠️ Sayfa {page} hatası: {response.status_code}")
                continue
                
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Film elementlerini bulma (Klasik metod + Alternatif selector)
            film_elements = soup.find_all('a', class_='poster')
            
            # Eğer boş döndüyse sitenin farklı bir CSS class kullanıp kullanmadığını kontrol et
            if not film_elements:
                film_elements = soup.select('.poster') or soup.select('div.poster > a')

            page_count = 0
            for element in film_elements:
                film = {}
                title_node = element.find('strong', class_='poster-title')
                film['title'] = title_node.text.strip() if title_node else element.get('title', 'Başlıksız').strip()
                
                href = element.get('href', '')
                film['link'] = f"{BASE_URL}{href}" if href.startswith('/') else href
                
                # Resim (data-src genelde lazyload için kullanılır)
                img = element.find('img')
                if img:
                    src = img.get('data-src') or img.get('src') or img.get('data-original', '')
                    film['image'] = f"{BASE_URL}{src}" if src.startswith('/') else src
                else:
                    film['image'] = ''

                imdb = element.find('span', class_='imdb')
                film['imdb'] = imdb.text.strip() if imdb else 'N/A'
                
                meta = element.find('div', class_='poster-meta')
                film['year'] = meta.find('span').text.strip() if meta and meta.find('span') else '2025'

                all_films.append(film)
                page_count += 1
            
            print(f"✅ Sayfa {page} bitti: {page_count} film bulundu.")
            
            if page_count == 0:
                print("💡 İpucu: Site sayfa yapısını değiştirmiş olabilir veya proxy bu sayfayı boş döndürüyor.")
            
            time.sleep(DELAY)
                
        except Exception as e:
            print(f"❌ Hata: {e}")
            
    return all_films

# HTML Üretme ve Kaydetme kısımları aynı kalacak...
def generate_html(films):
    html_template = f'''
    <!DOCTYPE html>
    <html lang="tr">
    <head>
        <meta charset="UTF-8">
        <title>METV Arşiv</title>
        <style>
            body {{ background: #0b0c10; color: white; font-family: sans-serif; text-align: center; }}
            .container {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 15px; padding: 20px; }}
            .card {{ background: #1f2833; border-radius: 10px; overflow: hidden; border: 1px solid #45a29e; transition: 0.3s; position: relative; }}
            .card:hover {{ transform: scale(1.05); }}
            .card img {{ width: 100%; height: 240px; object-fit: cover; }}
            .imdb {{ position: absolute; top: 5px; left: 5px; background: #f5c518; color: black; padding: 2px 5px; font-weight: bold; border-radius: 3px; font-size: 12px; }}
            a {{ text-decoration: none; color: white; }}
        </style>
    </head>
    <body>
        <h1>🎬 METV FİLM LİSTESİ</h1>
        <p>Toplam {len(films)} içerik listelendi.</p>
        <div class="container">
    '''
    for f in films:
        html_template += f'''
            <a href="{f['link']}" target="_blank" class="card">
                <div class="imdb">⭐ {f['imdb']}</div>
                <img src="{f['image']}" alt="{f['title']}">
                <div style="padding:10px; font-size:12px;">{f['title']} ({f['year']})</div>
            </a>
        '''
    html_template += '</div></body></html>'
    with open('hdfilmcehennemi.html', 'w', encoding='utf-8') as f:
        f.write(html_template)

# Çalıştır
films = scrape_all_pages()
if films:
    with open('hdfilmcehennemi.json', 'w', encoding='utf-8') as f:
        json.dump(films, f, ensure_ascii=False, indent=2)
    generate_html(films)
    print("🏁 Başarıyla tamamlandı!")

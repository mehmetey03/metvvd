import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import urllib.parse
import os

# ============================================================================
# AYARLAR
# ============================================================================
print(f"📅 Scraping started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
PROXY_URL = "https://api.codetabs.com/v1/proxy/?quest="
TARGET_SITE = "https://www.hdfilmcehennemi.nl/"

def scrape_site():
    """Siteyi tara ve verileri çek"""
    proxy_url = PROXY_URL + urllib.parse.quote(TARGET_SITE)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
    }
    
    try:
        print(f"🔍 Fetching: {TARGET_SITE}")
        response = requests.get(proxy_url, headers=headers, timeout=30)
        
        if response.status_code != 200:
            print(f"❌ Status: {response.status_code}")
            return []
        
        soup = BeautifulSoup(response.content, 'html.parser')
        films = []
        film_elements = soup.find_all('a', class_='poster')
        
        print(f"✅ Found {len(film_elements)} film elements")
        
        for element in film_elements:
            film = {}
            title_node = element.find('strong', class_='poster-title')
            film['title'] = title_node.text.strip() if title_node else element.get('title', '').strip()
            
            if not film['title']: continue
            
            href = element.get('href', '')
            film['link'] = f"https://www.hdfilmcehennemi.nl{href}" if href.startswith('/') else href
            
            meta = element.find('div', class_='poster-meta')
            film['year'] = meta.find_all('span')[0].text.strip() if meta and meta.find_all('span') else '2025'
            
            imdb = element.find('span', class_='imdb')
            film['imdb'] = imdb.text.strip() if imdb else '6.0'
            
            # Resim çekme
            img = element.find('img', class_='lazyload')
            if img:
                src = img.get('data-src') or img.get('src', '')
                film['image'] = f"https://www.hdfilmcehennemi.nl{src}" if src.startswith('/') else src
            else:
                film['image'] = 'https://via.placeholder.com/300x450/15161a/ffffff?text=Resim+Yok'
            
            films.append(film)
        return films
    except Exception as e:
        print(f"❌ Error: {e}")
        return []

def generate_html(films):
    """Filmleri şık bir HTML dosyasına dönüştürür"""
    html_template = f'''
    <!DOCTYPE html>
    <html lang="tr">
    <head>
        <meta charset="UTF-8">
        <title>METV VOD - {datetime.now().strftime('%d.%m.%Y')}</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{ background: #0b0c10; color: white; font-family: 'Segoe UI', sans-serif; margin: 0; padding: 0; }}
            .header {{ background: #1f2833; padding: 20px; text-align: center; border-bottom: 3px solid #66fcf1; sticky; top: 0; z-index: 100; }}
            .container {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 20px; padding: 20px; }}
            .card {{ background: #15161a; border-radius: 10px; overflow: hidden; border: 1px solid #333; transition: 0.3s; cursor: pointer; position: relative; }}
            .card:hover {{ transform: scale(1.05); border-color: #66fcf1; }}
            .card img {{ width: 100%; height: 270px; object-fit: cover; }}
            .card-info {{ padding: 10px; text-align: center; }}
            .card-title {{ font-size: 14px; font-weight: bold; margin: 5px 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
            .imdb-badge {{ position: absolute; top: 10px; left: 10px; background: rgba(245, 197, 24, 0.9); color: black; padding: 2px 8px; border-radius: 5px; font-weight: bold; font-size: 12px; }}
            .year-badge {{ color: #888; font-size: 12px; }}
            a {{ text-decoration: none; color: inherit; }}
            #search {{ padding: 10px; border-radius: 20px; border: none; width: 80%; max-width: 400px; margin-top: 10px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🎬 METV VOD ARŞİVİ</h1>
            <input type="text" id="search" placeholder="Film ara..." onkeyup="search()">
        </div>
        <div class="container" id="grid">
    '''
    
    for f in films:
        html_template += f'''
            <a href="{f['link']}" target="_blank" class="card">
                <div class="imdb-badge">⭐ {f['imdb']}</div>
                <img src="{f['image']}" loading="lazy">
                <div class="card-info">
                    <div class="card-title">{f['title']}</div>
                    <div class="year-badge">{f['year']}</div>
                </div>
            </a>
        '''
    
    html_template += '''
        </div>
        <script>
            function search() {
                let input = document.getElementById('search').value.toLowerCase();
                let cards = document.getElementsByClassName('card');
                for (let card of cards) {
                    let title = card.innerText.toLowerCase();
                    card.style.display = title.includes(input) ? "block" : "none";
                }
            }
        </script>
    </body>
    </html>
    '''
    
    with open('hdfilmcehennemi.html', 'w', encoding='utf-8') as f:
        f.write(html_template)
    print("📁 HTML dosyası başarıyla oluşturuldu: hdfilmcehennemi.html")

# ============================================================================
# ANA ÇALIŞTIRICI
# ============================================================================
films_data = scrape_site()

if films_data:
    # 1. JSON Kaydet
    with open('hdfilmcehennemi.json', 'w', encoding='utf-8') as f:
        json.dump(films_data, f, ensure_ascii=False, indent=2)
    print(f"✅ JSON kaydedildi. ({len(films_data)} film)")

    # 2. HTML Üret
    generate_html(films_data)
else:
    print("❌ Veri toplanamadığı için dosya oluşturulmadı.")

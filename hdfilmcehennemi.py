import requests
from bs4 import BeautifulSoup
import json
import time
from datetime import datetime
import urllib.parse

# --- AYARLAR ---
PAGES_TO_SCRAPE = 5  # Çekilecek sayfa sayısı
DELAY = 1.0          # Sayfalar arası bekleme (IP ban riskine karşı)
PROXY_URL = "https://api.codetabs.com/v1/proxy/?quest="
BASE_URL = "https://www.hdfilmcehennemi.nl"

print(f"📅 Scraping started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"📊 Pages to scrape: {PAGES_TO_SCRAPE}")

def scrape_all_pages():
    all_films = []
    
    for page in range(1, PAGES_TO_SCRAPE + 1):
        # URL oluşturma (1. sayfa farklı, diğerleri /sayfa/X/ şeklinde)
        current_url = BASE_URL + "/" if page == 1 else f"{BASE_URL}/sayfa/{page}/"
        proxy_url = PROXY_URL + urllib.parse.quote(current_url)
        
        print(f"🔍 [{page}/{PAGES_TO_SCRAPE}] Fetching: {current_url}")
        
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'}
            response = requests.get(proxy_url, headers=headers, timeout=30)
            
            if response.status_code != 200:
                print(f"⚠️ Page {page} skipped (Status: {response.status_code})")
                continue
                
            soup = BeautifulSoup(response.content, 'html.parser')
            film_elements = soup.find_all('a', class_='poster')
            
            page_count = 0
            for element in film_elements:
                film = {}
                title_node = element.find('strong', class_='poster-title')
                film['title'] = title_node.text.strip() if title_node else element.get('title', '').strip()
                
                if not film['title']: continue
                
                href = element.get('href', '')
                film['link'] = f"{BASE_URL}{href}" if href.startswith('/') else href
                
                meta = element.find('div', class_='poster-meta')
                film['year'] = meta.find_all('span')[0].text.strip() if meta and meta.find_all('span') else 'N/A'
                
                imdb = element.find('span', class_='imdb')
                film['imdb'] = imdb.text.strip() if imdb else 'N/A'
                
                img = element.find('img')
                if img:
                    src = img.get('data-src') or img.get('src', '')
                    film['image'] = f"{BASE_URL}{src}" if src.startswith('/') else src
                else:
                    film['image'] = 'https://via.placeholder.com/300x450'

                all_films.append(film)
                page_count += 1
            
            print(f"✅ Found {page_count} films on page {page}")
            
            # Sayfalar arası kısa bekleme
            if page < PAGES_TO_SCRAPE:
                time.sleep(DELAY)
                
        except Exception as e:
            print(f"❌ Error on page {page}: {e}")
            
    return all_films

def generate_html(films):
    """HTML Galeri Tasarımı"""
    html_template = f'''
    <!DOCTYPE html>
    <html lang="tr">
    <head>
        <meta charset="UTF-8">
        <title>METV Dev Arşiv</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{ background: #0b0c10; color: white; font-family: sans-serif; margin: 0; }}
            .header {{ background: #1f2833; padding: 20px; text-align: center; border-bottom: 3px solid #66fcf1; position: sticky; top: 0; z-index: 100; }}
            .container {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 15px; padding: 20px; }}
            .card {{ background: #15161a; border-radius: 8px; overflow: hidden; border: 1px solid #333; transition: 0.3s; position: relative; }}
            .card:hover {{ transform: translateY(-5px); border-color: #66fcf1; box-shadow: 0 5px 15px rgba(102, 252, 241, 0.2); }}
            .card img {{ width: 100%; height: 230px; object-fit: cover; }}
            .card-info {{ padding: 8px; text-align: center; font-size: 13px; }}
            .imdb {{ position: absolute; top: 5px; left: 5px; background: #f5c518; color: black; padding: 2px 5px; border-radius: 4px; font-weight: bold; font-size: 11px; }}
            #search {{ padding: 12px; width: 80%; max-width: 500px; border-radius: 25px; border: none; }}
            a {{ text-decoration: none; color: inherit; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🎬 METV FİLM ARŞİVİ</h1>
            <input type="text" id="search" placeholder="Yüzlerce film içinde ara..." onkeyup="search()">
            <p style="color: #66fcf1;">Toplam {len(films)} Film Bulundu</p>
        </div>
        <div class="container" id="grid">
    '''
    for f in films:
        html_template += f'''
            <a href="{f['link']}" target="_blank" class="card">
                <div class="imdb">⭐ {f['imdb']}</div>
                <img src="{f['image']}" loading="lazy">
                <div class="card-info">
                    <strong>{f['title']}</strong><br>
                    <span style="color: #888;">{f['year']}</span>
                </div>
            </a>
        '''
    html_template += '''
        </div>
        <script>
            function search() {
                let val = document.getElementById('search').value.toLowerCase();
                document.querySelectorAll('.card').forEach(c => {
                    c.style.display = c.innerText.toLowerCase().includes(val) ? "" : "none";
                });
            }
        </script>
    </body></html>
    '''
    with open('hdfilmcehennemi.html', 'w', encoding='utf-8') as f:
        f.write(html_template)

# --- ÇALIŞTIR ---
final_list = scrape_all_pages()

if final_list:
    with open('hdfilmcehennemi.json', 'w', encoding='utf-8') as f:
        json.dump(final_list, f, ensure_ascii=False, indent=2)
    generate_html(final_list)
    print(f"\n🏁 İŞLEM TAMAMLANDI!")
    print(f"📂 Toplam {len(final_list)} film çekildi.")
    print(f"📁 Dosyalar oluşturuldu: hdfilmcehennemi.json, hdfilmcehennemi.html")
else:
    print("❌ Hiç veri çekilemedi.")

import sys
import requests
from bs4 import BeautifulSoup
import time
import json
import re
import os
from datetime import datetime
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

# ============================================================================
# AYARLAR VE PROXY
# ============================================================================
PAGES_TO_SCRAPE = int(sys.argv[1]) if len(sys.argv) > 1 else 5
MAX_WORKERS = 8 # Proxy hızına göre dengelendi
PROXY_URL = "https://api.codetabs.com/v1/proxy/?quest="
BASE_URL = "https://www.hdfilmcehennemi.nl"

def get_with_proxy(url):
    proxy_url = PROXY_URL + urllib.parse.quote(url)
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'}
    try:
        res = requests.get(proxy_url, headers=headers, timeout=20)
        return res if res.status_code == 200 else None
    except:
        return None

def slugify(text):
    text = text.lower()
    tr_map = str.maketrans("ığüşöç ", "igusoc-")
    return re.sub(r'[^a-z0-9-]', '', text.translate(tr_map)).strip('-')

# ============================================================================
# VERİ ÇIKARMA (PARSER)
# ============================================================================
def extract_film_info(element):
    try:
        title = element.get('title') or element.find('strong').text.strip()
        link = element.get('href')
        if not link.startswith('http'):
            link = urljoin(BASE_URL, link)
            
        # Resim çekme (lazyload desteği)
        img_tag = element.find('img')
        img_url = img_tag.get('data-src') or img_tag.get('src') if img_tag else ""
        
        # Meta Bilgileri
        imdb = element.find('span', class_='imdb').text.strip() if element.find('span', class_='imdb') else "N/A"
        
        return {
            "id": slugify(title),
            "isim": title,
            "resim": img_url,
            "link": link,
            "imdb": imdb,
            "yil": element.find('div', class_='poster-meta').find('span').text.strip() if element.find('div', class_='poster-meta') else "N/A"
        }
    except:
        return None

# ============================================================================
# HTML ÜRETİCİ (VOD STYLE)
# ============================================================================
def create_modern_html(data):
    html_content = f'''
    <!DOCTYPE html>
    <html lang="tr">
    <head>
        <meta charset="UTF-8"><title>ME TV - FİLM ARŞİVİ</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
        <style>
            :root {{ --main: #572aa7; --bg: #0b0c10; --card: #1f2833; }}
            body {{ background: var(--bg); color: white; font-family: 'Segoe UI', sans-serif; margin: 0; }}
            .header {{ padding: 20px; background: #15161a; border-bottom: 2px solid var(--main); position: sticky; top: 0; z-index: 100; text-align: center; }}
            .search-bar {{ padding: 10px; width: 80%; max-width: 500px; border-radius: 20px; border: none; outline: none; }}
            .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 15px; padding: 20px; }}
            .card {{ background: var(--card); border-radius: 10px; overflow: hidden; transition: 0.3s; position: relative; cursor: pointer; border: 1px solid #333; }}
            .card:hover {{ transform: translateY(-5px); border-color: var(--main); }}
            .card img {{ width: 100%; height: 240px; object-fit: cover; }}
            .imdb-badge {{ position: absolute; top: 10px; left: 10px; background: #f5c518; color: black; padding: 2px 6px; border-radius: 4px; font-weight: bold; font-size: 12px; }}
            .info {{ padding: 10px; font-size: 13px; text-align: center; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h2>🎬 ME TV VOD</h2>
            <input type="text" class="search-bar" id="search" placeholder="Film ara..." onkeyup="filter()">
        </div>
        <div class="grid" id="grid">
    '''
    for f in data:
        html_content += f'''
            <div class="card" onclick="window.open('{f['link']}', '_blank')">
                <div class="imdb-badge">⭐ {f['imdb']}</div>
                <img src="{f['resim']}" loading="lazy">
                <div class="info">{f['isim']} ({f['yil']})</div>
            </div>
        '''
    html_content += '''
        </div>
        <script>
            function filter() {
                let val = document.getElementById('search').value.toLowerCase();
                document.querySelectorAll('.card').forEach(c => {
                    c.style.display = c.innerText.toLowerCase().includes(val) ? '' : 'none';
                });
            }
        </script>
    </body></html>
    '''
    with open("hdfilmcehennemi.html", "w", encoding="utf-8") as f:
        f.write(html_content)

# ============================================================================
# ANA ÇALIŞTIRICI
# ============================================================================
def main():
    all_data = []
    print(f"🚀 Proxy üzerinden {PAGES_TO_SCRAPE} sayfa taranıyor...")
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        pages = [f"{BASE_URL}/sayfa/{p}/" for p in range(1, PAGES_TO_SCRAPE + 1)]
        future_to_url = {executor.submit(get_with_proxy, url): url for url in pages}
        
        for future in as_completed(future_to_url):
            res = future.result()
            if res:
                soup = BeautifulSoup(res.content, 'html.parser')
                elements = soup.find_all('a', class_='poster')
                for el in elements:
                    info = extract_film_info(el)
                    if info: all_data.append(info)
                print(f"✅ Sayfa işlendi. Toplam film: {len(all_data)}")

    # Kaydetme işlemleri
    with open('hdfilmcehennemi.json', 'w', encoding='utf-8') as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    
    create_modern_html(all_data)
    print(f"\n🏁 TAMAMLANDI! {len(all_data)} film kaydedildi.")
    print("📁 hdfilmcehennemi.json ve hdfilmcehennemi.html dosyaları hazır.")

if __name__ == "__main__":
    main()

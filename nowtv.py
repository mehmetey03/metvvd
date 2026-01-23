import cloudscraper
from bs4 import BeautifulSoup
import json
import time
import re
import os
import subprocess
import logging
from urllib.parse import urljoin, urlparse

# Log ayarları
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

BASE_URL = "https://www.nowtv.com.tr"
MAIN_URL = "https://www.nowtv.com.tr/dizi-izle"

def slugify(text):
    if not text: return ""
    mapping = {'ç': 'c', 'ğ': 'g', 'ı': 'i', 'ö': 'o', 'ş': 's', 'ü': 'u', 'Ç': 'c', 'Ğ': 'g', 'İ': 'i', 'Ö': 'o', 'Ş': 's', 'Ü': 'u'}
    text = str(text).lower().strip()
    for tr, en in mapping.items():
        text = text.replace(tr, en)
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'[\s-]+', '-', text)
    return text.strip('-')

def clean_url(url):
    if not url: return ""
    url = url.strip()
    if url.startswith('//'): url = 'https:' + url
    elif url.startswith('/'): url = BASE_URL + url
    elif not url.startswith(('http://', 'https://')): url = BASE_URL + '/' + url.lstrip('/')
    return url

def extract_series_info(scraper, series_url):
    try:
        resp = scraper.get(series_url, timeout=20)
        if resp.status_code != 200: return []
        soup = BeautifulSoup(resp.text, 'html.parser')
        episodes = []
        
        # NowTV bölüm kartlarını hedefle
        items = soup.select('.video-item, .list-item, a[href*="/bolumler/"]')
        for item in items:
            link_elem = item if item.name == 'a' else item.find('a', href=True)
            if not link_elem: continue
            ep_url = clean_url(link_elem['href'])
            if "/bolum" not in ep_url: continue 
            
            title_elem = item.select_one('.title, h3, .program-name')
            title = title_elem.get_text(strip=True) if title_elem else "Bölüm"
            img_elem = item.find('img')
            thumb = clean_url(img_elem.get('src') or img_elem.get('data-src', '')) if img_elem else ""
            
            episodes.append({"ad": title, "link": ep_url, "thumbnail": thumb})
        return episodes[::-1]
    except Exception as e:
        logger.error(f"Dizi detay hatası: {e}")
        return []

def create_html(series_data):
    json_data = json.dumps(series_data, ensure_ascii=False)
    # Burada senin verdiğin CSS ve HTML yapısını koruyup JS fonksiyonlarını tamamladım
    html_template = f'''
    <!DOCTYPE html>
    <html lang="tr">
    <head>
        <title>NOW TV DİZİ ARŞİVİ</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <style>
            :root {{ --primary: #e50914; --bg: #141414; --card-bg: #1f1f1f; --text: #ffffff; }}
            body {{ background-color: var(--bg); color: var(--text); font-family: 'Segoe UI', sans-serif; margin: 0; padding: 0; }}
            .header {{ padding: 20px 4%; background: rgba(0,0,0,0.9); position: sticky; top: 0; z-index: 1000; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #333; }}
            .logo {{ font-size: 28px; font-weight: bold; color: var(--primary); text-decoration: none; }}
            .search-box input {{ padding: 10px 20px; border-radius: 20px; border: 1px solid #444; background: #000; color: #fff; width: 250px; }}
            .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 20px; padding: 20px 4%; }}
            .card {{ background: var(--card-bg); border-radius: 8px; overflow: hidden; cursor: pointer; transition: 0.3s; border: 1px solid #222; }}
            .card:hover {{ transform: scale(1.05); border-color: var(--primary); }}
            .card img {{ width: 100%; aspect-ratio: 2/3; object-fit: cover; }}
            .card-info {{ padding: 10px; text-align: center; font-weight: bold; font-size: 14px; }}
            .player-overlay {{ position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.95); z-index: 2000; display: none; align-items: center; justify-content: center; }}
            .player-container {{ width: 90%; max-width: 1000px; position: relative; }}
            .close-btn {{ position: absolute; top: -40px; right: 0; color: #fff; font-size: 30px; cursor: pointer; }}
            iframe {{ width: 100%; height: 56.25vw; max-height: 600px; border: none; }}
        </style>
    </head>
    <body>
        <div class="header">
            <a href="#" class="logo">NOW TV ARŞİV</a>
            <div class="search-box"><input type="text" id="searchInput" placeholder="Dizi ara..." onkeyup="search()"></div>
        </div>
        <div id="seriesGrid" class="grid"></div>
        <div id="episodesGrid" class="grid" style="display:none;"></div>
        <div id="playerOverlay" class="player-overlay">
            <div class="player-container">
                <span class="close-btn" onclick="closePlayer()">&times;</span>
                <iframe id="videoFrame" src="" allowfullscreen></iframe>
            </div>
        </div>
        <script>
            const data = {json_data};
            const sGrid = document.getElementById('seriesGrid');
            const eGrid = document.getElementById('episodesGrid');

            function render() {{
                sGrid.innerHTML = "";
                for(let id in data) {{
                    sGrid.innerHTML += `<div class="card" onclick="showEpisodes('${{id}}')">
                        <img src="${{data[id].resim}}">
                        <div class="card-info">${{data[id].isim}}</div>
                    </div>`;
                }}
            }}

            function showEpisodes(id) {{
                sGrid.style.display = "none";
                eGrid.style.display = "grid";
                eGrid.innerHTML = `<div style="grid-column:1/-1"><button onclick="location.reload()" style="background:red; color:white; border:none; padding:10px; cursor:pointer">GERİ DÖN</button><h2>${{data[id].isim}}</h2></div>`;
                data[id].bolumler.forEach(ep => {{
                    eGrid.innerHTML += `<div class="card" onclick="play('${{ep.link}}')">
                        <img src="${{ep.thumbnail || data[id].resim}}">
                        <div class="card-info">${{ep.ad}}</div>
                    </div>`;
                }});
            }}

            function play(url) {{
                document.getElementById('videoFrame').src = url;
                document.getElementById('playerOverlay').style.display = "flex";
            }}

            function closePlayer() {{
                document.getElementById('playerOverlay').style.display = "none";
                document.getElementById('videoFrame').src = "";
            }}
            
            function search() {{
                let val = document.getElementById('searchInput').value.toLowerCase();
                document.querySelectorAll('#seriesGrid .card').forEach(card => {{
                    card.style.display = card.innerText.toLowerCase().includes(val) ? "block" : "none";
                }});
            }}

            render();
        </script>
    </body>
    </html>
    '''
    with open("nowtv_vod.html", "w", encoding="utf-8") as f:
        f.write(html_template)

def run_scraper():
    logger.info("🚀 Scraper Başlatıldı...")
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome','platform': 'windows','desktop': True})
    
    try:
        response = scraper.get(MAIN_URL, timeout=30)
        soup = BeautifulSoup(response.text, 'html.parser')
        series_data = {}
        
        # NowTV'deki dizi kartlarını bul
        cards = soup.select('.list-item, .program-card')
        for card in cards:
            link_elem = card.find('a', href=True)
            if not link_elem: continue
            
            s_url = clean_url(link_elem['href'])
            s_name = card.select_one('.program-name, .title').get_text(strip=True)
            s_id = slugify(s_name)
            
            img_elem = card.find('img')
            img = clean_url(img_elem.get('src') or img_elem.get('data-src', '')) if img_elem else ""
            
            logger.info(f"🔍 İşleniyor: {s_name}")
            eps = extract_series_info(scraper, s_url)
            
            if eps:
                series_data[s_id] = {"isim": s_name, "resim": img, "bolumler": eps}
            time.sleep(1)

        with open("nowtv_data.json", "w", encoding="utf-8") as f:
            json.dump(series_data, f, ensure_ascii=False, indent=2)
        
        create_html(series_data)
        logger.info("🎉 İşlem tamamlandı.")

    except Exception as e:
        logger.error(f"Hata: {e}")

if __name__ == "__main__":
    run_scraper()

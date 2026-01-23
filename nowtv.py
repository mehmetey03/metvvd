import cloudscraper
from bs4 import BeautifulSoup
import json
import time
import re
import os
import logging

# --- LOG AYARLARI ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

BASE_URL = "https://www.nowtv.com.tr"
MAIN_URL = "https://www.nowtv.com.tr/dizi-arsivi"

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
    html_content = f'''<!DOCTYPE html>
<html lang="tr">
<head>
    <title>NOW TV Arşivi</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root {{ --primary: #e50914; --bg: #141414; --card-bg: #1f1f1f; --text: #ffffff; }}
        body {{ background-color: var(--bg); color: var(--text); font-family: 'Segoe UI', sans-serif; margin: 0; padding: 0; }}
        .header {{ padding: 20px 4%; background: linear-gradient(to bottom, rgba(0,0,0,0.8), transparent); position: sticky; top: 0; z-index: 100; backdrop-filter: blur(10px); display: flex; justify-content: space-between; align-items: center; }}
        .logo {{ font-size: 28px; font-weight: bold; color: var(--primary); text-decoration: none; }}
        .search-box {{ position: relative; width: 250px; }}
        .search-box input {{ width: 100%; padding: 10px 15px 10px 35px; border-radius: 20px; border: 1px solid #333; background: #000; color: #fff; }}
        .search-box i {{ position: absolute; left: 12px; top: 12px; color: #888; }}
        .container {{ padding: 20px 4%; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 25px; }}
        .card {{ background: var(--card-bg); border-radius: 10px; overflow: hidden; cursor: pointer; transition: 0.3s; position: relative; border: 1px solid #222; }}
        .card:hover {{ transform: translateY(-5px); box-shadow: 0 10px 20px rgba(229,9,20,0.2); border-color: var(--primary); }}
        .card img {{ width: 100%; aspect-ratio: 2/3; object-fit: cover; }}
        .card-info {{ padding: 12px; font-size: 14px; font-weight: bold; text-align: center; color: #eee; }}
        .back-btn {{ background: var(--primary); color: #fff; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; margin-bottom: 20px; display: none; font-weight: bold; }}
        h2 {{ border-left: 4px solid var(--primary); padding-left: 15px; margin-bottom: 25px; }}
        @media (max-width: 600px) {{ .grid {{ grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); }} .search-box {{ width: 150px; }} }}
    </style>
</head>
<body>
    <div class="header">
        <a href="#" onclick="location.reload()" class="logo">NOW TV ARŞİV</a>
        <div class="search-box">
            <i class="fa fa-search"></i>
            <input type="text" id="searchInput" placeholder="Dizi/Bölüm ara..." onkeyup="search()">
        </div>
    </div>

    <div class="container">
        <button id="backBtn" class="back-btn" onclick="showSeries()"><i class="fa fa-arrow-left"></i> GERİ DÖN</button>
        <h2 id="viewTitle">Tüm Diziler</h2>
        <div id="mainGrid" class="grid"></div>
    </div>

    <script>
        const data = {json_data};
        const mainGrid = document.getElementById('mainGrid');
        const viewTitle = document.getElementById('viewTitle');
        const backBtn = document.getElementById('backBtn');

        function showSeries(filter = "") {{
            mainGrid.innerHTML = "";
            viewTitle.innerText = "Tüm Diziler";
            backBtn.style.display = "none";
            
            for (let id in data) {{
                if (data[id].isim.toLowerCase().includes(filter.toLowerCase())) {{
                    const card = document.createElement('div');
                    card.className = 'card';
                    card.onclick = () => showEpisodes(id);
                    card.innerHTML = `
                        <img src="${{data[id].resim}}" onerror="this.src='https://via.placeholder.com/300x450?text=Görsel+Bulunamadı'">
                        <div class="card-info">${{data[id].isim}}</div>
                    `;
                    mainGrid.appendChild(card);
                }}
            }}
        }}

        function showEpisodes(id) {{
            mainGrid.innerHTML = "";
            viewTitle.innerText = data[id].isim;
            backBtn.style.display = "block";
            window.scrollTo(0,0);
            
            data[id].bolumler.forEach(ep => {{
                const card = document.createElement('div');
                card.className = 'card';
                card.onclick = () => window.open(ep.link, '_blank');
                card.innerHTML = `
                    <img src="${{ep.thumbnail || data[id].resim}}" onerror="this.src='https://via.placeholder.com/300x200?text=Bölüm+Görseli'">
                    <div class="card-info">${{ep.ad}}</div>
                `;
                mainGrid.appendChild(card);
            }});
        }}

        function search() {{
            const val = document.getElementById('searchInput').value;
            showSeries(val);
        }}

        window.onload = () => showSeries();
    </script>
</body>
</html>
'''
    with open("nowtv_vod.html", "w", encoding="utf-8") as f:
        f.write(html_content)

def run_scraper():
    logger.info("🚀 Scraper Başlatıldı...")
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
    
    try:
        response = scraper.get(MAIN_URL, timeout=30)
        soup = BeautifulSoup(response.text, 'html.parser')
        series_data = {}
        cards = soup.select('.list-item, .program-card')

        for card in cards:
            link_elem = card.find('a', href=True)
            if not link_elem: continue
            
            s_url = clean_url(link_elem['href'])
            s_name = (card.select_one('.program-name, .title, h2, h3') or link_elem).get_text(strip=True)
            s_id = slugify(s_name)
            
            if s_id in series_data or not s_name: continue

            img_elem = card.find('img')
            img = clean_url(img_elem.get('src') or img_elem.get('data-src', '')) if img_elem else ""
            
            logger.info(f"🔍 Çekiliyor: {s_name}")
            eps = extract_series_info(scraper, s_url)
            
            if eps:
                series_data[s_id] = {"isim": s_name, "resim": img, "link": s_url, "bolumler": eps}
            
            time.sleep(1)

        with open("nowtv_data.json", "w", encoding="utf-8") as f:
            json.dump(series_data, f, ensure_ascii=False, indent=2)
            
        create_html(series_data)
        logger.info("🎉 İşlem başarıyla bitti, dosyalar hazır.")

    except Exception as e:
        logger.error(f"Hata: {e}")

if __name__ == "__main__":
    run_scraper()

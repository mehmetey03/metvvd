import cloudscraper
from bs4 import BeautifulSoup
import json
import time
import re
import os
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
    """Dizi sayfasından veya /bolumler sayfasından bölümleri ayıklar"""
    episodes = []
    # NowTV bölümleri genellikle /bolumler klasöründe listeler
    target_urls = [series_url.rstrip('/') + "/bolumler", series_url]
    
    for url in target_urls:
        try:
            resp = scraper.get(url, timeout=20)
            if resp.status_code != 200: continue
            
            soup = BeautifulSoup(resp.text, 'html.parser')
            # Tüm linkleri tara
            all_links = soup.find_all('a', href=True)
            
            for link in all_links:
                href = link['href']
                # Linkin içinde 'bolum' geçmeli ve ana dizi linkinden uzun olmalı
                if "/bolum" in href and len(href) > len(series_url):
                    ep_url = clean_url(href)
                    
                    # Başlık Bulma
                    title = link.get_text(strip=True)
                    if not title or len(title) < 3:
                        title_elem = link.find(['h3', 'span', 'div'], class_=re.compile(r'title|name|caption'))
                        title = title_elem.get_text(strip=True) if title_elem else "Yeni Bölüm"
                    
                    # Görsel Bulma
                    img_elem = link.find('img') or link.find_parent().find('img')
                    thumb = clean_url(img_elem.get('src') or img_elem.get('data-src', '')) if img_elem else ""
                    
                    # Tekilleştirme
                    if ep_url not in [e['link'] for e in episodes]:
                        episodes.append({
                            "ad": title,
                            "link": ep_url,
                            "thumbnail": thumb
                        })
            
            if episodes: break # Eğer ilk URL'den veri geldiyse ikinciyi deneme
        except Exception as e:
            logger.error(f"Detay hatası ({url}): {e}")
            
    return episodes[::-1] # Eskiden yeniye sırala

def create_html(series_data):
    """Modern VOD Arayüzü Oluşturur"""
    json_data = json.dumps(series_data, ensure_ascii=False)
    html_template = f'''<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <title>NOW TV VOD ARŞİVİ</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root {{ --primary: #e50914; --bg: #141414; --card-bg: #1f1f1f; --text: #ffffff; }}
        body {{ background: var(--bg); color: var(--text); font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; }}
        .navbar {{ padding: 15px 5%; background: rgba(0,0,0,0.95); position: sticky; top: 0; z-index: 1000; display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid var(--primary); }}
        .logo {{ font-size: 24px; font-weight: bold; color: var(--primary); text-decoration: none; }}
        .search-container input {{ padding: 8px 15px; border-radius: 20px; border: 1px solid #444; background: #000; color: #fff; width: 200px; }}
        .container {{ padding: 20px 5%; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 20px; }}
        .card {{ background: var(--card-bg); border-radius: 10px; overflow: hidden; cursor: pointer; transition: 0.3s; position: relative; border: 1px solid #222; }}
        .card:hover {{ transform: translateY(-5px); border-color: var(--primary); }}
        .card img {{ width: 100%; aspect-ratio: 2/3; object-fit: cover; }}
        .card-body {{ padding: 10px; font-size: 14px; text-align: center; font-weight: 500; }}
        .episode-badge {{ position: absolute; top: 10px; right: 10px; background: var(--primary); color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px; }}
        .player-modal {{ position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.98); z-index: 9999; display: none; align-items: center; justify-content: center; }}
        .player-content {{ width: 90%; max-width: 1100px; position: relative; }}
        .close-player {{ position: absolute; top: -45px; right: 0; color: white; font-size: 35px; cursor: pointer; }}
        iframe {{ width: 100%; aspect-ratio: 16/9; border: none; background: #000; }}
        .back-btn {{ background: var(--primary); color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; margin-bottom: 20px; }}
    </style>
</head>
<body>
    <div class="navbar">
        <a href="#" class="logo">NOW TV ARŞİV</a>
        <div class="search-container"><input type="text" id="search" placeholder="Dizi ara..." onkeyup="filterContent()"></div>
    </div>

    <div class="container">
        <div id="seriesView">
            <h2 style="margin-bottom:20px;">Tüm Diziler</h2>
            <div id="seriesGrid" class="grid"></div>
        </div>

        <div id="episodeView" style="display:none;">
            <button class="back-btn" onclick="showSeries()"><i class="fas fa-arrow-left"></i> Geri Dön</button>
            <h2 id="selectedSeriesTitle" style="margin-bottom:20px;"></h2>
            <div id="episodesGrid" class="grid"></div>
        </div>
    </div>

    <div id="playerModal" class="player-modal">
        <div class="player-content">
            <span class="close-player" onclick="closePlayer()">&times;</span>
            <iframe id="mainPlayer" src="" allowfullscreen></iframe>
        </div>
    </div>

    <script>
        const seriesData = {json_data};
        
        function renderSeries() {{
            const grid = document.getElementById('seriesGrid');
            grid.innerHTML = "";
            for (let id in seriesData) {{
                const s = seriesData[id];
                grid.innerHTML += `
                    <div class="card" onclick="showEpisodes('${{id}}')">
                        <span class="episode-badge">${{s.bolumler.length}} Bölüm</span>
                        <img src="${{s.resim || 'https://via.placeholder.com/200x300?text=Resim+Yok'}}" onerror="this.src='https://via.placeholder.com/200x300?text=Resim+Yok'">
                        <div class="card-body">${{s.isim}}</div>
                    </div>`;
            }}
        }}

        function showEpisodes(id) {{
            const s = seriesData[id];
            document.getElementById('seriesView').style.display = "none";
            document.getElementById('episodeView').style.display = "block";
            document.getElementById('selectedSeriesTitle').innerText = s.isim;
            
            const grid = document.getElementById('episodesGrid');
            grid.innerHTML = "";
            s.bolumler.forEach(ep => {{
                grid.innerHTML += `
                    <div class="card" onclick="playVideo('${{ep.link}}')">
                        <img src="${{ep.thumbnail || s.resim}}" style="aspect-ratio:16/9">
                        <div class="card-body">${{ep.ad}}</div>
                    </div>`;
            }});
            window.scrollTo(0,0);
        }}

        function showSeries() {{
            document.getElementById('seriesView').style.display = "block";
            document.getElementById('episodeView').style.display = "none";
        }}

        function playVideo(url) {{
            document.getElementById('mainPlayer').src = url;
            document.getElementById('playerModal').style.display = "flex";
        }}

        function closePlayer() {{
            document.getElementById('playerModal').style.display = "none";
            document.getElementById('mainPlayer').src = "";
        }}

        function filterContent() {{
            const val = document.getElementById('search').value.toLowerCase();
            document.querySelectorAll('#seriesGrid .card').forEach(card => {{
                card.style.display = card.innerText.toLowerCase().includes(val) ? "block" : "none";
            }});
        }}

        renderSeries();
    </script>
</body>
</html>'''
    with open("nowtv_vod.html", "w", encoding="utf-8") as f:
        f.write(html_template)

def run_scraper():
    logger.info("🚀 Scraper Başlatıldı...")
    scraper = cloudscraper.create_scraper(
        browser={'browser': 'chrome','platform': 'windows','desktop': True}
    )
    
    try:
        response = scraper.get(MAIN_URL, timeout=30)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Dizi kartlarını yakala
        # NowTV güncel seçicileri: .list-item veya .program-card
        cards = soup.select('.list-item, .program-card, a[href*="/dizi-izle/"]')
        series_data = {}

        for card in cards:
            link_elem = card if card.name == 'a' else card.find('a', href=True)
            if not link_elem: continue
            
            raw_url = link_elem['href']
            if "/dizi-izle/" not in raw_url: continue
            
            s_url = clean_url(raw_url)
            # İsim bulma
            name_elem = card.select_one('.program-name, .title, span')
            s_name = name_elem.get_text(strip=True) if name_elem else "Bilinmeyen Dizi"
            
            if len(s_name) < 2: continue # Hatalı verileri ele
            
            s_id = slugify(s_name)
            if s_id in series_data: continue

            img_elem = card.find('img')
            s_img = clean_url(img_elem.get('src') or img_elem.get('data-src', '')) if img_elem else ""

            logger.info(f"🔍 Dizi İşleniyor: {s_name}")
            
            # Bölümleri çek
            episodes = extract_series_info(scraper, s_url)
            
            if episodes:
                series_data[s_id] = {
                    "isim": s_name,
                    "resim": s_img,
                    "link": s_url,
                    "bolumler": episodes
                }
                logger.info(f"✅ {len(episodes)} bölüm bulundu.")
            else:
                logger.warning(f"⚠️ {s_name} için bölüm bulunamadı, atlanıyor.")
            
            time.sleep(1.5) # Banlanmamak için kısa bekleme

        # Kaydet
        if series_data:
            with open("nowtv_data.json", "w", encoding="utf-8") as f:
                json.dump(series_data, f, ensure_ascii=False, indent=2)
            create_html(series_data)
            logger.info(f"🎉 İşlem Tamam! {len(series_data)} dizi arşive eklendi.")
        else:
            logger.error("❌ Hiçbir veri çekilemedi. Seçiciler (Selectors) değişmiş olabilir.")

    except Exception as e:
        logger.error(f"Kritik Hata: {e}")

if __name__ == "__main__":
    run_scraper()

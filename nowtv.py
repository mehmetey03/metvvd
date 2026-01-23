import cloudscraper
from bs4 import BeautifulSoup
import json
import time
import re
import os

# Ayarlar
BASE_URL = "https://www.nowtv.com.tr"
# Now TV'de arşiv sistemi sayfa sayfa veya "Load More" (Ajax) ile çalışır
ARCHIVE_URL = "https://www.nowtv.com.tr/diziler/arsiv?page="
BRADMAX_PLAYER = "https://bradmax.com/client/embed-player/d9decbf0d308f4bb91825c3f3a2beb7b0aaee2f6_8493?mediaUrl="

def slugify(text):
    mapping = {'ç':'c','ğ':'g','ı':'i','ö':'o','ş':'s','ü':'u','İ':'i'}
    text = text.lower()
    for tr, en in mapping.items(): text = text.replace(tr, en)
    return re.sub(r'[^a-z0-9]+', '-', text).strip('-')

def get_now_m3u8_logic(scraper, url):
    """PHP'deki gibi önce sayfayı sonra M3U8'i yakalar"""
    try:
        # Sayfayı çek
        r = scraper.get(url, timeout=10)
        
        # 1. Aşama: Sayfa içindeki scriptlerde veya meta taglarda m3u8 ara
        m3u8_patterns = [
            r'https?://[^"\']+\.m3u8[^"\']*',
            r'["\']videoUrl["\']\s*:\s*["\']([^"\']+)["\']',
            r'source\s+src=["\']([^"\']+\.m3u8)["\']'
        ]
        
        for p in m3u8_patterns:
            m = re.search(p, r.text)
            if m:
                found = m.group(1) if "(" in p else m.group(0)
                return found.replace('\\/', '/')
        
        # 2. Aşama: Eğer m3u8 yoksa, Now TV'nin Player iframe'ini ara
        iframe = re.search(r'iframe src=["\']([^"\']+/embed/[^"\']+)["\']', r.text)
        if iframe:
            return iframe.group(1)

        return url
    except:
        return url

def run_now_scraper():
    print("🚀 Now TV VOD Scraper Başlatıldı...")
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
    series_data = {}

    # İlk 5 sayfayı tara (Arşivi genişletmek istersen 10 yapabilirsin)
    for page in range(1, 6):
        print(f"📄 Sayfa {page} taranıyor...")
        try:
            resp = scraper.get(f"{ARCHIVE_URL}{page}", timeout=15)
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # Senin paylaştığın HTML yapısındaki seçiciler:
            items = soup.select('.list-item')
            if not items: break

            for item in items:
                name_tag = item.select_one('.program-name strong')
                link_tag = item.select_one('.list-item-image a')
                img_tag = item.select_one('.list-item-image img')

                if name_tag and link_tag:
                    title = name_tag.get_text(strip=True)
                    href = link_tag['href']
                    poster = img_tag['src'] if img_tag else ""
                    if poster.startswith('/'): poster = BASE_URL + poster
                    
                    dizi_id = slugify(title)
                    print(f"  📺 {title} taranıyor...")

                    # Bölümler sayfasına git (/izle -> /bolumler)
                    # Now TV'de bölümler genellikle dizi ana sayfasının altındadır
                    target_url = href.replace('/izle', '') + "/bolumler"
                    if not target_url.startswith('http'): target_url = BASE_URL + target_url

                    b_resp = scraper.get(target_url)
                    b_soup = BeautifulSoup(b_resp.text, 'html.parser')
                    
                    # Bölüm kartlarını bul
                    b_cards = b_soup.select('.list-item-image a')
                    
                    eps = []
                    for bc in b_cards[:15]: # Her diziden son 15 bölüm
                        b_link = bc['href']
                        if not b_link.startswith('http'): b_link = BASE_URL + b_link
                        
                        # PHP Mantığı ile M3U8 çek
                        real_link = get_now_m3u8_logic(scraper, b_link)
                        
                        # Bölüm adını linkten veya varsa başlıktan al
                        b_title = b_link.split('/')[-1].replace('-', ' ').title()
                        
                        eps.append({"ad": b_title, "link": real_link})
                    
                    if eps:
                        series_data[dizi_id] = {
                            "resim": poster,
                            "bolumler": eps[::-1] # Eskiden yeniye
                        }
            time.sleep(1)
        except Exception as e:
            print(f"❌ Hata oluştu: {e}")
            continue

    # HTML OLUŞTURMA
    create_final_html(series_data)

def create_final_html(data):
    file_name = "nowtv_vod.html"
    json_data = json.dumps(data, ensure_ascii=False)
    
    html_content = f'''<!DOCTYPE html>
<html lang="tr">
<head>
    <title>ME TV NOW VOD</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://code.jquery.com/jquery-3.5.1.min.js"></script>
    <style>
        body {{ margin: 0; background: #00040d; color: white; font-family: sans-serif; font-style: italic; overflow-x: hidden; }}
        .header {{ width: 100%; height: 65px; background: #15161a; border-bottom: 1px solid #323442; padding: 10px 20px; box-sizing: border-box; display: flex; justify-content: space-between; align-items: center; position: sticky; top: 0; z-index: 1000; }}
        .logo {{ font-weight: bold; color: #572aa7; font-size: 22px; text-transform: uppercase; }}
        .search-box input {{ background: #0a0e17; border: 1px solid #323442; color: white; padding: 10px 15px; border-radius: 25px; width: 200px; outline: none; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 20px; padding: 20px; }}
        .card {{ background: #15161a; border: 1px solid #323442; border-radius: 12px; overflow: hidden; cursor: pointer; transition: 0.3s; position: relative; }}
        .card:hover {{ border-color: #572aa7; transform: translateY(-5px); }}
        .card img {{ width: 100%; aspect-ratio: 2/3; object-fit: cover; }}
        .card-title {{ position: absolute; bottom: 0; background: linear-gradient(transparent, rgba(0,0,0,0.9)); width: 100%; padding: 10px; font-size: 12px; text-align: center; font-weight: bold; }}
        .hidden {{ display: none !important; }}
        .player-overlay {{ position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: black; z-index: 9999; display: none; }}
        .btn {{ background: #572aa7; color: white; padding: 10px 20px; border: none; cursor: pointer; border-radius: 5px; margin: 10px; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="header">
        <div class="logo">ME TV NOW</div>
        <div class="search-box"><input type="text" id="searchInput" placeholder="Dizi ara..." oninput="doSearch()"></div>
    </div>

    <div id="mainGrid" class="grid"></div>

    <div id="episodeGridContainer" class="hidden">
        <button class="btn" onclick="goBack()">← ANA SAYFA</button>
        <div id="episodeGrid" class="grid"></div>
    </div>

    <div id="playerOverlay" class="player-overlay">
        <button class="btn" onclick="closePlayer()">✕ KAPAT</button>
        <div id="playerContainer" style="height: calc(100% - 70px);"></div>
    </div>

    <script>
        const database = {json_data};
        const BRADMAX = "{BRADMAX_PLAYER}";

        function init() {{
            const grid = document.getElementById("mainGrid");
            Object.keys(database).forEach(id => {{
                const item = database[id];
                const div = document.createElement("div");
                div.className = "card";
                div.innerHTML = `<img src="${{item.resim}}"><div class="card-title">${{id.replace(/-/g,' ').toUpperCase()}}</div>`;
                div.onclick = () => showEpisodes(id);
                grid.appendChild(div);
            }});
        }}

        function showEpisodes(id) {{
            window.scrollTo(0,0);
            document.getElementById("mainGrid").classList.add("hidden");
            document.getElementById("episodeGridContainer").classList.remove("hidden");
            const grid = document.getElementById("episodeGrid");
            grid.innerHTML = "";
            database[id].bolumler.forEach(ep => {{
                const div = document.createElement("div");
                div.className = "card";
                div.innerHTML = `<img src="${{database[id].resim}}"><div class="card-title">${{ep.ad}}</div>`;
                div.onclick = () => playVideo(ep.link);
                grid.appendChild(div);
            }});
        }}

        function playVideo(link) {{
            const container = document.getElementById("playerContainer");
            document.getElementById("playerOverlay").style.display = "block";
            let finalUrl = link.includes(".m3u8") ? BRADMAX + encodeURIComponent(link) : link;
            container.innerHTML = `<iframe src="${{finalUrl}}&autoplay=true" width="100%" height="100%" frameborder="0" allowfullscreen></iframe>`;
        }}

        function goBack() {{
            document.getElementById("mainGrid").classList.remove("hidden");
            document.getElementById("episodeGridContainer").classList.add("hidden");
        }}

        function closePlayer() {{
            document.getElementById("playerOverlay").style.display = "none";
            document.getElementById("playerContainer").innerHTML = "";
        }}

        function doSearch() {{
            let q = $("#searchInput").val().toLowerCase();
            $(".card").each(function() {{
                $(this).toggle($(this).text().toLowerCase().includes(q));
            }});
        }}

        init();
    </script>
</body>
</html>'''

    with open(file_name, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"✅ Bitti! {file_name} dosyası hazır.")

if __name__ == "__main__":
    run_now_scraper()

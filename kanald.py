import requests
from bs4 import BeautifulSoup
import json
import time
import re
from urllib.parse import urljoin, urlparse

BASE_URL = "https://www.kanald.com.tr"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def get_soup(url):
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        return BeautifulSoup(response.content, "html.parser")
    except: return None

def get_all_video_series():
    print("🚀 Kanal D serileri taranıyor...")
    soup = get_soup(BASE_URL)
    if not soup: return []
    
    series_list = []
    # Diziler ve Programlar sayfalarını tara
    for path in ['/diziler', '/programlar']:
        page_soup = get_soup(BASE_URL + path)
        if not page_soup: continue
        
        cards = page_soup.select('a[href*="/diziler/"], a[href*="/programlar/"]')
        for card in cards:
            href = card.get('href')
            if not href or href == path: continue
            
            full_url = urljoin(BASE_URL, href)
            title = card.get('title') or card.text.strip()
            img = card.find('img')
            poster = img.get('data-src') or img.get('src') if img else ""
            
            if title and full_url not in [s['url'] for s in series_list]:
                series_list.append({
                    "name": title.replace('İzle', '').strip(),
                    "url": full_url,
                    "poster": urljoin(BASE_URL, poster) if poster else ""
                })
    return series_list[:12] # Örnek olması için ilk 12 seri

def get_series_episodes(series_url, series_name):
    print(f"  📺 '{series_name}' videoları aranıyor...")
    # Bu kısım simülasyon ve basit scraping içerir 
    # Gerçek m3u8 linkleri genellikle iframe içindeki api'den gelir
    # Demo amaçlı doğrudan video sayfasına gider
    return [
        {"ad": f"{series_name} - Tanıtım", "link": "https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8"},
        {"ad": f"{series_name} - Son Bölüm", "link": "https://bitdash-a.akamaihd.net/content/sintel/hls/playlist.m3u8"}
    ]

def create_html_file(data):
    json_str = json.dumps(data, ensure_ascii=False)
    
    html_template = f'''
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <title>Kanal D VOD Player</title>
    <script src="https://cdn.jsdelivr.net/npm/hls.js@latest"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root {{ --bg: #050a12; --card: #121a2d; --accent: #007bff; --text: #ffffff; }}
        body {{ background: var(--bg); color: var(--text); font-family: sans-serif; margin: 0; padding: 20px; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 20px; }}
        .card {{ background: var(--card); border-radius: 10px; overflow: hidden; cursor: pointer; transition: 0.3s; border: 1px solid #222; }}
        .card:hover {{ transform: translateY(-5px); border-color: var(--accent); }}
        .card img {{ width: 100%; height: 280px; object-fit: cover; }}
        .card-body {{ padding: 15px; font-weight: bold; text-align: center; }}
        
        #player-overlay {{ position: fixed; top:0; left:0; width:100%; height:100%; background: rgba(0,0,0,0.95); display:none; flex-direction:column; align-items:center; justify-content:center; z-index:1000; }}
        video {{ width: 80%; max-width: 1000px; background: #000; border-radius: 10px; box-shadow: 0 0 30px var(--accent); }}
        .close-btn {{ position: absolute; top: 20px; right: 20px; font-size: 30px; cursor: pointer; color: #fff; }}
        .ep-list {{ margin-top: 20px; display: none; }}
        .ep-item {{ background: #222; padding: 10px; margin: 5px; border-radius: 5px; cursor: pointer; }}
        .ep-item:hover {{ background: var(--accent); }}
    </style>
</head>
<body>
    <h1><i class="fas fa-play"></i> Kanal D Kütüphanesi</h1>
    <div id="series-grid" class="grid"></div>

    <div id="ep-list-container" class="ep-list">
        <button onclick="showGrid()" style="padding:10px; cursor:pointer;"><i class="fas fa-arrow-left"></i> Geri Dön</button>
        <h2 id="selected-title"></h2>
        <div id="episodes-container"></div>
    </div>

    <div id="player-overlay">
        <span class="close-btn" onclick="closePlayer()">&times;</span>
        <video id="video" controls></video>
        <h3 id="video-title"></h3>
    </div>

    <script>
        const data = {json_str};
        const grid = document.getElementById('series-grid');
        const epList = document.getElementById('ep-list-container');
        
        // Grid Oluştur
        Object.keys(data).forEach(key => {{
            const item = data[key];
            const div = document.createElement('div');
            div.className = 'card';
            div.innerHTML = `<img src="${{item.resim}}" alt=""> <div class="card-body">${{item.name}}</div>`;
            div.onclick = () => showEpisodes(key);
            grid.appendChild(div);
        }});

        function showEpisodes(key) {{
            grid.style.display = 'none';
            epList.style.display = 'block';
            const item = data[key];
            document.getElementById('selected-title').innerText = item.name;
            const container = document.getElementById('episodes-container');
            container.innerHTML = '';
            item.bolumler.forEach(ep => {{
                const d = document.createElement('div');
                d.className = 'ep-item';
                d.innerText = ep.ad;
                d.onclick = () => playVideo(ep.link, ep.ad);
                container.appendChild(d);
            }});
        }}

        function showGrid() {{
            grid.style.display = 'grid';
            epList.style.display = 'none';
        }}

        function playVideo(url, title) {{
            const video = document.getElementById('video');
            const overlay = document.getElementById('player-overlay');
            overlay.style.display = 'flex';
            document.getElementById('video-title').innerText = title;

            if (Hls.isSupported()) {{
                const hls = new Hls();
                hls.loadSource(url);
                hls.attachMedia(video);
                hls.on(Hls.Events.MANIFEST_PARSED, () => video.play());
            }} else if (video.canPlayType('application/vnd.apple.mpegurl')) {{
                video.src = url;
                video.addEventListener('loadedmetadata', () => video.play());
            }}
        }}

        function closePlayer() {{
            const video = document.getElementById('video');
            video.pause();
            document.getElementById('player-overlay').style.display = 'none';
        }}
    </script>
</body>
</html>
'''
    with open("kanald_library.html", "w", encoding="utf-8") as f:
        f.write(html_template)
    print("\n✅ Başarılı! 'kanald_library.html' dosyası oluşturuldu.")

def main():
    series = get_all_video_series()
    final_data = {}
    for s in series:
        slug = s['name'].lower().replace(' ', '-')
        final_data[slug] = {
            "name": s['name'],
            "resim": s['poster'],
            "bolumler": get_series_episodes(s['url'], s['name'])
        }
    create_html_file(final_data)

if __name__ == "__main__":
    main()

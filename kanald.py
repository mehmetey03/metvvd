import requests
from bs4 import BeautifulSoup
import json
import re
from urllib.parse import urljoin

BASE_URL = "https://www.kanald.com.tr"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def get_soup(url):
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        return BeautifulSoup(response.content, "html.parser")
    except Exception as e:
        print(f"Hata oluştu: {url} -> {e}")
        return None

def get_all_series():
    print("🚀 Kanal D serileri taranıyor...")
    series_list = []
    # Gereksiz linkleri elemek için filtre
    exclude = ["TÜMÜNÜ GÖR", "DİZİLER", "PROGRAMLAR", "ARŞİV", "CANLI YAYIN", "HABER"]

    for path in ['/diziler', '/programlar']:
        soup = get_soup(BASE_URL + path)
        if not soup: continue
        
        # Kartları bul (Kanal D'nin güncel CSS sınıfları)
        cards = soup.select('div.card')
        for card in cards:
            link_tag = card.find('a', href=True)
            title_tag = card.select_one('.card-title')
            img_tag = card.find('img')

            if link_tag and title_tag:
                title = title_tag.get_text(strip=True)
                href = link_tag['href']
                
                # Filtreleme
                if any(x in title.upper() for x in exclude) or len(title) < 3:
                    continue

                full_url = urljoin(BASE_URL, href)
                poster = img_tag.get('data-src') or img_tag.get('src') if img_tag else ""
                
                if full_url not in [s['url'] for s in series_list]:
                    series_list.append({
                        "name": title,
                        "url": full_url,
                        "poster": urljoin(BASE_URL, poster) if poster else ""
                    })
    
    print(f"✅ {len(series_list)} geçerli seri bulundu.")
    return series_list[:20]

def create_html(data):
    json_str = json.dumps(data, ensure_ascii=False)
    html_content = f'''<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Kanal D VOD</title>
    <script src="https://cdn.jsdelivr.net/npm/hls.js@latest"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root {{ --bg: #0b0f19; --card: #161d2f; --accent: #3a86ff; --text: #ffffff; }}
        body {{ background: var(--bg); color: var(--text); font-family: 'Segoe UI', sans-serif; margin: 0; padding: 20px; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 20px; max-width: 1200px; margin: 0 auto; }}
        .card {{ background: var(--card); border-radius: 12px; overflow: hidden; cursor: pointer; transition: 0.3s; border: 1px solid #232d45; }}
        .card:hover {{ transform: translateY(-5px); border-color: var(--accent); box-shadow: 0 10px 20px rgba(0,0,0,0.5); }}
        .card img {{ width: 100%; height: 280px; object-fit: cover; }}
        .card-info {{ padding: 12px; text-align: center; font-weight: 600; font-size: 14px; }}
        #player-overlay {{ position: fixed; top:0; left:0; width:100%; height:100%; background: rgba(0,0,0,0.98); display:none; flex-direction:column; align-items:center; justify-content:center; z-index:9999; }}
        video {{ width: 90%; max-width: 900px; border-radius: 8px; background: #000; }}
        .close-btn {{ position: absolute; top: 20px; right: 20px; font-size: 40px; cursor: pointer; color: #fff; line-height: 1; }}
        .back-btn {{ background: var(--accent); color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; margin-bottom: 20px; }}
    </style>
</head>
<body>
    <div id="main-view">
        <h1 style="text-align:center">📺 Kanal D Video Arşivi</h1>
        <div id="series-grid" class="grid"></div>
    </div>

    <div id="episodes-view" style="display:none; max-width: 1200px; margin: 0 auto;">
        <button class="back-btn" onclick="showMain()"><i class="fas fa-arrow-left"></i> Geri Dön</button>
        <h2 id="view-title"></h2>
        <div id="episodes-list" class="grid"></div>
    </div>

    <div id="player-overlay">
        <span class="close-btn" onclick="closePlayer()">&times;</span>
        <video id="video" controls></video>
        <h3 id="playing-title"></h3>
    </div>

    <script>
        const library = {json_str};
        const grid = document.getElementById('series-grid');

        Object.keys(library).forEach(id => {{
            const item = library[id];
            const div = document.createElement('div');
            div.className = 'card';
            div.innerHTML = `<img src="${{item.resim || 'https://via.placeholder.com/200x300'}}" loading="lazy">
                             <div class="card-info">${{item.name}}</div>`;
            div.onclick = () => showEpisodes(id);
            grid.appendChild(div);
        }});

        function showEpisodes(id) {{
            document.getElementById('main-view').style.display = 'none';
            document.getElementById('episodes-view').style.display = 'block';
            const data = library[id];
            document.getElementById('view-title').innerText = data.name;
            const list = document.getElementById('episodes-list');
            list.innerHTML = '';
            
            // Demo Linkler (Gerçek m3u8 scraping için ekstra fonksiyon gerekir)
            const demoLinks = [
                {{ad: "Fragman 1", link: "https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8"}},
                {{ad: "Özel Sahneler", link: "https://bitdash-a.akamaihd.net/content/sintel/hls/playlist.m3u8"}}
            ];

            demoLinks.forEach(ep => {{
                const d = document.createElement('div');
                d.className = 'card';
                d.innerHTML = `<div class="card-info" style="height:100px; display:flex; align-items:center; justify-content:center">${{ep.ad}}</div>`;
                d.onclick = () => play(ep.link, ep.ad);
                list.appendChild(d);
            }});
        }}

        function showMain() {{
            document.getElementById('main-view').style.display = 'block';
            document.getElementById('episodes-view').style.display = 'none';
        }}

        function play(url, title) {{
            const v = document.getElementById('video');
            document.getElementById('player-overlay').style.display = 'flex';
            document.getElementById('playing-title').innerText = title;
            if(Hls.isSupported()) {{
                const hls = new Hls();
                hls.loadSource(url);
                hls.attachMedia(v);
                hls.on(Hls.Events.MANIFEST_PARSED, () => v.play());
            }} else {{ v.src = url; v.play(); }}
        }}

        function closePlayer() {{
            const v = document.getElementById('video');
            v.pause();
            document.getElementById('player-overlay').style.display = 'none';
        }}
    </script>
</body>
</html>'''
    with open("kanald_library.html", "w", encoding="utf-8") as f:
        f.write(html_content)

if __name__ == "__main__":
    series = get_all_series()
    data_map = {{}}
    for s in series:
        data_map[s['name']] = {{"name": s['name'], "resim": s['poster'], "url": s['url']}}
    create_html(data_map)
    print("✨ kanald_library.html oluşturuldu!")

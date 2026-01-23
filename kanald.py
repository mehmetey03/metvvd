import requests
from bs4 import BeautifulSoup
import json
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
        print(f"Hata: {url} -> {e}")
        return None

def get_all_series():
    print("🚀 Kanal D serileri taranıyor...")
    series_list = []
    exclude = ["TÜMÜNÜ GÖR", "DİZİLER", "PROGRAMLAR", "ARŞİV", "CANLI YAYIN", "HABER"]

    for path in ['/diziler', '/programlar']:
        soup = get_soup(BASE_URL + path)
        if not soup: continue
        
        # Kanal D'nin farklı kart yapılarını yakalamak için genişletilmiş seçiciler
        cards = soup.find_all(['div', 'a'], class_=['card', 'content-card', 'inner-content'])
        
        for card in cards:
            # Başlığı bul (farklı hiyerarşilerde olabilir)
            title_tag = card.find(['span', 'h2', 'h3'], class_=['card-title', 'title'])
            if not title_tag:
                title_tag = card.find('img', alt=True)
                title = title_tag['alt'] if title_tag else ""
            else:
                title = title_tag.get_text(strip=True)

            # Linki bul
            link_tag = card if card.name == 'a' else card.find('a', href=True)
            img_tag = card.find('img')

            if link_tag and title:
                href = link_tag.get('href', '')
                if any(x in title.upper() for x in exclude) or len(title) < 3:
                    continue

                full_url = urljoin(BASE_URL, href)
                # Resim URL'sini çek
                poster = ""
                if img_tag:
                    poster = img_tag.get('data-src') or img_tag.get('src') or ""

                if full_url not in [s['url'] for s in series_list]:
                    series_list.append({
                        "name": title,
                        "url": full_url,
                        "poster": urljoin(BASE_URL, poster) if poster else ""
                    })
    
    print(f"✅ {len(series_list)} geçerli seri bulundu.")
    return series_list

def create_html(data):
    # JavaScript içindeki süslü parantezler ile Python f-string parantezlerinin 
    # çakışmaması için süslü parantezleri çiftledim {{ }}
    json_str = json.dumps(data, ensure_ascii=False)
    html_content = f'''<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Kanal D Arşivi</title>
    <script src="https://cdn.jsdelivr.net/npm/hls.js@latest"></script>
    <style>
        body {{ background: #0b0f19; color: white; font-family: sans-serif; padding: 20px; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 15px; }}
        .card {{ background: #161d2f; border-radius: 8px; overflow: hidden; cursor: pointer; border: 1px solid #232d45; }}
        .card img {{ width: 100%; height: 250px; object-fit: cover; }}
        .card-info {{ padding: 10px; font-size: 14px; text-align: center; }}
        #player {{ position: fixed; top:0; left:0; width:100%; height:100%; background: black; display:none; flex-direction:column; align-items:center; justify-content:center; z-index:99; }}
        video {{ width: 90%; max-height: 80%; }}
        .close {{ position: absolute; top: 20px; right: 20px; font-size: 30px; cursor: pointer; }}
    </style>
</head>
<body>
    <h1 style="text-align:center">📺 Kanal D Video Arşivi</h1>
    <div id="grid" class="grid"></div>

    <div id="player">
        <span class="close" onclick="document.getElementById('player').style.display='none'; document.getElementById('v').pause();">&times;</span>
        <video id="v" controls></video>
    </div>

    <script>
        const library = {json_str};
        const grid = document.getElementById('grid');

        Object.keys(library).forEach(key => {{
            const item = library[key];
            const div = document.createElement('div');
            div.className = 'card';
            div.innerHTML = `<img src="${{item.resim}}" loading="lazy"><div class="card-info">${{item.name}}</div>`;
            div.onclick = () => {{
                const v = document.getElementById('v');
                document.getElementById('player').style.display = 'flex';
                const testUrl = "https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8"; // Örnek oynatma
                if(Hls.isSupported()) {{
                    const hls = new Hls();
                    hls.loadSource(testUrl);
                    hls.attachMedia(v);
                    hls.on(Hls.Events.MANIFEST_PARSED, () => v.play());
                }}
            }};
            grid.appendChild(div);
        }});
    </script>
</body>
</html>'''
    with open("kanald_library.html", "w", encoding="utf-8") as f:
        f.write(html_content)

if __name__ == "__main__":
    series = get_all_series()
    # HATA BURADAYDI: {{}} yerine {} kullanıldı.
    data_map = {} 
    for s in series:
        data_map[s['name']] = {"name": s['name'], "resim": s['poster'], "url": s['url']}
    
    create_html(data_map)
    print("✨ kanald_library.html başarıyla oluşturuldu!")

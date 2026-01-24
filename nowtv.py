import cloudscraper
from bs4 import BeautifulSoup
import json
import time
import re
import subprocess

# --- AYARLAR ---
JSON_SOURCE_URL = "https://raw.githubusercontent.com/mehmetey03/metvvd/refs/heads/main/nowtv_data.json"
BASE_URL = "https://www.nowtv.com.tr"
BRADMAX_PLAYER = "https://bradmax.com/client/embed-player/d9decbf0d308f4bb91825c3f3a2beb7b0aaee2f6_8493?mediaUrl="

def slugify(text):
    mapping = {'ç':'c','ğ':'g','ı':'i','ö':'o','ş':'s','ü':'u','İ':'i','I':'i'}
    text = text.lower()
    for tr, en in mapping.items(): text = text.replace(tr, en)
    return re.sub(r'[^a-z0-9]+', '-', text).strip('-')

def get_now_m3u8(scraper, bolum_url):
    try:
        time.sleep(0.5)  # Engel yememek için bekleme süresini biraz artırdık
        r = scraper.get(bolum_url, timeout=10)
        # Video linkini sayfa kaynağından regex ile çek (JSON içindeki videoSource veya m3u8)
        m3u8_match = re.search(r'(https?://[^\s"\']+\.m3u8[^\s"\']*)', r.text)
        if m3u8_match:
            return m3u8_match.group(0).replace('\\/', '/')
        return bolum_url
    except:
        return bolum_url

def commit_and_push(file_name):
    print(f"\n📤 {file_name} GitHub'a gönderiliyor...")
    try:
        subprocess.run(["git", "config", "--global", "user.name", "github-actions[bot]"], check=True)
        subprocess.run(["git", "config", "--global", "user.email", "github-actions[bot]@users.noreply.github.com"], check=True)
        subprocess.run(["git", "add", file_name], check=True)
        status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout
        if status:
            subprocess.run(["git", "commit", "-m", "🔄 NOW TV VOD: All Episodes Updated"], check=True)
            subprocess.run(["git", "push"], check=True)
            print("🚀 GitHub'a başarıyla yüklendi!")
        else:
            print("ℹ️ Değişiklik yok, commit atlanıyor.")
    except Exception as e:
        print(f"❌ Git Hatası: {e}")

def run_scraper():
    print("🚀 Bot Başlatıldı. Kaynak JSON okunuyor...")
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
    
    try:
        source_resp = scraper.get(JSON_SOURCE_URL)
        target_series = json.loads(source_resp.text)
    except Exception as e:
        print(f"❌ JSON okuma hatası: {e}")
        return

    memory_data = {}

    for dizi_key, info in target_series.items():
        title = info['isim']
        dizi_url = info['link']
        poster = info['resim']
        
        # /izle kısmını /bolumler ile değiştirerek asıl listeye ulaş
        bolumler_url = dizi_url.split('/izle')[0].rstrip('/') + "/bolumler"
        print(f"\n📺 {title} taranıyor -> {bolumler_url}")
        
        try:
            b_resp = scraper.get(bolumler_url, timeout=15)
            b_soup = BeautifulSoup(b_resp.text, 'html.parser')
            
            eps = []
            
            # YÖNTEM 1: Dropdown (Bölüm Ara) Menüsünden Tüm Linkleri Çek
            select_box = b_soup.find('select', id='video-finder-changer')
            if select_box:
                # data-target özniteliği olan tüm option'ları bul
                options = select_box.find_all('option', {'data-target': True})
                print(f"✅ Toplam {len(options)} bölüm menüde bulundu.")
                
                for opt in options:
                    b_url = opt['data-target']
                    b_title = opt.get_text(strip=True)
                    
                    m3u8 = get_now_m3u8(scraper, b_url)
                    eps.append({"ad": b_title, "link": m3u8})
                    print(f"   🔗 Eklendi: {b_title}")

            # YÖNTEM 2: Eğer Menü Boşsa Sayfadaki Kartları Tara (Fallback)
            if not eps:
                b_cards = b_soup.find_all('div', class_='list-item')
                for bc in b_cards:
                    link_tag = bc.find('a', href=True)
                    if link_tag and "/bolum/" in link_tag['href']:
                        full_b_url = BASE_URL + link_tag['href'] if link_tag['href'].startswith('/') else link_tag['href']
                        title_tag = bc.select_one('.program-name, .title')
                        b_title = title_tag.get_text(strip=True) if title_tag else "Bölüm"
                        
                        m3u8 = get_now_m3u8(scraper, full_b_url)
                        if not any(e['link'] == m3u8 for e in eps):
                            eps.append({"ad": b_title, "link": m3u8})
                            print(f"   🔗 Karttan Bulundu: {b_title}")

            if eps:
                # Listeyi Bölüm 1 en üstte olacak şekilde sıralamak istersen:
                # eps.reverse() 
                memory_data[dizi_key] = {
                    "isim": title,
                    "resim": poster,
                    "bolumler": eps
                }
        except Exception as e:
            print(f"   ⚠️ {title} bölümleri çekilirken hata: {e}")

    create_html(memory_data)

def create_html(series_data):
    file_name = "nowtv_vod.html"
    json_embedded = json.dumps(series_data, ensure_ascii=False)
    
    html_template = f'''<!DOCTYPE html>
<html lang="tr">
<head>
    <title>NOW VOD PLAYER</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{ margin: 0; background: #080808; color: #fff; font-family: 'Segoe UI', Tahoma, sans-serif; }}
        .navbar {{ background: #000; padding: 15px 30px; border-bottom: 2px solid #f50057; display: flex; justify-content: space-between; align-items: center; position: sticky; top: 0; z-index: 100; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 20px; padding: 30px; }}
        .card {{ background: #121212; border-radius: 10px; overflow: hidden; cursor: pointer; transition: 0.3s; border: 1px solid #222; position: relative; }}
        .card:hover {{ transform: scale(1.05); border-color: #f50057; box-shadow: 0 0 15px rgba(245, 0, 87, 0.3); }}
        .card img {{ width: 100%; aspect-ratio: 2/3; object-fit: cover; }}
        .card-name {{ padding: 10px; text-align: center; font-size: 13px; font-weight: bold; background: rgba(0,0,0,0.7); }}
        .player-view {{ position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: #000; z-index: 1000; display: none; }}
        .btn {{ background: #f50057; color: #fff; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; font-weight: bold; margin: 10px; }}
        .hidden {{ display: none !important; }}
        input#searchInput {{ padding: 10px; border-radius: 20px; border: 1px solid #333; width: 250px; background: #111; color: white; }}
    </style>
</head>
<body>
    <div class="navbar">
        <div style="font-size: 22px; font-weight: bold; color: #f50057;">METV NOW VOD</div>
        <input type="text" id="searchInput" placeholder="Dizi veya bölüm ara..." oninput="search()">
    </div>
    
    <div id="mainGrid" class="grid"></div>
    <div id="episodeGrid" class="grid hidden"></div>
    
    <div id="playerView" class="player-view">
        <div style="display:flex; justify-content: space-between; align-items:center; padding: 0 10px;">
             <button class="btn" onclick="closePlayer()">✕ KAPAT</button>
             <span id="playingTitle" style="color:#f50057; font-weight:bold;"></span>
        </div>
        <div id="videoContainer" style="height: calc(100% - 70px);"></div>
    </div>

    <script>
        const seriesData = {json_embedded};
        const BRADMAX = "{BRADMAX_PLAYER}";

        function init() {{
            const grid = document.getElementById("mainGrid");
            grid.innerHTML = "";
            Object.keys(seriesData).forEach(id => {{
                const d = seriesData[id];
                const card = document.createElement("div");
                card.className = "card";
                card.innerHTML = `<img src="${{d.resim}}"><div class="card-name">${{d.isim}}</div>`;
                card.onclick = () => showEpisodes(id);
                grid.appendChild(card);
            }});
        }}

        function showEpisodes(id) {{
            window.scrollTo(0,0);
            document.getElementById("mainGrid").classList.add("hidden");
            const eg = document.getElementById("episodeGrid");
            eg.classList.remove("hidden");
            eg.innerHTML = `<div style="grid-column: 1/-1;"><button class="btn" onclick="goBack()">← ANA SAYFA</button><h2 style="display:inline; margin-left:20px;">${{seriesData[id].isim}}</h2></div>`;
            
            seriesData[id].bolumler.forEach(ep => {{
                const card = document.createElement("div");
                card.className = "card ep-card";
                card.innerHTML = `<img src="${{seriesData[id].resim}}" style="aspect-ratio:16/9;"><div class="card-name">${{ep.ad}}</div>`;
                card.onclick = () => playVideo(ep.link, ep.ad);
                eg.appendChild(card);
            }});
        }}

        function playVideo(link, title) {{
            document.getElementById("playerView").style.display = "block";
            document.getElementById("playingTitle").innerText = title;
            let u = link.includes(".m3u8") ? BRADMAX + encodeURIComponent(link) : link;
            document.getElementById("videoContainer").innerHTML = `<iframe src="${{u}}&autoplay=true" width="100%" height="100%" frameborder="0" allowfullscreen></iframe>`;
        }}

        function closePlayer() {{
            document.getElementById("playerView").style.display = "none";
            document.getElementById("videoContainer").innerHTML = "";
        }}

        function goBack() {{
            document.getElementById("episodeGrid").classList.add("hidden");
            document.getElementById("mainGrid").classList.remove("hidden");
        }}

        function search() {{
            let q = document.getElementById("searchInput").value.toLowerCase();
            document.querySelectorAll(".card").forEach(c => {{
                c.style.display = c.innerText.toLowerCase().includes(q) ? "" : "none";
            }});
        }}
        init();
    </script>
</body>
</html>'''

    with open(file_name, "w", encoding="utf-8") as f:
        f.write(html_template)
    commit_and_push(file_name)

if __name__ == "__main__":
    run_scraper()

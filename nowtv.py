import cloudscraper
from bs4 import BeautifulSoup
import json
import time
import re
import subprocess
import os

# --- AYARLAR ---
JSON_SOURCE_URL = "https://raw.githubusercontent.com/mehmetey03/metvvd/refs/heads/main/nowtv_data.json"
BASE_URL = "https://www.nowtv.com.tr"
BRADMAX_PLAYER = "https://bradmax.com/client/embed-player/d9decbf0d308f4bb91825c3f3a2beb7b0aaee2f6_8493?mediaUrl="

def get_now_m3u8(scraper, bolum_url):
    try:
        time.sleep(0.4)
        r = scraper.get(bolum_url, timeout=10)
        # Regex: Daha geniş kapsamlı m3u8 arama
        m3u8_match = re.search(r'["\'](https?://[^\s"\']+\.m3u8[^\s"\']*)["\']', r.text)
        if m3u8_match:
            return m3u8_match.group(1).replace('\\/', '/')
        return bolum_url
    except:
        return bolum_url

def commit_and_push(file_name):
    print(f"\n📤 {file_name} GitHub'a gönderiliyor...")
    try:
        subprocess.run(["git", "config", "--global", "user.name", "github-actions[bot]"], check=True)
        subprocess.run(["git", "config", "--global", "user.email", "github-actions[bot]@users.noreply.github.com"], check=True)
        subprocess.run(["git", "add", "."], check=True)
        
        # Değişiklik kontrolü
        status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout
        if not status:
            print("ℹ️ Değişiklik yok, gönderim atlanıyor.")
            return

        subprocess.run(["git", "commit", "-m", "🔄 NOW TV VOD: Veri Güncellendi"], check=True)
        # Push hatasını önlemek için pull yapalım veya force kullanalım (dikkatli olunmalı)
        subprocess.run(["git", "push"], check=True)
        print("🚀 GitHub'a başarıyla yüklendi!")
    except Exception as e:
        print(f"❌ Git Hatası (Muhtemelen yetki veya çakışma): {e}")

def run_scraper():
    print("🚀 Bot Başlatıldı. Kaynak JSON okunuyor...")
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
    
    try:
        source_resp = scraper.get(JSON_SOURCE_URL)
        target_series = json.loads(source_resp.text)
        print(f"📦 Toplam {len(target_series)} dizi kaynakta bulundu.")
    except Exception as e:
        print(f"❌ JSON ana kaynak okuma hatası: {e}")
        return

    memory_data = {}

    for dizi_key, info in target_series.items():
        title = info.get('isim', 'Bilinmeyen Dizi')
        dizi_url = info.get('link', '')
        poster = info.get('resim', '')
        
        if not dizi_url: continue

        bolumler_url = dizi_url.split('/izle')[0].rstrip('/') + "/bolumler"
        print(f"\n📺 {title} taranıyor...")
        
        try:
            b_resp = scraper.get(bolumler_url, timeout=15)
            b_soup = BeautifulSoup(b_resp.text, 'html.parser')
            
            eps = []
            # HTML'deki dropdown menüyü yakala
            select_box = b_soup.find('select', id='video-finder-changer')
            
            if select_box:
                options = select_box.find_all('option', {'data-target': True})
                for opt in options:
                    b_url = opt['data-target']
                    b_title = opt.get_text(strip=True)
                    
                    # Video linkini çek
                    video_link = get_now_m3u8(scraper, b_url)
                    eps.append({"ad": b_title, "link": video_link})
                
                print(f"✅ {len(eps)} bölüm eklendi.")
            
            # Eğer veri bulunduysa hafızaya yaz
            if eps:
                memory_data[dizi_key] = {
                    "isim": title,
                    "resim": poster,
                    "bolumler": eps
                }
            else:
                print(f"⚠️ {title} için bölüm bulunamadı.")

        except Exception as e:
            print(f"⚠️ {title} işlenirken hata: {e}")

    # Veri gerçekten toplandı mı kontrol et
    if memory_data:
        print(f"\n📊 Toplam {len(memory_data)} dizi başarıyla işlendi. HTML oluşturuluyor...")
        create_html(memory_data)
    else:
        print("❌ HATA: Hiçbir veri toplanamadı, HTML oluşturulmayacak.")

def create_html(series_data):
    file_name = "nowtv_vod.html"
    # JSON verisini JS içinde güvenle kullanmak için
    json_str = json.dumps(series_data, ensure_ascii=False).replace("'", "\\'")
    
    html_template = f'''<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>METV NOW VOD</title>
    <style>
        body {{ margin: 0; background: #080808; color: #fff; font-family: sans-serif; }}
        .navbar {{ background: #000; padding: 15px; border-bottom: 2px solid #f50057; display: flex; justify-content: space-between; align-items: center; position: sticky; top:0; z-index:99; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 15px; padding: 20px; }}
        .card {{ background: #111; border-radius: 8px; overflow: hidden; cursor: pointer; border: 1px solid #222; transition: 0.2s; }}
        .card:hover {{ border-color: #f50057; transform: scale(1.03); }}
        .card img {{ width: 100%; aspect-ratio: 2/3; object-fit: cover; display: block; }}
        .card-name {{ padding: 8px; text-align: center; font-size: 12px; font-weight: bold; }}
        .player-view {{ position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: #000; z-index: 1000; display: none; }}
        .btn {{ background: #f50057; color: #fff; border: none; padding: 8px 15px; border-radius: 4px; cursor: pointer; }}
        .hidden {{ display: none !important; }}
        input {{ padding: 8px; border-radius: 20px; border: none; width: 150px; outline: none; }}
    </style>
</head>
<body>
    <div class="navbar">
        <b style="color:#f50057">METV NOW</b>
        <input type="text" id="search" placeholder="Ara..." oninput="doSearch()">
    </div>
    <div id="mainGrid" class="grid"></div>
    <div id="episodeGrid" class="grid hidden"></div>
    <div id="playerView" class="player-view">
        <div style="padding:10px; display:flex; justify-content:space-between;">
            <button class="btn" onclick="closePlayer()">KAPAT</button>
            <span id="pTitle"></span>
        </div>
        <div id="vContainer" style="height:calc(100% - 60px)"></div>
    </div>
    <script>
        const data = JSON.parse('{json_str}');
        const BRAD = "{BRADMAX_PLAYER}";
        
        function init() {{
            const g = document.getElementById("mainGrid");
            Object.keys(data).forEach(k => {{
                const item = data[k];
                const div = document.createElement("div");
                div.className = "card";
                div.innerHTML = `<img src="${{item.resim}}"><div class="card-name">${{item.isim}}</div>`;
                div.onclick = () => showEps(k);
                g.appendChild(div);
            }});
        }}
        
        function showEps(k) {{
            const eg = document.getElementById("episodeGrid");
            const mg = document.getElementById("mainGrid");
            mg.classList.add("hidden");
            eg.classList.remove("hidden");
            eg.innerHTML = `<div style="grid-column:1/-1"><button class="btn" onclick="location.reload()">Geri</button> <h3>${{data[k].isim}}</h3></div>`;
            data[k].bolumler.forEach(e => {{
                const div = document.createElement("div");
                div.className = "card";
                div.innerHTML = `<img src="${{data[k].resim}}" style="aspect-ratio:16/9"><div class="card-name">${{e.ad}}</div>`;
                div.onclick = () => play(e.link, e.ad);
                eg.appendChild(div);
            }});
        }}
        
        function play(l, t) {{
            document.getElementById("playerView").style.display = "block";
            document.getElementById("pTitle").innerText = t;
            const src = l.includes(".m3u8") ? BRAD + encodeURIComponent(l) : l;
            document.getElementById("vContainer").innerHTML = `<iframe src="${{src}}&autoplay=true" width="100%" height="100%" frameborder="0" allowfullscreen></iframe>`;
        }}
        
        function closePlayer() {{
            document.getElementById("playerView").style.display = "none";
            document.getElementById("vContainer").innerHTML = "";
        }}

        function doSearch() {{
            let q = document.getElementById("search").value.toLowerCase();
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

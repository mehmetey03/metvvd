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

def commit_and_push(file_name):
    print(f"\n📤 {file_name} GitHub'a gönderiliyor...")
    try:
        subprocess.run(["git", "config", "--global", "user.name", "github-actions[bot]"], check=True)
        subprocess.run(["git", "config", "--global", "user.email", "github-actions[bot]@users.noreply.github.com"], check=True)
        subprocess.run(["git", "add", "."], check=True)
        status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout
        if status:
            subprocess.run(["git", "commit", "-m", "🔄 NOW TV VOD: Hızlı Güncelleme"], check=True)
            subprocess.run(["git", "push"], check=True)
            print("🚀 GitHub'a başarıyla yüklendi!")
        else:
            print("ℹ️ Değişiklik yok.")
    except Exception as e:
        print(f"❌ Git Hatası: {e}")

def run_scraper():
    print("🚀 Bot Başlatıldı...")
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
    
    try:
        source_resp = scraper.get(JSON_SOURCE_URL, timeout=10)
        target_series = json.loads(source_resp.text)
    except Exception as e:
        print(f"❌ Kaynak JSON okunamadı: {e}")
        return

    memory_data = {}

    for dizi_key, info in target_series.items():
        title = info.get('isim', 'Dizi')
        dizi_url = info.get('link', '')
        poster = info.get('resim', '')
        
        # /izle -> /bolumler dönüşümü
        bolumler_url = dizi_url.split('/izle')[0].rstrip('/') + "/bolumler"
        print(f"🔍 {title} taranıyor...", end=" ", flush=True)
        
        try:
            b_resp = scraper.get(bolumler_url, timeout=10)
            b_soup = BeautifulSoup(b_resp.text, 'html.parser')
            
            eps = []
            # Dropdown menüsünü bul
            select_box = b_soup.find('select', id='video-finder-changer')
            
            if select_box:
                options = select_box.find_all('option', {'data-target': True})
                for opt in options:
                    # HIZ İÇİN: M3U8 linkini burada çekmiyoruz, HTML içinde direkt sayfa linkini kullanıyoruz
                    # Bradmax zaten sayfa içindeki videoyu otomatik yakalayabiliyor
                    eps.append({
                        "ad": opt.get_text(strip=True),
                        "link": opt['data-target'] 
                    })
                print(f"✅ {len(eps)} bölüm.")
            else:
                print("❌ Bölüm listesi bulunamadı.")

            if eps:
                memory_data[dizi_key] = {"isim": title, "resim": poster, "bolumler": eps}

        except Exception as e:
            print(f"⚠️ Hata: {e}")

    if memory_data:
        create_html(memory_data)
    else:
        print("❌ Hiç veri toplanamadı!")

def create_html(series_data):
    file_name = "nowtv_vod.html"
    # JSON verisindeki tırnak sorunlarını kökten çözelim
    clean_json = json.dumps(series_data, ensure_ascii=False).replace('"', '\\"').replace("'", "\\'")
    
    html_template = f'''<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>METV NOW VOD</title>
    <style>
        body {{ margin: 0; background: #0a0a0a; color: #fff; font-family: sans-serif; }}
        .navbar {{ background: #000; padding: 15px; border-bottom: 2px solid #f50057; display: flex; justify-content: space-between; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 15px; padding: 20px; }}
        .card {{ background: #111; border-radius: 8px; overflow: hidden; cursor: pointer; border: 1px solid #222; text-align: center; }}
        .card:hover {{ border-color: #f50057; transform: translateY(-5px); }}
        .card img {{ width: 100%; aspect-ratio: 2/3; object-fit: cover; }}
        .card-name {{ padding: 10px; font-size: 12px; font-weight: bold; }}
        #player {{ position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: #000; display: none; z-index: 999; }}
        .btn {{ background: #f50057; color: #fff; border: none; padding: 10px; cursor: pointer; border-radius: 5px; }}
        .hidden {{ display: none; }}
    </style>
</head>
<body>
    <div class="navbar"><b>METV NOW VOD</b> <input type="text" id="srch" placeholder="Ara..." oninput="search()"></div>
    <div id="mGrid" class="grid"></div>
    <div id="eGrid" class="grid hidden"></div>
    <div id="player">
        <div style="padding:10px;"><button class="btn" onclick="closeP()">KAPAT</button></div>
        <iframe id="ifr" width="100%" height="90%" frameborder="0" allowfullscreen></iframe>
    </div>

    <script>
        const series = JSON.parse('{clean_json}');
        const BRAD = "{BRADMAX_PLAYER}";

        function init() {{
            const g = document.getElementById("mGrid");
            Object.keys(series).forEach(k => {{
                const d = series[k];
                const c = document.createElement("div");
                c.className = "card";
                c.innerHTML = `<img src="${{d.resim}}"><div class="card-name">${{d.isim}}</div>`;
                c.onclick = () => showEps(k);
                g.appendChild(c);
            }});
        }}

        function showEps(k) {{
            const eg = document.getElementById("eGrid");
            document.getElementById("mGrid").classList.add("hidden");
            eg.classList.remove("hidden");
            eg.innerHTML = `<div style="grid-column:1/-1"><button class="btn" onclick="location.reload()">← GERİ</button> <h2>${{series[k].isim}}</h2></div>`;
            series[k].bolumler.forEach(e => {{
                const c = document.createElement("div");
                c.className = "card";
                c.innerHTML = `<img src="${{series[k].resim}}" style="aspect-ratio:16/9"><div class="card-name">${{e.ad}}</div>`;
                c.onclick = () => play(e.link);
                eg.appendChild(c);
            }});
        }}

        function play(url) {{
            document.getElementById("player").style.display = "block";
            // Bradmax artık linki otomatik çözebilir, çözemezse URL'i direkt açar
            document.getElementById("ifr").src = BRAD + encodeURIComponent(url);
        }}

        function closeP() {{
            document.getElementById("player").style.display = "none";
            document.getElementById("ifr").src = "";
        }}

        function search() {{
            let q = document.getElementById("srch").value.toLowerCase();
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

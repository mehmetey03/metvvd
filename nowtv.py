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

def commit_and_push(file_name):
    print(f"\n📤 {file_name} GitHub'a gönderiliyor...")
    try:
        # Git Ayarları
        subprocess.run(["git", "config", "--global", "user.name", "github-actions[bot]"], check=True)
        subprocess.run(["git", "config", "--global", "user.email", "github-actions[bot]@users.noreply.github.com"], check=True)
        
        # Değişiklikleri ekle
        subprocess.run(["git", "add", "."], check=True)
        
        # Değişiklik var mı kontrol et
        status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout
        if not status:
            print("ℹ️ Hiçbir değişiklik yok, push atlanıyor.")
            return

        # Commit ve Push (Force push kullanarak hataları bypass ediyoruz)
        subprocess.run(["git", "commit", "-m", "🔄 NOW TV VOD: M3U8 & Auto-Update"], check=True)
        # Mevcut branch ismini otomatik bul ve zorla pushla
        subprocess.run(["git", "push", "--force"], check=True)
        print("🚀 GitHub'a başarıyla yüklendi!")
    except Exception as e:
        print(f"❌ Git Hatası (Muhtemelen yetki sorunu): {e}")
        print("💡 İpucu: GitHub Repo Ayarları > Actions > General > 'Workflow permissions' kısmını 'Read and write' yapmalısın.")

def run_scraper():
    print("🚀 Bot Başlatıldı. Toplu M3U8 taraması yapılıyor...")
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
    
    try:
        source_resp = scraper.get(JSON_SOURCE_URL, timeout=10)
        target_series = json.loads(source_resp.text)
    except Exception as e:
        print(f"❌ Kaynak JSON hatası: {e}")
        return

    memory_data = {}

    for dizi_key, info in target_series.items():
        title = info.get('isim', 'Dizi')
        dizi_url = info.get('link', '')
        poster = info.get('resim', '')
        
        bolumler_url = dizi_url.split('/izle')[0].rstrip('/') + "/bolumler"
        print(f"🔍 {title} taranıyor...", end=" ", flush=True)
        
        try:
            response = scraper.get(bolumler_url, timeout=10)
            # Sayfa içindeki tüm m3u8 linklerini regex ile süpür
            all_m3u8s = re.findall(r'https?://[^\s"\'\\,]+\.m3u8[^\s"\'\\,]*', response.text)
            all_m3u8s = [m.replace('\\/', '/') for m in all_m3u8s]
            unique_m3u8s = list(dict.fromkeys(all_m3u8s))

            b_soup = BeautifulSoup(response.text, 'html.parser')
            eps = []
            
            select_box = b_soup.find('select', id='video-finder-changer')
            if select_box:
                options = select_box.find_all('option', {'data-target': True})
                for i, opt in enumerate(options):
                    b_title = opt.get_text(strip=True)
                    # M3U8 linkini sırayla eşleştir (Eğer m3u8 yoksa sayfa linkini kullan)
                    m3u8_link = unique_m3u8s[i] if i < len(unique_m3u8s) else opt['data-target']
                    eps.append({"ad": b_title, "link": m3u8_link})
                
                print(f"✅ {len(eps)} bölüm yakalandı.")

            if eps:
                memory_data[dizi_key] = {"isim": title, "resim": poster, "bolumler": eps}

        except Exception as e:
            print(f"⚠️ Hata: {e}")

    if memory_data:
        create_html(memory_data)
    else:
        print("❌ Veri bulunamadı.")

def create_html(series_data):
    file_name = "nowtv_vod.html"
    # JS tarafında hata vermemesi için tırnakları ve özel karakterleri güvenli hale getiriyoruz
    json_safe = json.dumps(series_data, ensure_ascii=False).replace("'", "\\'")
    
    html_template = f'''<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>METV NOW VOD</title>
    <style>
        body {{ margin: 0; background: #080808; color: #fff; font-family: sans-serif; }}
        .nav {{ background: #000; padding: 15px; border-bottom: 2px solid #f50057; display: flex; justify-content: space-between; position: sticky; top:0; z-index:99; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 15px; padding: 20px; }}
        .card {{ background: #111; border-radius: 8px; overflow: hidden; cursor: pointer; border: 1px solid #222; }}
        .card:hover {{ border-color: #f50057; transform: translateY(-3px); }}
        .card img {{ width: 100%; aspect-ratio: 2/3; object-fit: cover; }}
        .card-name {{ padding: 8px; text-align: center; font-size: 11px; font-weight: bold; }}
        #player {{ position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: #000; display: none; z-index: 1000; }}
        .btn {{ background: #f50057; color: #fff; border: none; padding: 10px; cursor: pointer; border-radius: 5px; }}
        .hidden {{ display: none; }}
        input {{ padding: 8px; border-radius: 20px; border: none; outline: none; }}
    </style>
</head>
<body>
    <div class="nav"><b>METV NOW</b> <input type="text" id="sr" placeholder="Ara..." oninput="sh()"></div>
    <div id="mG" class="grid"></div>
    <div id="eG" class="grid hidden"></div>
    <div id="player">
        <div style="padding:10px; background:#000;"><button class="btn" onclick="cls()">KAPAT</button> <span id="curT" style="margin-left:15px; color:#f50057"></span></div>
        <div id="vC" style="height:calc(100% - 60px)"></div>
    </div>
    <script>
        const series = JSON.parse('{json_safe}');
        const BRAD = "{BRADMAX_PLAYER}";

        function init() {{
            const g = document.getElementById("mG");
            Object.keys(series).forEach(k => {{
                const d = series[k];
                const c = document.createElement("div");
                c.className = "card";
                c.innerHTML = `<img src="${{d.resim}}"><div class="card-name">${{d.isim}}</div>`;
                c.onclick = () => show(k);
                g.appendChild(c);
            }});
        }}

        function show(k) {{
            const eg = document.getElementById("eG");
            document.getElementById("mG").classList.add("hidden");
            eg.classList.remove("hidden");
            eg.innerHTML = `<div style="grid-column:1/-1"><button class="btn" onclick="location.reload()">← GERİ</button> <h3 style="display:inline; margin-left:10px;">${{series[k].isim}}</h3></div>`;
            series[k].bolumler.forEach(e => {{
                const c = document.createElement("div");
                c.className = "card";
                c.innerHTML = `<img src="${{series[k].resim}}" style="aspect-ratio:16/9; object-fit:cover;"><div class="card-name">${{e.ad}}</div>`;
                c.onclick = () => play(e.link, e.ad);
                eg.appendChild(c);
            }});
        }}

        function play(l, name) {{
            document.getElementById("player").style.display = "block";
            document.getElementById("curT").innerText = name;
            let src = l.includes(".m3u8") ? BRAD + encodeURIComponent(l) : l;
            document.getElementById("vC").innerHTML = `<iframe src="${{src}}&autoplay=true" width="100%" height="100%" frameborder="0" allowfullscreen></iframe>`;
        }}

        function cls() {{
            document.getElementById("player").style.display = "none";
            document.getElementById("vC").innerHTML = "";
        }}
        
        function sh() {{
            let q = document.getElementById("sr").value.toLowerCase();
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

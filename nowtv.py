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

def get_now_m3u8(scraper, bolum_url):
    """Bölüm sayfasındaki gerçek m3u8 linkini regex ile yakalar."""
    try:
        # Hız için ufak bir bekleme
        time.sleep(0.3)
        r = scraper.get(bolum_url, timeout=7)
        # m3u8 linkini arayan kapsamlı regex
        match = re.search(r'(https?://[^\s"\']+\.m3u8[^\s"\']*)', r.text)
        if match:
            # Kaçış karakterlerini temizle (\/ -> /)
            return match.group(0).replace('\\/', '/')
        return bolum_url # Bulamazsa sayfa linkini döner
    except:
        return bolum_url

def commit_and_push(file_name):
    print(f"\n📤 {file_name} GitHub'a gönderiliyor...")
    try:
        subprocess.run(["git", "config", "--global", "user.name", "github-actions[bot]"], check=True)
        subprocess.run(["git", "config", "--global", "user.email", "github-actions[bot]@users.noreply.github.com"], check=True)
        subprocess.run(["git", "add", "."], check=True)
        status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout
        if status:
            subprocess.run(["git", "commit", "-m", "🔄 NOW TV VOD: M3U8 Links Updated"], check=True)
            subprocess.run(["git", "push"], check=True)
            print("🚀 GitHub'a başarıyla yüklendi!")
    except Exception as e:
        print(f"❌ Git Hatası: {e}")

def run_scraper():
    print("🚀 Bot Başlatıldı. M3U8 taraması yapılıyor...")
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
    
    try:
        source_resp = scraper.get(JSON_SOURCE_URL)
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
        print(f"\n📺 {title} taranıyor...")
        
        try:
            b_resp = scraper.get(bolumler_url, timeout=10)
            b_soup = BeautifulSoup(b_resp.text, 'html.parser')
            
            eps = []
            select_box = b_soup.find('select', id='video-finder-changer')
            
            if select_box:
                all_options = select_box.find_all('option', {'data-target': True})
                
                # PERFORMANS AYARI: 
                # Botun asılmamasını istiyorsan sadece son 20 bölümü çekebiliriz.
                # Hepsini istiyorsan '[:20]' kısmını silebilirsin ama işlem çok uzun sürer.
                target_options = all_options[:20] 
                
                print(f"   🔎 Toplam {len(all_options)} bölümden {len(target_options)} tanesi taranıyor...")
                
                for opt in target_options:
                    b_page_url = opt['data-target']
                    b_title = opt.get_text(strip=True)
                    
                    # Sayfa içine girip M3U8 linkini alıyoruz
                    m3u8_link = get_now_m3u8(scraper, b_page_url)
                    
                    eps.append({
                        "ad": b_title,
                        "link": m3u8_link
                    })
                    print(f"   ✅ {b_title} linki alındı.")

            if eps:
                memory_data[dizi_key] = {"isim": title, "resim": poster, "bolumler": eps}

        except Exception as e:
            print(f"⚠️ {title} hatası: {e}")

    if memory_data:
        create_html(memory_data)
    else:
        print("❌ Veri toplanamadı.")

def create_html(series_data):
    file_name = "nowtv_vod.html"
    json_str = json.dumps(series_data, ensure_ascii=False).replace('"', '\\"').replace("'", "\\'")
    
    html_template = f'''<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <title>METV NOW VOD</title>
    <style>
        body {{ margin: 0; background: #080808; color: #fff; font-family: sans-serif; }}
        .navbar {{ background: #000; padding: 15px; border-bottom: 2px solid #f50057; display: flex; justify-content: space-between; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 15px; padding: 20px; }}
        .card {{ background: #111; border-radius: 8px; overflow: hidden; cursor: pointer; border: 1px solid #222; }}
        .card:hover {{ border-color: #f50057; }}
        .card img {{ width: 100%; aspect-ratio: 2/3; object-fit: cover; }}
        .card-name {{ padding: 8px; text-align: center; font-size: 12px; }}
        #player {{ position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: #000; display: none; z-index: 999; }}
        .btn {{ background: #f50057; color: #fff; border: none; padding: 10px; cursor: pointer; border-radius: 5px; }}
        .hidden {{ display: none; }}
    </style>
</head>
<body>
    <div class="navbar"><b>METV NOW</b> <input type="text" id="sr" placeholder="Ara..." oninput="sh()"></div>
    <div id="mG" class="grid"></div>
    <div id="eG" class="grid hidden"></div>
    <div id="player">
        <div style="padding:10px;"><button class="btn" onclick="cls()">KAPAT</button></div>
        <div id="vC" style="height:90%"></div>
    </div>
    <script>
        const data = JSON.parse('{json_str}');
        const BRAD = "{BRADMAX_PLAYER}";

        function init() {{
            const g = document.getElementById("mG");
            Object.keys(data).forEach(k => {{
                const d = data[k];
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
            eg.innerHTML = `<div style="grid-column:1/-1"><button class="btn" onclick="location.reload()">← GERİ</button> <h3>${{data[k].isim}}</h3></div>`;
            data[k].bolumler.forEach(e => {{
                const c = document.createElement("div");
                c.className = "card";
                c.innerHTML = `<img src="${{data[k].resim}}" style="aspect-ratio:16/9"><div class="card-name">${{e.ad}}</div>`;
                c.onclick = () => play(e.link);
                eg.appendChild(c);
            }});
        }}

        function play(l) {{
            document.getElementById("player").style.display = "block";
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

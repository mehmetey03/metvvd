import cloudscraper
from bs4 import BeautifulSoup
import json
import time
import re
import subprocess

# Ayarlar
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
        # Sayfaya gir ve M3U8 linkini ara
        r = scraper.get(bolum_url, timeout=10)
        m3u8_match = re.search(r'(https?://[^\s"\']+\.m3u8[^\s"\']*)', r.text)
        if m3u8_match:
            return m3u8_match.group(0).replace('\\/', '/')
        return bolum_url # Bulamazsa kendi linkini dön
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
            subprocess.run(["git", "commit", "-m", "🔄 NOW TV VOD updated with Owl-Stage Scraper"], check=True)
            subprocess.run(["git", "push"], check=True)
            print("🚀 GitHub'a başarıyla yüklendi!")
    except Exception as e:
        print(f"❌ Git Hatası: {e}")

def run_scraper():
    print("🚀 Bot Başlatıldı. Kaynak JSON ve Owl-Stage yapısı taranıyor...")
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
        
        # Linki bölümler sayfasına çevir (Örn: /izle -> /bolumler)
        bolumler_url = dizi_url.split('/izle')[0].rstrip('/') + "/bolumler"
        
        print(f"📺 {title} taranıyor: {bolumler_url}")
        
        try:
            resp = scraper.get(bolumler_url, timeout=15)
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # Paylaştığın yapıya göre: .owl-item içindeki a etiketlerini bul
            items = soup.select('.owl-item')
            if not items:
                # Alternatif: Owl-Stage yoksa standart list-item ara
                items = soup.select('.list-item, .video-card')

            eps = []
            for item in items:
                a_tag = item.find('a', href=True)
                name_tag = item.select_one('.program-name')
                
                if a_tag and "/bolum/" in a_tag['href']:
                    b_url = BASE_URL + a_tag['href'] if a_tag['href'].startswith('/') else a_tag['href']
                    b_title = name_tag.get_text(strip=True) if name_tag else "Bölüm"
                    
                    # Video linkini yakala
                    m3u8 = get_now_m3u8(scraper, b_url)
                    
                    # Aynı linki tekrar ekleme
                    if not any(e['link'] == m3u8 for e in eps):
                        eps.append({"ad": b_title, "link": m3u8})
                        print(f"   ✅ Yakalandı: {b_title}")

            if eps:
                # Bölümleri normal sıraya diz (Sitede genelde sondan başa gelir)
                memory_data[dizi_key] = {
                    "isim": title,
                    "resim": poster,
                    "bolumler": eps[::-1] 
                }
        except Exception as e:
            print(f"   ⚠️ {title} hatası: {e}")

    create_html(memory_data)

def create_html(series_data):
    file_name = "nowtv_vod.html"
    json_embedded = json.dumps(series_data, ensure_ascii=False)
    
    # Senin istediğin METV tarzı mor-siyah modern arayüz
    html_template = f'''<!DOCTYPE html>
<html lang="tr">
<head>
    <title>METV NOW VOD</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{ margin: 0; background: #0a0a0c; color: #fff; font-family: sans-serif; font-style: italic; }}
        .header {{ background: #15161a; padding: 15px 25px; border-bottom: 2px solid #572aa7; display: flex; justify-content: space-between; align-items: center; position: sticky; top: 0; z-index: 100; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 15px; padding: 20px; }}
        .card {{ background: #15161a; border: 1px solid #323442; border-radius: 8px; overflow: hidden; cursor: pointer; transition: 0.3s; position: relative; aspect-ratio: 2/3; }}
        .card:hover {{ border-color: #572aa7; transform: translateY(-5px); }}
        .card img {{ width: 100%; height: 100%; object-fit: cover; }}
        .card-info {{ position: absolute; bottom: 0; background: linear-gradient(transparent, black); width: 100%; padding: 8px; text-align: center; font-size: 12px; }}
        .player-overlay {{ position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: #000; z-index: 9999; display: none; }}
        .btn-back {{ background: #572aa7; color: #fff; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; margin: 10px; }}
        .hidden {{ display: none !important; }}
    </style>
</head>
<body>
    <div class="header">
        <div style="color: #572aa7; font-weight: bold; font-size: 20px;">METV NOW VOD</div>
        <input type="text" id="srch" placeholder="Ara..." oninput="search()" style="background:#000; color:#fff; border:1px solid #323442; padding:5px 15px; border-radius:20px;">
    </div>
    <div id="main_g" class="grid"></div>
    <div id="eps_g" class="grid hidden"></div>
    <div id="p_view" class="player-overlay">
        <button class="btn-back" onclick="closeP()">✕ KAPAT</button>
        <div id="v_area" style="height:calc(100% - 70px);"></div>
    </div>
    <script>
        const data = {json_embedded};
        const BRADMAX = "{BRADMAX_PLAYER}";
        function init() {{
            const g = document.getElementById("main_g");
            Object.keys(data).forEach(id => {{
                const d = data[id];
                const c = document.createElement("div");
                c.className = "card";
                c.innerHTML = `<img src="${{d.resim}}"><div class="card-info">${{d.isim.toUpperCase()}}</div>`;
                c.onclick = () => showE(id);
                g.appendChild(c);
            }});
        }}
        function showE(id) {{
            document.getElementById("main_g").classList.add("hidden");
            const eg = document.getElementById("eps_g");
            eg.classList.remove("hidden");
            eg.innerHTML = `<div style="grid-column: 1/-1;"><button class="btn-back" onclick="goB()">← DİZİLER</button> <h3 style="display:inline">${{data[id].isim}}</h3></div>`;
            data[id].bolumler.forEach(e => {{
                const c = document.createElement("div");
                c.className = "card";
                c.innerHTML = `<img src="${{data[id].resim}}"><div class="card-info">${{e.ad}}</div>`;
                c.onclick = () => play(e.link);
                eg.appendChild(c);
            }});
        }}
        function play(l) {{
            document.getElementById("p_view").style.display = "block";
            let u = l.includes(".m3u8") ? BRADMAX + encodeURIComponent(l) : l;
            document.getElementById("v_area").innerHTML = `<iframe src="${{u}}&autoplay=true" width="100%" height="100%" frameborder="0" allowfullscreen></iframe>`;
        }}
        function closeP() {{ document.getElementById("p_view").style.display="none"; document.getElementById("v_area").innerHTML=""; }}
        function goB() {{ document.getElementById("eps_g").classList.add("hidden"); document.getElementById("main_g").classList.remove("hidden"); }}
        function search() {{
            let v = document.getElementById("srch").value.toLowerCase();
            document.querySelectorAll(".card").forEach(c => c.style.display = c.innerText.toLowerCase().includes(v) ? "" : "none");
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

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
    """Bölüm sayfasındaki asıl m3u8 linkini bulur"""
    try:
        # Engellenmemek için çok kısa bekleme
        time.sleep(0.1)
        r = scraper.get(bolum_url, timeout=10)
        # Geniş kapsamlı M3U8 arama
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
            subprocess.run(["git", "commit", "-m", "🔄 NOW TV VOD: Tüm Bölümler Güncellendi"], check=True)
            subprocess.run(["git", "push"], check=True)
            print("🚀 GitHub'a başarıyla yüklendi!")
        else:
            print("✨ Değişiklik yok, push atılmadı.")
    except Exception as e:
        print(f"❌ Git Hatası: {e}")

def run_scraper():
    print("🚀 Bot Başlatıldı. Tüm bölümler taranıyor...")
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
    
    try:
        # GitHub'dan dizi listesini al
        source_resp = scraper.get(JSON_SOURCE_URL)
        target_series = json.loads(source_resp.text)
    except Exception as e:
        print(f"❌ Kaynak JSON hatası: {e}")
        return

    memory_data = {}

    for dizi_id, info in target_series.items():
        title = info['isim']
        # /izle kısmını /bolumler yaparak tüm arşivi hedefle
        bolumler_url = info['link'].split('/izle')[0].rstrip('/') + "/bolumler"
        
        print(f"📺 {title} taranıyor...")
        
        try:
            resp = scraper.get(bolumler_url, timeout=15)
            # Regex ile sayfa içindeki TÜM bölüm linklerini (/bolum/123 gibi) topla
            # Sadece slider (owl-item) değil, tüm HTML kaynağını tarar
            raw_links = re.findall(r'href=["\']([^"\']+/bolum/\d+)["\']', resp.text)
            
            # Tekrar eden linkleri temizle
            unique_links = list(dict.fromkeys(raw_links))
            
            eps = []
            for link in unique_links:
                full_b_url = BASE_URL + link if link.startswith('/') else link
                
                # Bölüm adını linkten tahmin et (Örn: /bolum/45 -> 45. Bölüm)
                b_number = link.split('/')[-1]
                b_name = f"{b_number}. Bölüm"
                
                # Video linkini çek
                m3u8 = get_now_m3u8(scraper, full_b_url)
                
                eps.append({"ad": b_name, "link": m3u8})
            
            # Bölümleri sayısal olarak sırala (1, 2, 3...)
            eps.sort(key=lambda x: int(re.search(r'\d+', x['ad']).group()) if re.search(r'\d+', x['ad']) else 0)

            if eps:
                memory_data[dizi_id] = {
                    "isim": title,
                    "resim": info['resim'],
                    "bolumler": eps # Eskiden yeniye sıralı
                }
                print(f"   ✅ {len(eps)} bölüm başarıyla listelendi.")
            else:
                print(f"   ⚠️ Hiç bölüm bulunamadı!")

        except Exception as e:
            print(f"   ❌ {title} taranırken hata: {e}")

    create_html(memory_data)

def create_html(series_data):
    file_name = "nowtv_vod.html"
    json_embedded = json.dumps(series_data, ensure_ascii=False)
    
    html_template = f'''<!DOCTYPE html>
<html lang="tr">
<head>
    <title>METV NOW VOD</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{ margin: 0; background: #050505; color: white; font-family: 'Segoe UI', sans-serif; font-style: italic; }}
        .header {{ background: #111; padding: 15px 25px; border-bottom: 2px solid #572aa7; display: flex; justify-content: space-between; align-items: center; position: sticky; top: 0; z-index: 1000; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 15px; padding: 20px; }}
        .card {{ background: #111; border: 1px solid #222; border-radius: 10px; overflow: hidden; cursor: pointer; transition: 0.3s; position: relative; }}
        .card:hover {{ border-color: #572aa7; transform: translateY(-5px); box-shadow: 0 5px 15px rgba(87,42,167,0.3); }}
        .card img {{ width: 100%; aspect-ratio: 2/3; object-fit: cover; }}
        .card-txt {{ padding: 10px; text-align: center; font-size: 13px; font-weight: bold; background: linear-gradient(transparent, #000); position: absolute; bottom: 0; width: 100%; box-sizing: border-box; }}
        .player {{ position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: #000; z-index: 2000; display: none; }}
        .btn {{ background: #572aa7; color: white; border: none; padding: 10px 20px; cursor: pointer; border-radius: 5px; margin: 15px; font-weight: bold; }}
        .hidden {{ display: none !important; }}
    </style>
</head>
<body>
    <div class="header">
        <div style="color:#572aa7; font-size:22px; font-weight:bold;">METV NOW VOD</div>
        <input type="text" id="srch" placeholder="Ara..." oninput="doSearch()" style="background:#000; color:#fff; border:1px solid #333; padding:8px 15px; border-radius:20px; outline:none;">
    </div>
    
    <div id="m-grid" class="grid"></div>
    <div id="e-grid" class="grid hidden"></div>
    
    <div id="p-view" class="player">
        <button class="btn" onclick="closeP()">✕ KAPAT</button>
        <div id="v-frame" style="height: calc(100% - 80px);"></div>
    </div>

    <script>
        const data = {json_embedded};
        const PLAYER_URL = "{BRADMAX_PLAYER}";

        function init() {{
            const mg = document.getElementById("m-grid");
            Object.keys(data).forEach(id => {{
                const d = data[id];
                const c = document.createElement("div");
                c.className = "card";
                c.innerHTML = `<img src="${{d.resim}}"><div class="card-txt">${{d.isim.toUpperCase()}}</div>`;
                c.onclick = () => showE(id);
                mg.appendChild(c);
            }});
        }}

        function showE(id) {{
            window.scrollTo(0,0);
            document.getElementById("m-grid").classList.add("hidden");
            const eg = document.getElementById("e-grid");
            eg.classList.remove("hidden");
            eg.innerHTML = `<div style="grid-column:1/-1;"><button class="btn" onclick="back()">← DİZİLER</button><h2 style="display:inline;margin-left:15px;">${{data[id].isim}}</h2></div>`;
            
            data[id].bolumler.forEach(ep => {{
                const c = document.createElement("div");
                c.className = "card";
                c.innerHTML = `<img src="${{data[id].resim}}"><div class="card-txt">${{ep.ad}}</div>`;
                c.onclick = () => play(ep.link);
                eg.appendChild(c);
            }});
        }}

        function play(link) {{
            document.getElementById("p-view").style.display = "block";
            let final = link.includes(".m3u8") ? PLAYER_URL + encodeURIComponent(link) : link;
            document.getElementById("v-frame").innerHTML = `<iframe src="${{final}}&autoplay=true" width="100%" height="100%" frameborder="0" allowfullscreen></iframe>`;
        }}

        function closeP() {{ document.getElementById("p-view").style.display="none"; document.getElementById("v-frame").innerHTML=""; }}
        function back() {{ document.getElementById("e-grid").classList.add("hidden"); document.getElementById("m-grid").classList.remove("hidden"); }}
        function doSearch() {{
            let q = document.getElementById("srch").value.toLowerCase();
            document.querySelectorAll(".card").forEach(c => c.style.display = c.innerText.toLowerCase().includes(q) ? "" : "none");
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

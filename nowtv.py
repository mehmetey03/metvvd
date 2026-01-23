import cloudscraper
from bs4 import BeautifulSoup
import json
import time
import re
import subprocess

# Ayarlar
BASE_URL = "https://www.nowtv.com.tr"
ARCHIVE_URL = "https://www.nowtv.com.tr/dizi-arsivi"
BRADMAX_PLAYER = "https://bradmax.com/client/embed-player/d9decbf0d308f4bb91825c3f3a2beb7b0aaee2f6_8493?mediaUrl="

def slugify(text):
    mapping = {'ç':'c','ğ':'g','ı':'i','ö':'o','ş':'s','ü':'u','İ':'i','I':'i'}
    text = text.lower()
    for tr, en in mapping.items(): text = text.replace(tr, en)
    return re.sub(r'[^a-z0-9]+', '-', text).strip('-')

def get_now_m3u8(scraper, bolum_url):
    try:
        time.sleep(0.3)
        r = scraper.get(bolum_url, timeout=10)
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
        
        # Sadece bu dosyada değişiklik varsa commit yap
        if subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout:
            subprocess.run(["git", "commit", "-m", "🔄 NOW TV VOD Güncellendi"], check=True)
            subprocess.run(["git", "push"], check=True)
            print("🚀 GitHub'a yüklendi!")
    except Exception as e:
        print(f"❌ Git Hatası: {e}")

def run_scraper():
    print("🚀 NOW TV Scraper Başlatıldı (JSON dosyası kullanılmıyor)...")
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
    
    # Verileri geçici olarak bu sözlükte tutacağız
    memory_data = {}
    
    try:
        resp = scraper.get(ARCHIVE_URL, timeout=20)
        soup = BeautifulSoup(resp.text, 'html.parser')
        cards = soup.select('.list-item')

        for card in cards:
            link_tag = card.find('a', href=True)
            if not link_tag: continue
            
            href = link_tag['href']
            # Dizi ana sayfa kontrolü
            if "/izle" not in href and "/bolumler" not in href:
                if href.count('/') > 2: continue 

            title_tag = card.select_one('.program-name strong') or card.select_one('.program-name')
            if not title_tag: continue
            
            title = title_tag.get_text(strip=True)
            dizi_id = slugify(title)
            bolumler_url = (BASE_URL + href if href.startswith('/') else href).split('/izle')[0].rstrip('/') + "/bolumler"

            print(f"📺 {title} çekiliyor...")
            
            try:
                b_resp = scraper.get(bolumler_url, timeout=15)
                b_soup = BeautifulSoup(b_resp.text, 'html.parser')
                b_cards = b_soup.select('.list-item')
                
                eps = []
                for bc in b_cards:
                    b_link = bc.find('a', href=True)
                    if b_link and "/bolum/" in b_link['href']:
                        full_b_url = BASE_URL + b_link['href'] if b_link['href'].startswith('/') else b_link['href']
                        b_name_tag = bc.select_one('.program-name')
                        b_title = b_name_tag.get_text(strip=True) if b_name_tag else "Bölüm"
                        
                        m3u8 = get_now_m3u8(scraper, full_b_url)
                        if not any(e['link'] == m3u8 for e in eps):
                            eps.append({"ad": b_title, "link": m3u8})

                if eps:
                    img = card.find('img')
                    poster = img.get('data-src') or img.get('src', '')
                    if not poster.startswith('http'): poster = BASE_URL + poster
                    
                    # Veriyi hafızaya kaydet
                    memory_data[dizi_id] = {
                        "isim": title,
                        "resim": poster,
                        "bolumler": eps
                    }
                    print(f"  ✅ {len(eps)} bölüm eklendi.")
            except: continue

    except Exception as e:
        print(f"❌ Hata: {e}")

    # Çekilen veriyi doğrudan HTML oluşturma fonksiyonuna gönder
    create_html(memory_data)

def create_html(series_data):
    file_name = "nowtv_vod.html"
    # Python sözlüğünü JSON formatında bir stringe çevirip HTML içine gömüyoruz
    json_embedded = json.dumps(series_data, ensure_ascii=False)
    
    html_template = f'''<!DOCTYPE html>
<html lang="tr">
<head>
    <title>NOW TV ARŞİV</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://code.jquery.com/jquery-3.5.1.min.js"></script>
    <style>
        body {{ margin: 0; background: #000; color: #fff; font-family: sans-serif; }}
        .nav {{ background: #111; padding: 15px; border-bottom: 2px solid #ff0055; position: sticky; top: 0; z-index: 100; display: flex; justify-content: space-between; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 15px; padding: 20px; }}
        .card {{ background: #1a1a1a; border-radius: 8px; overflow: hidden; cursor: pointer; transition: 0.2s; border: 1px solid #333; }}
        .card:hover {{ border-color: #ff0055; transform: scale(1.03); }}
        .card img {{ width: 100%; aspect-ratio: 2/3; object-fit: cover; }}
        .card-txt {{ padding: 10px; font-size: 12px; text-align: center; }}
        .hidden {{ display: none !important; }}
        .player {{ position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: #000; z-index: 1000; display: none; }}
        .btn {{ background: #ff0055; color: white; border: none; padding: 10px 20px; cursor: pointer; border-radius: 5px; margin: 10px; }}
    </style>
</head>
<body>
    <div class="nav">
        <b style="color:#ff0055">NOW VOD</b>
        <input type="text" id="search" placeholder="Ara..." oninput="doSearch()" style="border-radius:5px; border:none; padding:5px;">
    </div>
    <div id="m-grid" class="grid"></div>
    <div id="e-grid" class="grid hidden"></div>
    <div id="p-view" class="player">
        <button class="btn" onclick="closeP()">✕ KAPAT</button>
        <div id="v-frame" style="height: calc(100% - 75px);"></div>
    </div>
    <script>
        // VERİLER BURAYA GÖMÜLÜDÜR
        const data = {json_embedded};
        const PLAYER = "{BRADMAX_PLAYER}";

        function init() {{
            const m = document.getElementById("m-grid");
            Object.keys(data).forEach(id => {{
                const c = document.createElement("div");
                c.className = "card";
                c.innerHTML = `<img src="${{data[id].resim}}"><div class="card-txt">${{data[id].isim}}</div>`;
                c.onclick = () => showE(id);
                m.appendChild(c);
            }});
        }}
        function showE(id) {{
            document.getElementById("m-grid").classList.add("hidden");
            const eg = document.getElementById("e-grid");
            eg.classList.remove("hidden");
            eg.innerHTML = `<div style="grid-column: 1/-1"><button class="btn" onclick="back()">← DÖN</button><h3>${{data[id].isim}}</h3></div>`;
            data[id].bolumler.forEach(ep => {{
                const c = document.createElement("div");
                c.className = "card";
                c.innerHTML = `<img src="${{data[id].resim}}"><div class="card-txt">${{ep.ad}}</div>`;
                c.onclick = () => play(ep.link);
                eg.appendChild(c);
            }});
        }}
        function play(l) {{
            document.getElementById("p-view").style.display = "block";
            let u = l.includes(".m3u8") ? PLAYER + encodeURIComponent(l) : l;
            document.getElementById("v-frame").innerHTML = `<iframe src="${{u}}&autoplay=true" width="100%" height="100%" frameborder="0" allowfullscreen></iframe>`;
        }}
        function closeP() {{ document.getElementById("p-view").style.display = "none"; document.getElementById("v-frame").innerHTML = ""; }}
        function back() {{ document.getElementById("e-grid").classList.add("hidden"); document.getElementById("m-grid").classList.remove("hidden"); }}
        function doSearch() {{
            let q = document.getElementById("search").value.toLowerCase();
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

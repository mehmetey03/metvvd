import cloudscraper
from bs4 import BeautifulSoup
import json
import time
import re
import subprocess

# Ayarlar
BASE_URL = "https://www.nowtv.com.tr"
# NowTV'nin tüm arşivi yüklemek için kullandığı AJAX servisi
API_URL = "https://www.nowtv.com.tr/api/v1/programs/archive?page="
BRADMAX_PLAYER = "https://bradmax.com/client/embed-player/d9decbf0d308f4bb91825c3f3a2beb7b0aaee2f6_8493?mediaUrl="

def slugify(text):
    mapping = {'ç':'c','ğ':'g','ı':'i','ö':'o','ş':'s','ü':'u','İ':'i','I':'i'}
    text = text.lower()
    for tr, en in mapping.items(): text = text.replace(tr, en)
    return re.sub(r'[^a-z0-9]+', '-', text).strip('-')

def get_now_m3u8(scraper, bolum_url):
    try:
        time.sleep(0.1) # Hız sınırına takılmamak için minik bekleme
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
        status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout
        if status:
            subprocess.run(["git", "commit", "-m", "🔄 TÜM ARŞİV GÜNCELLENDİ"], check=True)
            subprocess.run(["git", "push"], check=True)
            print("🚀 Başarıyla yüklendi!")
        else:
            print("✨ Değişiklik yok.")
    except Exception as e:
        print(f"❌ Git Hatası: {e}")

def run_scraper():
    print("🚀 NOW TV Tam Arşiv Scraper Başlatıldı...")
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
    series_data = {}
    
    # Sayfa sayfa tüm arşivi tara (Daha fazla butonunu simüle eder)
    for page in range(1, 10): # İlk 10 sayfayı tara (tüm arşivi kapsar)
        print(f"📂 Arşiv Sayfası {page} taranıyor...")
        try:
            resp = scraper.get(f"{API_URL}{page}", timeout=15)
            # Eğer API JSON dönüyorsa işle, dönmüyorsa (HTML ise) BS4 ile işle
            if "application/json" in resp.headers.get('Content-Type', ''):
                data = resp.json()
                html_content = data.get('html', '')
            else:
                html_content = resp.text

            soup = BeautifulSoup(html_content, 'html.parser')
            cards = soup.select('.list-item')
            
            if not cards: break # Artık kart gelmiyorsa döngüden çık

            for card in cards:
                link_tag = card.find('a', href=True)
                if not link_tag: continue
                
                title = card.select_one('.program-name').get_text(strip=True)
                if title in [s['isim'] for s in series_data.values()]: continue # Tekrarı önle
                
                dizi_id = slugify(title)
                href = link_tag['href']
                bolumler_url = (BASE_URL + href if href.startswith('/') else href).split('/izle')[0].rstrip('/') + "/bolumler"

                print(f"  📺 {title} çekiliyor...")
                
                try:
                    b_resp = scraper.get(bolumler_url, timeout=15)
                    b_soup = BeautifulSoup(b_resp.text, 'html.parser')
                    # Tüm bölümleri (sayfadaki tüm list-item'ları) al
                    b_cards = b_soup.find_all('div', class_=re.compile(r'list-item|video-card'))
                    
                    eps = []
                    for bc in b_cards:
                        b_link = bc.find('a', href=True)
                        if b_link and "/bolum/" in b_link['href']:
                            full_b_url = BASE_URL + b_link['href'] if b_link['href'].startswith('/') else b_link['href']
                            b_name_tag = bc.select_one('.program-name, .title, .video-title')
                            b_title = b_name_tag.get_text(strip=True) if b_name_tag else "Bölüm"
                            
                            m3u8 = get_now_m3u8(scraper, full_b_url)
                            eps.append({"ad": b_title, "link": m3u8})

                    if eps:
                        img = card.find('img')
                        poster = img.get('data-src') or img.get('src', '')
                        if not poster.startswith('http'): poster = BASE_URL + poster
                        
                        series_data[dizi_id] = {
                            "isim": title,
                            "resim": poster,
                            "bolumler": eps
                        }
                        print(f"    ✅ {len(eps)} bölüm eklendi.")
                except: continue
        except Exception as e:
            print(f"⚠️ Sayfa {page} hatası: {e}")
            break

    create_html(series_data)

def create_html(series_data):
    # (Önceki HTML şablonun aynısı, sadece JavaScript içindeki 'data' güncelleniyor)
    file_name = "nowtv_vod.html"
    json_embedded = json.dumps(series_data, ensure_ascii=False)
    
    html = f'''<!DOCTYPE html>
<html lang="tr">
<head>
    <title>NOW TV ARŞİV</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{ margin: 0; background: #050505; color: #eee; font-family: sans-serif; }}
        .nav {{ background: #111; padding: 15px; border-bottom: 3px solid #f50057; display: flex; justify-content: space-between; position: sticky; top: 0; z-index: 100; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 15px; padding: 15px; }}
        .card {{ background: #181818; border-radius: 8px; overflow: hidden; cursor: pointer; border: 1px solid #222; }}
        .card:hover {{ border-color: #f50057; }}
        .card img {{ width: 100%; aspect-ratio: 2/3; object-fit: cover; }}
        .card-txt {{ padding: 8px; font-size: 11px; text-align: center; }}
        .hidden {{ display: none !important; }}
        .player {{ position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: #000; z-index: 200; display: none; }}
        .btn {{ background: #f50057; color: #fff; border: none; padding: 10px; cursor: pointer; margin: 5px; border-radius: 4px; }}
    </style>
</head>
<body>
    <div class="nav">
        <b>NOW TV VOD</b>
        <input type="text" id="search" placeholder="Dizi ara..." oninput="doSearch()" style="padding:5px; border-radius:4px; border:none;">
    </div>
    <div id="m-grid" class="grid"></div>
    <div id="e-grid" class="grid hidden"></div>
    <div id="p-view" class="player">
        <button class="btn" onclick="closeP()">✕ KAPAT</button>
        <div id="v-frame" style="height: calc(100% - 60px);"></div>
    </div>
    <script>
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
            window.scrollTo(0,0);
            document.getElementById("m-grid").classList.add("hidden");
            const eg = document.getElementById("e-grid");
            eg.classList.remove("hidden");
            eg.innerHTML = `<div style="grid-column: 1/-1"><button class="btn" onclick="back()">← GERİ</button><h2>${{data[id].isim}}</h2></div>`;
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
        function back() {{ document.getElementById("e-grid").classList.add("hidden"); document.getElementById("m-grid").classList.remove("hidden"); }}
        function closeP() {{ document.getElementById("p-view").style.display = "none"; document.getElementById("v-frame").innerHTML = ""; }}
        function doSearch() {{
            let q = document.getElementById("search").value.toLowerCase();
            document.querySelectorAll("#m-grid .card").forEach(c => c.style.display = c.innerText.toLowerCase().includes(q) ? "" : "none");
        }}
        init();
    </script>
</body>
</html>'''

    with open(file_name, "w", encoding="utf-8") as f:
        f.write(html)
    commit_and_push(file_name)

if __name__ == "__main__":
    run_scraper()

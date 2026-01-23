import cloudscraper
from bs4 import BeautifulSoup
import json
import re
import subprocess
import time

# Ayarlar
BASE_URL = "https://www.nowtv.com.tr"
# Now TV'nin gizli arşiv API'si (Sadece sayfa numarasını değiştirerek her şeyi alabiliriz)
API_URL = "https://www.nowtv.com.tr/api/v1/programs/archive?page="
BRADMAX_PLAYER = "https://bradmax.com/client/embed-player/d9decbf0d308f4bb91825c3f3a2beb7b0aaee2f6_8493?mediaUrl="

def slugify(text):
    mapping = {'ç':'c','ğ':'g','ı':'i','ö':'o','ş':'s','ü':'u','İ':'i','I':'i'}
    text = text.lower()
    for tr, en in mapping.items(): text = text.replace(tr, en)
    return re.sub(r'[^a-z0-9]+', '-', text).strip('-')

def get_now_m3u8(scraper, bolum_url):
    try:
        r = scraper.get(bolum_url, timeout=10)
        m3u8_match = re.search(r'(https?://[^\s"\']+\.m3u8[^\s"\']*)', r.text)
        if m3u8_match:
            return m3u8_match.group(0).replace('\\/', '/')
        return bolum_url
    except:
        return bolum_url

def run_scraper():
    print("🚀 NOW TV Tam Arşiv Taraması Başladı...")
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
    series_data = {}
    
    # Sayfa 1'den başlayıp boş dönene kadar devam eder (Genelde 10-15 sayfa sürer)
    page = 1
    while True:
        print(f"📂 Sayfa {page} taranıyor...")
        try:
            # API'den HTML parçasını çekiyoruz
            resp = scraper.get(f"{API_URL}{page}", timeout=15)
            # API JSON dönüyor, içindeki 'html' anahtarını alıyoruz
            data_json = resp.json()
            html_chunk = data_json.get('html', '')
            
            if not html_chunk or "list-item" not in html_chunk:
                print("🏁 Tüm sayfalar tarandı, başka dizi kalmadı.")
                break
                
            soup = BeautifulSoup(html_chunk, 'html.parser')
            cards = soup.select('.list-item')
            
            for card in cards:
                link_tag = card.find('a', href=True)
                title_tag = card.find('strong') or card.find(class_='program-name')
                
                if not link_tag or not title_tag: continue
                
                title = title_tag.get_text(strip=True)
                href = link_tag['href']
                dizi_id = slugify(title)

                # Daha önce eklenmişse atla (Tekrarı önler)
                if dizi_id in series_data: continue

                print(f"  🎬 {title} çekiliyor...")
                bolumler_url = (BASE_URL + href if href.startswith('/') else href).replace('/izle', '/bolumler')
                
                try:
                    b_resp = scraper.get(bolumler_url, timeout=10)
                    b_soup = BeautifulSoup(b_resp.text, 'html.parser')
                    b_links = b_soup.find_all('a', href=re.compile(r'/bolum/'))
                    
                    eps = []
                    for b_link in b_links:
                        full_b_url = BASE_URL + b_link['href'] if b_link['href'].startswith('/') else b_link['href']
                        b_name = b_link.find_next(class_='program-name') or b_link.find_next('strong')
                        b_title = b_name.get_text(strip=True) if b_name else "Bölüm"
                        
                        m3u8 = get_now_m3u8(scraper, full_b_url)
                        eps.append({"ad": b_title, "link": m3u8})

                    if eps:
                        img = card.find('img')
                        poster = img.get('src') or img.get('data-src', '')
                        if poster and not poster.startswith('http'): poster = BASE_URL + poster
                        
                        series_data[dizi_id] = {
                            "isim": title,
                            "resim": poster,
                            "bolumler": eps
                        }
                        print(f"    ✅ {len(eps)} bölüm.")
                except: continue
            
            page += 1 # Bir sonraki sayfaya geç
            time.sleep(1) # Siteyi yormamak için kısa bekleme
            
        except Exception as e:
            print(f"⚠️ Sayfa {page} yüklenirken hata oluştu veya bitti: {e}")
            break

    if series_data:
        create_html(series_data)
    else:
        print("🚨 Veri bulunamadı!")

def create_html(series_data):
    # HTML oluşturma ve Git push işlemleri (Öncekiyle aynı)
    file_name = "nowtv_vod.html"
    json_embedded = json.dumps(series_data, ensure_ascii=False)
    
    html_content = f'''<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="utf-8">
    <title>NOW VOD FULL ARŞİV</title>
    <style>
        body {{ background:#050505; color:#eee; font-family:sans-serif; margin:0; }}
        .nav {{ background:#111; padding:15px; border-bottom:2px solid #f50057; position:sticky; top:0; display:flex; justify-content:space-between; }}
        .grid {{ display:grid; grid-template-columns:repeat(auto-fill, minmax(140px, 1fr)); gap:15px; padding:20px; }}
        .card {{ background:#181818; border-radius:8px; overflow:hidden; cursor:pointer; border:1px solid #222; transition:0.3s; }}
        .card:hover {{ border-color:#f50057; transform:scale(1.05); }}
        .card img {{ width:100%; aspect-ratio:2/3; object-fit:cover; }}
        .card-name {{ padding:8px; font-size:12px; text-align:center; }}
        .player {{ position:fixed; top:0; left:0; width:100%; height:100%; background:#000; display:none; z-index:999; }}
        .btn {{ background:#f50057; color:#fff; border:none; padding:10px 15px; cursor:pointer; border-radius:4px; margin:10px; }}
    </style>
</head>
<body>
    <div class="nav">
        <b>NOW TV FULL ARŞİV (${{Object.keys(data).length}} Dizi)</b>
        <input type="text" id="search" placeholder="Ara..." oninput="doSearch()" style="padding:5px; border-radius:4px; border:none;">
    </div>
    <div id="m-grid" class="grid"></div>
    <div id="p-view" class="player">
        <button class="btn" onclick="closeP()">✕ KAPAT</button>
        <div id="v-frame" style="height:calc(100% - 60px);"></div>
    </div>
    <script>
        const data = {json_embedded};
        function init() {{
            const m = document.getElementById("m-grid");
            m.innerHTML = "";
            Object.keys(data).forEach(id => {{
                const c = document.createElement("div");
                c.className = "card";
                c.innerHTML = `<img src="${{data[id].resim}}"><div class="card-name">${{data[id].isim}}</div>`;
                c.onclick = () => showE(id);
                m.appendChild(c);
            }});
        }}
        function showE(id) {{
            window.scrollTo(0,0);
            const m = document.getElementById("m-grid");
            m.innerHTML = `<div style="grid-column:1/-1"><button class="btn" onclick="init()">← ANA SAYFA</button><h2>${{data[id].isim}}</h2></div>`;
            data[id].bolumler.forEach(ep => {{
                const c = document.createElement("div");
                c.className = "card";
                c.innerHTML = `<img src="${{data[id].resim}}"><div class="card-name">${{ep.ad}}</div>`;
                c.onclick = () => play(ep.link);
                m.appendChild(c);
            }});
        }}
        function play(l) {{
            document.getElementById("p-view").style.display = "block";
            let u = l.includes(".m3u8") ? "https://bradmax.com/client/embed-player/d9decbf0d308f4bb91825c3f3a2beb7b0aaee2f6_8493?mediaUrl=" + encodeURIComponent(l) : l;
            document.getElementById("v-frame").innerHTML = `<iframe src="${{u}}&autoplay=true" width="100%" height="100%" frameborder="0" allowfullscreen></iframe>`;
        }}
        function closeP() {{ document.getElementById("p-view").style.display="none"; document.getElementById("v-frame").innerHTML=""; }}
        function doSearch() {{
            let q = document.getElementById("search").value.toLowerCase();
            document.querySelectorAll(".card").forEach(c => c.style.display = c.innerText.toLowerCase().includes(q) ? "" : "none");
        }}
        init();
    </script>
</body>
</html>'''

    with open(file_name, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    try:
        subprocess.run(["git", "config", "--global", "user.name", "github-actions[bot]"], check=True)
        subprocess.run(["git", "config", "--global", "user.email", "github-actions[bot]@users.noreply.github.com"], check=True)
        subprocess.run(["git", "add", file_name], check=True)
        subprocess.run(["git", "commit", "-m", "🔄 Arşiv Tamamlandı"], check=True)
        subprocess.run(["git", "push"], check=True)
    except: pass

if __name__ == "__main__":
    run_scraper()

import cloudscraper
from bs4 import BeautifulSoup
import json
import time
import re
import os
import subprocess

# Ayarlar
BASE_URL = "https://www.kanald.com.tr"
ARCHIVE_URL = "https://www.kanald.com.tr/diziler/arsiv?page="
BRADMAX_PLAYER_URL = "https://bradmax.com/client/embed-player/d9decbf0d308f4bb91825c3f3a2beb7b0aaee2f6_8493?mediaUrl="

def slugify(text):
    mapping = {'ç':'c','ğ':'g','ı':'i','ö':'o','ş':'s','ü':'u','İ':'i'}
    text = text.lower()
    for tr, en in mapping.items(): text = text.replace(tr, en)
    return re.sub(r'[^a-z0-9]+', '-', text).strip('-')

def commit_and_push(file_name):
    """GitHub Actions ortamında dosyayı repoya push eder."""
    print(f"\n📤 {file_name} GitHub'a gönderiliyor...")
    try:
        subprocess.run(["git", "config", "--global", "user.name", "github-actions[bot]"], check=True)
        subprocess.run(["git", "config", "--global", "user.email", "github-actions[bot]@users.noreply.github.com"], check=True)
        subprocess.run(["git", "add", file_name], check=True)
        status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout
        if status:
            subprocess.run(["git", "commit", "-m", "🔄 Kanal D Arşivi Güncellendi (PHP Embed Logic)"], check=True)
            subprocess.run(["git", "push"], check=True)
            print("🚀 GitHub'a başarıyla yüklendi!")
    except Exception as e:
        print(f"❌ Git Hatası: {e}")

def get_embed_link(scraper, bolum_url):
    """PHP kodundaki preg_match mantığı: Sayfadan gerçek embed linkini çeker"""
    try:
        resp = scraper.get(bolum_url, timeout=10)
        # PHP'deki: <link itemprop="embedURL" href="..."> araması
        match = re.search(r'<link[^>]+itemprop=["\']embedURL["\'][^>]+href=["\']([^"\']+)#i', resp.text)
        if not match:
            # Alternatif regex (bazı sayfalarda sıra değişebilir)
            match = re.search(r'itemprop=["\']embedURL["\']\s+href=["\']([^"\']+)["\']', resp.text)
        
        return match.group(1) if match else bolum_url
    except:
        return bolum_url

def get_series_episodes(scraper, series_url):
    episodes = []
    target_url = series_url.rstrip('/') + "/bolumler"
    try:
        resp = scraper.get(target_url, timeout=15)
        soup = BeautifulSoup(resp.text, 'html.parser')
        cards = soup.select('.story-card, .content-card, .video-card')
        for card in cards:
            link = card.find('a', href=True) or (card if card.name == 'a' else None)
            title_tag = card.select_one('.title, h3, h2, .caption')
            if link and title_tag:
                href = link['href']
                full_link = BASE_URL + href if href.startswith('/') else href
                
                # PHP MANTIĞI BURADA DEVREYE GİRİYOR:
                # Sadece sayfa linkini değil, sayfanın içindeki gerçek video linkini alıyoruz
                print(f"      🔍 Embed ID aranıyor: {title_tag.get_text(strip=True)}")
                real_video_link = get_embed_link(scraper, full_link)
                
                episodes.append({
                    "ad": title_tag.get_text(strip=True),
                    "link": real_video_link
                })
        return episodes[::-1]
    except: return []

def run_scraper():
    print("🚀 Kanal D - ME TV Scraper (Full Archive + PHP Embed Logic) Başlatıldı...")
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
    
    series_data = {}
    page = 1
    
    while page <= 10: # Sayfa sınırı (İstersen artırabilirsin)
        print(f"\n📄 Arşiv Sayfası {page} taranıyor...")
        try:
            response = scraper.get(f"{ARCHIVE_URL}{page}", timeout=20)
            if response.status_code != 200: break
            
            soup = BeautifulSoup(response.text, 'html.parser')
            cards = soup.select('a.poster-card')
            if not cards: break

            for card in cards:
                title = card.get('title') or card.find('img').get('alt', 'Dizi')
                href = card.get('href')
                dizi_id = slugify(title)
                
                if dizi_id in series_data: continue

                print(f"  📺 {title} taranıyor...")
                full_url = BASE_URL + href if href.startswith('/') else href
                eps = get_series_episodes(scraper, full_url)
                
                if eps:
                    img = card.find('img')
                    poster = img.get('data-src') or img.get('src', '')
                    if not poster.startswith('http'): poster = "https:" + poster
                    
                    series_data[dizi_id] = {
                        "resim": poster,
                        "bolumler": eps
                    }
            page += 1
            time.sleep(1)
        except: break

    create_html(series_data)

def create_html(series_data):
    file_name = "kanald_vod.html"
    json_data = json.dumps(series_data, ensure_ascii=False)
    
    # HTML TEMPLATE (Show TV Stilinde)
    html_template = f'''<!DOCTYPE html>
<html lang="tr">
<head>
    <title>ME TV KANAL D</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://code.jquery.com/jquery-3.5.1.min.js"></script>
    <style>
        body {{ margin: 0; background: #00040d; color: white; font-family: sans-serif; font-style: italic; }}
        .aramapanel {{ width: 100%; height: 65px; background: #15161a; border-bottom: 1px solid #323442; padding: 10px 20px; box-sizing: border-box; display: flex; justify-content: space-between; align-items: center; position: sticky; top: 0; z-index: 1000; }}
        .logo-area {{ display: flex; align-items: center; font-weight: bold; font-size: 18px; color: #572aa7; }}
        .logo-area img {{ height: 40px; margin-right: 12px; }}
        .search-area input {{ background: #0a0e17; border: 1px solid #323442; color: white; padding: 8px 15px; border-radius: 20px; outline: none; width: 180px; }}
        .filmpaneldis {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 15px; padding: 20px; }}
        .filmpanel {{ background: #15161a; border: 1px solid #323442; border-radius: 10px; overflow: hidden; cursor: pointer; transition: 0.3s; aspect-ratio: 2/3; position: relative; }}
        .filmpanel:hover {{ border-color: #572aa7; transform: translateY(-5px); }}
        .filmresim img {{ width: 100%; height: 100%; object-fit: cover; }}
        .filmisimpanel {{ position: absolute; bottom: 0; background: linear-gradient(transparent, black); width: 100%; padding: 10px; box-sizing: border-box; }}
        .filmisim {{ font-size: 12px; font-weight: bold; text-align: center; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
        .hidden {{ display: none !important; }}
        .playerpanel {{ position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: black; z-index: 9999; display: none; }}
        .geri-btn {{ background: #572aa7; color: white; padding: 10px 20px; border: none; cursor: pointer; margin: 15px; border-radius: 5px; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="aramapanel">
        <div class="logo-area"><img src="https://i.hizliresim.com/t6e66bt.png">ME TV</div>
        <div class="search-area"><input type="text" id="seriesSearch" placeholder="Ara..." oninput="search()"></div>
    </div>
    <div id="diziListesiContainer" class="filmpaneldis"></div>
    <div id="bolumContainer" class="hidden">
        <button class="geri-btn" onclick="geriDon()">← GERİ DÖN</button>
        <div id="bolumListesi" class="filmpaneldis"></div>
    </div>
    <div id="playerpanel" class="playerpanel">
        <button class="geri-btn" onclick="geriPlayer()">← KAPAT</button>
        <div id="main-player" style="height: calc(100% - 80px);"></div>
    </div>

    <script>
        var diziler = {json_data};
        const BRADMAX_PLAYER = "{BRADMAX_PLAYER_URL}";

        function init() {{
            const container = document.getElementById("diziListesiContainer");
            Object.keys(diziler).forEach(key => {{
                const d = diziler[key];
                const item = document.createElement("div");
                item.className = "filmpanel";
                item.innerHTML = `<div class="filmresim"><img src="${{d.resim}}"></div><div class="filmisimpanel"><div class="filmisim">${{key.replace(/-/g,' ').toUpperCase()}}</div></div>`;
                item.onclick = () => showBolumler(key);
                container.appendChild(item);
            }});
        }}

        function showBolumler(key) {{
            window.scrollTo(0,0);
            document.getElementById("diziListesiContainer").classList.add("hidden");
            document.getElementById("bolumContainer").classList.remove("hidden");
            const list = document.getElementById("bolumListesi");
            list.innerHTML = "";
            diziler[key].bolumler.forEach(ep => {{
                const item = document.createElement("div");
                item.className = "filmpanel";
                item.innerHTML = `<div class="filmresim"><img src="${{diziler[key].resim}}"></div><div class="filmisimpanel"><div class="filmisim">${{ep.ad}}</div></div>`;
                item.onclick = () => showPlayer(ep.link);
                list.appendChild(item);
            }});
        }}

        function showPlayer(link) {{
            document.getElementById("playerpanel").style.display = "block";
            // Eğer link zaten bir embed ise direkt kullan, değilse Bradmax ile sarmala
            let finalUrl = link.includes('bradmax') ? link : BRADMAX_PLAYER + encodeURIComponent(link);
            document.getElementById("main-player").innerHTML = `<iframe src="${{finalUrl}}&autoplay=true" width="100%" height="100%" frameborder="0" allowfullscreen></iframe>`;
        }}

        function geriDon() {{
            document.getElementById("diziListesiContainer").classList.remove("hidden");
            document.getElementById("bolumContainer").classList.add("hidden");
        }}

        function geriPlayer() {{
            document.getElementById("playerpanel").style.display = "none";
            document.getElementById("main-player").innerHTML = "";
        }}

        function search() {{
            let val = document.getElementById("seriesSearch").value.toLowerCase();
            $(".filmpanel").each(function() {{
                $(this).toggle($(this).text().toLowerCase().includes(val));
            }});
        }}
        init();
    </script>
</body>
</html>'''

    with open(file_name, "w", encoding="utf-8") as f:
        f.write(html_template)
    
    print(f"\n✅ İşlem tamamlandı! {file_name} oluşturuldu.")
    if os.getenv('GITHUB_ACTIONS') == 'true' or os.path.exists('.git'):
        commit_and_push(file_name)

if __name__ == "__main__":
    run_scraper()

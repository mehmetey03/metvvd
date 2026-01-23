import cloudscraper
from bs4 import BeautifulSoup
import json
import time
import re
import os
import subprocess

# Web sitesi kök adresi
BASE_URL = "https://www.kanald.com.tr"

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
            subprocess.run(["git", "commit", "-m", "🔄 Kanal D Arşivi Güncellendi"], check=True)
            subprocess.run(["git", "push"], check=True)
            print("🚀 GitHub Reponuza başarıyla yüklendi!")
        else:
            print("ℹ️ Değişiklik yok.")
    except Exception as e:
        print(f"❌ Git Hatası: {e}")

def get_series_episodes(scraper, series_url):
    episodes = []
    target_url = series_url.rstrip('/') + "/bolumler"
    try:
        resp = scraper.get(target_url, timeout=15)
        soup = BeautifulSoup(resp.text, 'html.parser')
        cards = soup.select('.story-card, .content-card')
        for card in cards:
            link = card.find('a', href=True) or (card if card.name == 'a' else None)
            title_tag = card.select_one('.title, h3, h2')
            if link and title_tag:
                full_link = BASE_URL + link['href'] if link['href'].startswith('/') else link['href']
                episodes.append({
                    "ad": title_tag.get_text(strip=True),
                    "link": full_link
                })
        return episodes[::-1] # Eskiden yeniye sırala
    except: return []

def run_scraper():
    print("🚀 Kanal D Arşiv Oluşturucu Başlatıldı...")
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
    
    series_data = {}
    try:
        response = scraper.get(f"{BASE_URL}/diziler", timeout=20)
        soup = BeautifulSoup(response.text, 'html.parser')
        cards = soup.select('a.poster-card')

        for idx, card in enumerate(cards[:20], 1): # İlk 20 diziyi al
            title = card.get('title') or card.find('img').get('alt', 'Dizi')
            href = card.get('href')
            print(f"[{idx}] 📺 {title} taranıyor...")
            
            full_url = BASE_URL + href if href.startswith('/') else href
            eps = get_series_episodes(scraper, full_url)
            
            if eps:
                img = card.find('img')
                poster = img.get('data-src') or img.get('src', '')
                if not poster.startswith('http'): poster = "https:" + poster
                
                series_data[slugify(title)] = {
                    "resim": poster,
                    "bolumler": eps
                }
                print(f"    ✅ {len(eps)} bölüm bulundu.")
            time.sleep(0.3)

        create_html(series_data)

    except Exception as e:
        print(f"❌ Hata: {e}")

def create_html(series_data):
    file_name = "kanald_archive.html"
    json_data = json.dumps(series_data, ensure_ascii=False)
    
    # SENİN SHOWTV İÇİN VERDİĞİN GÖZ ALICI TASARIM
    html_template = f'''<!DOCTYPE html>
<html lang="tr">
<head>
    <title>ME TV KANAL D VOD</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://code.jquery.com/jquery-3.5.1.min.js"></script>
    <script src="https://kit.fontawesome.com/bbe955c5ed.js" crossorigin="anonymous"></script>
    <style>
        body {{ margin: 0; background: #00040d; color: white; font-family: sans-serif; font-style: italic; }}
        .aramapanel {{ width: 100%; height: 60px; background: #15161a; border-bottom: 1px solid #323442; padding: 10px; box-sizing: border-box; display: flex; justify-content: space-between; align-items: center; position: sticky; top: 0; z-index: 100; }}
        .logo-area {{ display: flex; align-items: center; }}
        .logo-area img {{ width: 40px; margin-right: 10px; }}
        .aramapanelyazi {{ height: 35px; background: #222; border: 1px solid #444; color: white; padding: 0 10px; border-radius: 4px; }}
        .aramapanelbuton {{ height: 35px; background: #572aa7; color: white; border: none; padding: 0 15px; cursor: pointer; }}
        .filmpaneldis {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 15px; padding: 20px; }}
        .filmpanel {{ background: #15161a; border: 1px solid #323442; border-radius: 10px; overflow: hidden; cursor: pointer; transition: 0.3s; position: relative; }}
        .filmpanel:hover {{ border-color: #572aa7; transform: scale(1.05); }}
        .filmresim img {{ width: 100%; height: 200px; object-fit: cover; }}
        .filmisimpanel {{ position: absolute; bottom: 0; background: linear-gradient(transparent, black); width: 100%; padding: 10px; box-sizing: border-box; }}
        .filmisim {{ font-size: 12px; font-weight: bold; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
        .hidden {{ display: none !important; }}
        .playerpanel {{ position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: black; z-index: 2000; display: none; }}
        .geri-btn {{ background: #572aa7; color: white; padding: 10px 20px; border: none; cursor: pointer; margin: 10px; border-radius: 5px; }}
    </style>
</head>
<body>
    <div class="aramapanel">
        <div class="logo-area"><img src="https://i.hizliresim.com/t6e66bt.png"><span>ME TV KANAL D</span></div>
        <div class="search-area">
            <input type="text" id="seriesSearch" placeholder="Dizi Ara..." class="aramapanelyazi" oninput="search()">
        </div>
    </div>

    <div id="diziListesiContainer" class="filmpaneldis"></div>

    <div id="bolumContainer" class="hidden">
        <button class="geri-btn" onclick="geriDon()">← Geri Dön</button>
        <div id="bolumListesi" class="filmpaneldis"></div>
    </div>

    <div id="playerpanel" class="playerpanel">
        <button class="geri-btn" onclick="geriPlayer()">← Kapat</button>
        <div id="main-player" style="height: calc(100% - 60px);"></div>
    </div>

    <script>
        var diziler = {json_data};
        const BRADMAX_URL = "https://bradmax.com/client/embed-player/d9decbf0d308f4bb91825c3f3a2beb7b0aaee2f6_8493?mediaUrl=";

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
            const playerArea = document.getElementById("main-player");
            playerArea.innerHTML = `<iframe src="${{BRADMAX_URL + encodeURIComponent(link)}}&autoplay=true" width="100%" height="100%" frameborder="0" allowfullscreen></iframe>`;
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
    
    print(f"✅ Dosya oluşturuldu: {file_name}")
    if os.getenv('GITHUB_ACTIONS') == 'true' or os.path.exists('.git'):
        commit_and_push(file_name)

if __name__ == "__main__":
    run_scraper()

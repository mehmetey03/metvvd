import cloudscraper
from bs4 import BeautifulSoup
import json
import time
import re
import os
import subprocess

# Ayarlar
BASE_URL = "https://www.nowtv.com.tr"
ARCHIVE_URL = "https://www.nowtv.com.tr/diziler/arsiv?page="
BRADMAX_PLAYER = "https://bradmax.com/client/embed-player/d9decbf0d308f4bb91825c3f3a2beb7b0aaee2f6_8493?mediaUrl="

def slugify(text):
    mapping = {'ç':'c','ğ':'g','ı':'i','ö':'o','ş':'s','ü':'u','İ':'i'}
    text = text.lower()
    for tr, en in mapping.items(): text = text.replace(tr, en)
    return re.sub(r'[^a-z0-9]+', '-', text).strip('-')

def get_now_m3u8(scraper, url):
    """Now TV sayfalarından m3u8 veya video kaynağını ayıklar"""
    try:
        resp = scraper.get(url, timeout=10)
        # Now TV genellikle video verilerini JSON veya script içinde 'videoUrl' ya da 'hls' olarak tutar
        m3u8_match = re.search(r'["\'](https?://[^"\']+\.m3u8[^"\']*)["\']', resp.text)
        if m3u8_match:
            return m3u8_match.group(1).replace('\\/', '/')
        
        # Alternatif: Embed iframe varsa onu yakala
        embed_match = re.search(r'iframe src=["\']([^"\']+)["\']', resp.text)
        if embed_match:
            return embed_match.group(1)
            
        return url
    except:
        return url

def commit_and_push(file_name):
    print(f"\n📤 {file_name} GitHub'a gönderiliyor...")
    try:
        subprocess.run(["git", "config", "--global", "user.name", "github-actions[bot]"], check=True)
        subprocess.run(["git", "config", "--global", "user.email", "github-actions[bot]@users.noreply.github.com"], check=True)
        subprocess.run(["git", "add", file_name], check=True)
        if subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout:
            subprocess.run(["git", "commit", "-m", "🔄 Now TV Arşivi Güncellendi"], check=True)
            subprocess.run(["git", "push"], check=True)
            print("🚀 GitHub'a başarıyla yüklendi!")
    except Exception as e: print(f"❌ Git Hatası: {e}")

def run_scraper():
    print("🚀 Now TV - ME TV VOD Scraper Başlatıldı...")
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
    series_data = {}
    
    for page in range(1, 6): # Now TV arşiv sayfaları (ihtiyaca göre artırılabilir)
        print(f"\n📄 Now TV Sayfa {page} taranıyor...")
        try:
            resp = scraper.get(f"{ARCHIVE_URL}{page}", timeout=15)
            soup = BeautifulSoup(resp.text, 'html.parser')
            # Now TV'nin dizi kartları seçicisi (Genellikle 'video-box' veya 'show-card')
            cards = soup.select('.video-box, .show-card, a[href*="/diziler/"]')
            
            if not cards: break

            for card in cards:
                href = card.get('href')
                if not href or "/arsiv" in href: continue
                
                title_tag = card.select_one('.title, .name, h3')
                title = title_tag.get_text(strip=True) if title_tag else "Dizi"
                dizi_id = slugify(title)
                
                if dizi_id in series_data: continue

                print(f"  📺 {title} bölümleri taranıyor...")
                full_url = BASE_URL + href if href.startswith('/') else href
                
                # Bölümler sayfasına git
                b_url = full_url.rstrip('/') + "/bolumler"
                b_resp = scraper.get(b_url)
                b_soup = BeautifulSoup(b_resp.text, 'html.parser')
                b_cards = b_soup.select('a[href*="/bolumler/"]')

                eps = []
                for bc in b_cards[:12]: # Son 12 bölüm
                    b_href = bc.get('href')
                    b_title = bc.select_one('.title, .name, span')
                    if b_href and b_title:
                        episode_url = BASE_URL + b_href if b_href.startswith('/') else b_href
                        m3u8 = get_now_m3u8(scraper, episode_url)
                        eps.append({"ad": b_title.get_text(strip=True), "link": m3u8})
                
                if eps:
                    img = card.find('img')
                    poster = img.get('src') or img.get('data-src', '')
                    if poster and not poster.startswith('http'): poster = "https:" + poster
                    
                    series_data[dizi_id] = {"resim": poster, "bolumler": eps[::-1]}
                    print(f"    ✅ {len(eps)} bölüm eklendi.")
                    
            time.sleep(1)
        except Exception as e:
            print(f"❌ Sayfa hatası: {e}")
            continue

    create_html(series_data)

def create_html(series_data):
    file_name = "nowtv_vod.html"
    json_str = json.dumps(series_data, ensure_ascii=False)
    
    # ME TV - Standart Koyu Tema
    html = f'''<!DOCTYPE html>
<html lang="tr">
<head>
    <title>ME TV NOW TV</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://code.jquery.com/jquery-3.5.1.min.js"></script>
    <style>
        body {{ margin: 0; background: #00040d; color: white; font-family: sans-serif; font-style: italic; }}
        .aramapanel {{ width: 100%; height: 65px; background: #15161a; border-bottom: 1px solid #323442; padding: 10px 20px; box-sizing: border-box; display: flex; justify-content: space-between; align-items: center; position: sticky; top: 0; z-index: 1000; }}
        .logo-area {{ font-weight: bold; color: #572aa7; font-size: 20px; }}
        .search-area input {{ background: #0a0e17; border: 1px solid #323442; color: white; padding: 8px 15px; border-radius: 20px; outline: none; }}
        .filmpaneldis {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 15px; padding: 20px; }}
        .filmpanel {{ background: #15161a; border: 1px solid #323442; border-radius: 10px; overflow: hidden; cursor: pointer; transition: 0.3s; position: relative; aspect-ratio: 2/3; }}
        .filmpanel:hover {{ border-color: #572aa7; transform: scale(1.02); }}
        .filmresim img {{ width: 100%; height: 100%; object-fit: cover; }}
        .filmisimpanel {{ position: absolute; bottom: 0; background: rgba(0,0,0,0.8); width: 100%; padding: 8px; text-align: center; font-size: 11px; font-weight: bold; }}
        .hidden {{ display: none !important; }}
        .playerpanel {{ position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: black; z-index: 9999; display: none; }}
        .geri-btn {{ background: #572aa7; color: white; padding: 10px 15px; border: none; cursor: pointer; margin: 10px; border-radius: 5px; }}
    </style>
</head>
<body>
    <div class="aramapanel">
        <div class="logo-area">ME TV NOW</div>
        <div class="search-area"><input type="text" id="seriesSearch" placeholder="Ara..." oninput="search()"></div>
    </div>
    <div id="listContainer" class="filmpaneldis"></div>
    <div id="bolumContainer" class="hidden"><button class="geri-btn" onclick="backToMain()">← ANA SAYFA</button><div id="bolumListesi" class="filmpaneldis"></div></div>
    <div id="playerpanel" class="playerpanel"><button class="geri-btn" onclick="closePlayer()">← KAPAT</button><div id="main-player" style="height: calc(100% - 80px);"></div></div>

    <script>
        var diziler = {json_str};
        function init() {{
            const c = document.getElementById("listContainer");
            Object.keys(diziler).forEach(k => {{
                const d = diziler[k];
                const item = document.createElement("div");
                item.className = "filmpanel";
                item.innerHTML = `<div class="filmresim"><img src="${{d.resim}}"></div><div class="filmisimpanel">${{k.toUpperCase()}}</div>`;
                item.onclick = () => showEpisodes(k);
                c.appendChild(item);
            }});
        }}
        function showEpisodes(k) {{
            window.scrollTo(0,0);
            document.getElementById("listContainer").classList.add("hidden");
            document.getElementById("bolumContainer").classList.remove("hidden");
            const bl = document.getElementById("bolumListesi");
            bl.innerHTML = "";
            diziler[k].bolumler.forEach(e => {{
                const bi = document.createElement("div");
                bi.className = "filmpanel";
                bi.innerHTML = `<div class="filmresim"><img src="${{diziler[k].resim}}"></div><div class="filmisimpanel">${{e.ad}}</div>`;
                bi.onclick = () => play(e.link);
                bl.appendChild(bi);
            }});
        }}
        function play(link) {{
            document.getElementById("playerpanel").style.display = "block";
            let finalUrl = link.includes(".m3u8") ? "{BRADMAX_PLAYER}" + encodeURIComponent(link) : link;
            document.getElementById("main-player").innerHTML = `<iframe src="${{finalUrl}}&autoplay=true" width="100%" height="100%" frameborder="0" allowfullscreen></iframe>`;
        }}
        function backToMain() {{ document.getElementById("listContainer").classList.remove("hidden"); document.getElementById("bolumContainer").classList.add("hidden"); }}
        function closePlayer() {{ document.getElementById("playerpanel").style.display = "none"; document.getElementById("main-player").innerHTML = ""; }}
        function search() {{
            let v = $("#seriesSearch").val().toLowerCase();
            $(".filmpanel").each(function() {{ $(this).toggle($(this).text().toLowerCase().includes(v)); }});
        }}
        init();
    </script>
</body>
</html>'''

    with open(file_name, "w", encoding="utf-8") as f: f.write(html)
    commit_and_push(file_name)

if __name__ == "__main__":
    run_scraper()

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
BRADMAX_PLAYER = "https://bradmax.com/client/embed-player/d9decbf0d308f4bb91825c3f3a2beb7b0aaee2f6_8493?mediaUrl="

def slugify(text):
    mapping = {'ç':'c','ğ':'g','ı':'i','ö':'o','ş':'s','ü':'u','İ':'i'}
    text = text.lower()
    for tr, en in mapping.items(): text = text.replace(tr, en)
    return re.sub(r'[^a-z0-9]+', '-', text).strip('-')

def get_real_m3u8(scraper, bolum_url):
    """PHP kodundaki çift aşamalı M3U8 bulma mantığı"""
    try:
        # 1. Aşama: Bölüm sayfasından Embed URL'yi çek
        r1 = scraper.get(bolum_url, timeout=10)
        embed_match = re.search(r'<link[^>]+itemprop=["\']embedURL["\'][^>]+href=["\']([^"\']+)["\']', r1.text)
        
        if not embed_match:
            return bolum_url # Bulamazsa ana linke dön
            
        embed_url = embed_match.group(1)
        
        # 2. Aşama: Embed sayfasının içine girip M3U8 pattern'lerini ara
        r2 = scraper.get(embed_url, timeout=10, headers={"Referer": BASE_URL})
        embed_html = r2.text
        
        # PHP'deki Regex Pattern'leri
        patterns = [
            r'https?://vod[0-9]*\.cf\.dmcdn\.net/[^\s"\']+\.m3u8', # DMCDN Pattern
            r'https?://[^\s"\']+\.m3u8',                          # Genel M3U8
            r'["\']videoUrl["\']\s*:\s*["\']([^"\']+)["\']',      # JS VideoURL
            r'src=["\']([^"\']+\.m3u8)["\']'                      # Src tag
        ]
        
        for p in patterns:
            m = re.search(p, embed_html)
            if m:
                found_url = m.group(1) if "(" in p else m.group(0)
                # Unescape yap (\\/ -> /)
                return found_url.replace('\\/', '/')
        
        return embed_url # M3U8 bulunamazsa embed sayfasını döndür
    except:
        return bolum_url

def commit_and_push(file_name):
    print(f"\n📤 {file_name} GitHub'a gönderiliyor...")
    try:
        subprocess.run(["git", "config", "--global", "user.name", "github-actions[bot]"], check=True)
        subprocess.run(["git", "config", "--global", "user.email", "github-actions[bot]@users.noreply.github.com"], check=True)
        subprocess.run(["git", "add", file_name], check=True)
        if subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout:
            subprocess.run(["git", "commit", "-m", "🔄 Kanal D M3U8 Arşivi Güncellendi"], check=True)
            subprocess.run(["git", "push"], check=True)
            print("🚀 GitHub'a yüklendi!")
    except Exception as e: print(f"❌ Git Hatası: {e}")

def run_scraper():
    print("🚀 Kanal D M3U8 Scraper Başlatıldı (Sayfa 1-10)...")
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
    series_data = {}
    
    for page in range(1, 11): # İlk 10 sayfayı tara
        print(f"\n📄 Sayfa {page} taranıyor...")
        try:
            resp = scraper.get(f"{ARCHIVE_URL}{page}", timeout=15)
            soup = BeautifulSoup(resp.text, 'html.parser')
            cards = soup.select('a.poster-card')
            if not cards: break

            for card in cards:
                title = card.get('title') or card.find('img').get('alt', 'Dizi')
                href = card.get('href')
                dizi_id = slugify(title)
                
                print(f"  📺 {title} bölümleri çekiliyor...")
                full_url = BASE_URL + href if href.startswith('/') else href
                
                # Bölümleri bul
                b_resp = scraper.get(full_url.rstrip('/') + "/bolumler")
                b_soup = BeautifulSoup(b_resp.text, 'html.parser')
                b_cards = b_soup.select('.story-card, .content-card, .video-card')
                
                eps = []
                for bc in b_cards[:10]: # Performans için her diziden son 10 bölüm
                    link_tag = bc.find('a', href=True) or (bc if bc.name == 'a' else None)
                    name_tag = bc.select_one('.title, h3, h2, .caption')
                    if link_tag and name_tag:
                        b_url = BASE_URL + link_tag['href'] if link_tag['href'].startswith('/') else link_tag['href']
                        
                        # PHP'den gelen M3U8 mantığı burada!
                        m3u8_link = get_real_m3u8(scraper, b_url)
                        
                        eps.append({"ad": name_tag.get_text(strip=True), "link": m3u8_link})
                        print(f"    🔗 M3U8 Yakalandı: {name_tag.get_text(strip=True)[:30]}...")
                
                if eps:
                    img = card.find('img')
                    poster = img.get('data-src') or img.get('src', '')
                    series_data[dizi_id] = {"resim": poster, "bolumler": eps[::-1]}
                    
        except Exception as e:
            print(f"❌ Hata: {e}")
            continue

    create_html(series_data)

def create_html(series_data):
    file_name = "kanald_vod.html"
    json_str = json.dumps(series_data, ensure_ascii=False)
    
    html = f'''<!DOCTYPE html>
<html lang="tr">
<head>
    <title>METV  VOD</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://code.jquery.com/jquery-3.5.1.min.js"></script>
    <style>
        body {{ margin: 0; background: #00040d; color: white; font-family: sans-serif; font-style: italic; }}
        .aramapanel {{ width: 100%; height: 65px; background: #15161a; border-bottom: 1px solid #323442; padding: 10px 20px; box-sizing: border-box; display: flex; justify-content: space-between; align-items: center; position: sticky; top: 0; z-index: 1000; }}
        .logo-area {{ font-weight: bold; color: #572aa7; display: flex; align-items: center; }}
        .search-area input {{ background: #0a0e17; border: 1px solid #323442; color: white; padding: 8px 15px; border-radius: 20px; outline: none; }}
        .filmpaneldis {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 15px; padding: 20px; }}
        .filmpanel {{ background: #15161a; border: 1px solid #323442; border-radius: 10px; overflow: hidden; cursor: pointer; transition: 0.3s; position: relative; aspect-ratio: 2/3; }}
        .filmpanel:hover {{ border-color: #572aa7; transform: translateY(-5px); }}
        .filmresim img {{ width: 100%; height: 100%; object-fit: cover; }}
        .filmisimpanel {{ position: absolute; bottom: 0; background: linear-gradient(transparent, black); width: 100%; padding: 10px; text-align: center; }}
        .hidden {{ display: none !important; }}
        .playerpanel {{ position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: black; z-index: 9999; display: none; }}
        .geri-btn {{ background: #572aa7; color: white; padding: 10px 20px; border: none; cursor: pointer; margin: 15px; border-radius: 5px; }}
    </style>
</head>
<body>
    <div class="aramapanel">
        <div class="logo-area">METV KANAL D VOD</div>
        <div class="search-area"><input type="text" id="seriesSearch" placeholder="Dizi ara..." oninput="search()"></div>
    </div>
    <div id="diziListesiContainer" class="filmpaneldis"></div>
    <div id="bolumContainer" class="hidden"><button class="geri-btn" onclick="geriDon()">← GERİ</button><div id="bolumListesi" class="filmpaneldis"></div></div>
    <div id="playerpanel" class="playerpanel"><button class="geri-btn" onclick="geriPlayer()">← KAPAT</button><div id="main-player" style="height: calc(100% - 80px);"></div></div>

    <script>
        var diziler = {json_str};
        const BRADMAX = "{BRADMAX_PLAYER}";

        function init() {{
            const c = document.getElementById("diziListesiContainer");
            Object.keys(diziler).forEach(k => {{
                const item = document.createElement("div");
                item.className = "filmpanel";
                item.innerHTML = `<div class="filmresim"><img src="${{diziler[k].resim}}"></div><div class="filmisimpanel"><div>${{k.toUpperCase()}}</div></div>`;
                item.onclick = () => {{
                    document.getElementById("diziListesiContainer").classList.add("hidden");
                    document.getElementById("bolumContainer").classList.remove("hidden");
                    const bl = document.getElementById("bolumListesi");
                    bl.innerHTML = "";
                    diziler[k].bolumler.forEach(e => {{
                        const bi = document.createElement("div");
                        bi.className = "filmpanel";
                        bi.innerHTML = `<div class="filmresim"><img src="${{diziler[k].resim}}"></div><div class="filmisimpanel"><div>${{e.ad}}</div></div>`;
                        bi.onclick = (event) => {{ event.stopPropagation(); play(e.link); }};
                        bl.appendChild(bi);
                    }});
                }};
                c.appendChild(item);
            }});
        }}

        function play(link) {{
            document.getElementById("playerpanel").style.display = "block";
            let url = link.includes(".m3u8") ? BRADMAX + encodeURIComponent(link) : link;
            document.getElementById("main-player").innerHTML = `<iframe src="${{url}}&autoplay=true" width="100%" height="100%" frameborder="0" allowfullscreen></iframe>`;
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

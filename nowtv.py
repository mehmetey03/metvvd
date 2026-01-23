import cloudscraper
from bs4 import BeautifulSoup
import json
import time
import re
import subprocess

# Ayarlar
BASE_URL = "https://www.nowtv.com.tr"
ARCHIVE_URL = "https://www.nowtv.com.tr/dizi-arsivi"
# Bradmax veya benzeri bir player kullanılabilir, NowTV m3u8'leri için standart iframe desteği
BRADMAX_PLAYER = "https://bradmax.com/client/embed-player/d9decbf0d308f4bb91825c3f3a2beb7b0aaee2f6_8493?mediaUrl="

def slugify(text):
    mapping = {'ç':'c','ğ':'g','ı':'i','ö':'o','ş':'s','ü':'u','İ':'i','I':'i'}
    text = text.lower()
    for tr, en in mapping.items(): text = text.replace(tr, en)
    return re.sub(r'[^a-z0-9]+', '-', text).strip('-')

def get_now_m3u8(scraper, bolum_url):
    """NowTV özel m3u8 bulma mantığı"""
    try:
        # Engeli aşmak için biraz bekle
        time.sleep(1)
        r = scraper.get(bolum_url, timeout=15)
        html = r.text
        
        # 1. Regex ile m3u8 ara (NowTV genellikle JSON içinde veya script içinde saklar)
        m3u8_match = re.search(r'(https?://[^\s"\']+\.m3u8[^\s"\']*)', html)
        if m3u8_match:
            link = m3u8_match.group(0).replace('\\/', '/')
            return link
            
        # 2. Alternatif: Data attribute kontrolü
        soup = BeautifulSoup(html, 'html.parser')
        video_div = soup.find('div', {'data-video-source': True})
        if video_div:
            return video_div['data-video-source']
            
        return bolum_url # Bulamazsa sayfa linkini döndür
    except:
        return bolum_url

def commit_and_push(file_name):
    print(f"\n📤 {file_name} GitHub'a gönderiliyor...")
    try:
        subprocess.run(["git", "config", "--global", "user.name", "github-actions[bot]"], check=True)
        subprocess.run(["git", "config", "--global", "user.email", "github-actions[bot]@users.noreply.github.com"], check=True)
        subprocess.run(["git", "add", file_name], check=True)
        if subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout:
            subprocess.run(["git", "commit", "-m", "🔄 NOW TV M3U8 Arşivi Güncellendi"], check=True)
            subprocess.run(["git", "push"], check=True)
            print("🚀 GitHub'a yüklendi!")
    except Exception as e: print(f"❌ Git Hatası: {e}")

def run_scraper():
    print("🚀 NOW TV M3U8 Scraper Başlatıldı...")
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
    series_data = {}
    
    try:
        resp = scraper.get(ARCHIVE_URL, timeout=20)
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Dizi kartlarını seç (NowTV yapısı: .list-item)
        cards = soup.select('.videos .list-item')
        
        for card in cards[:20]: # Test için ilk 20 dizi, hepsini istersen sınırı kaldır
            name_tag = card.select_one('.program-name strong') or card.select_one('.program-name')
            link_tag = card.find('a', href=True)
            img_tag = card.find('img')
            
            if not name_tag or not link_tag: continue
            
            title = name_tag.get_text(strip=True)
            href = link_tag['href']
            dizi_id = slugify(title)
            poster = img_tag.get('src') or img_tag.get('data-src', '')
            
            print(f"  📺 {title} taranıyor...")
            
            # Bölümler sayfasına git
            bolumler_url = (BASE_URL + href if href.startswith('/') else href).replace('/izle', '/bolumler')
            
            try:
                b_resp = scraper.get(bolumler_url, timeout=15)
                b_soup = BeautifulSoup(b_resp.text, 'html.parser')
                # NowTV bölüm kartları genellikle aynı .list-item sınıfını kullanır
                b_cards = b_soup.select('.list-item')
                
                eps = []
                for bc in b_cards[:10]: # Her diziden son 10 bölüm
                    b_link_tag = bc.find('a', href=True)
                    b_name_tag = bc.select_one('.program-name')
                    
                    if b_link_tag and "/bolum/" in b_link_tag['href']:
                        b_url = BASE_URL + b_link_tag['href'] if b_link_tag['href'].startswith('/') else b_link_tag['href']
                        b_title = b_name_tag.get_text(strip=True) if b_name_tag else "Bölüm"
                        
                        # M3U8 yakala
                        m3u8_link = get_now_m3u8(scraper, b_url)
                        eps.append({"ad": b_title, "link": m3u8_link})
                        print(f"    🔗 M3U8: {b_title[:20]}...")
                
                if eps:
                    series_data[dizi_id] = {
                        "isim": title,
                        "resim": poster if poster.startswith('http') else BASE_URL + poster, 
                        "bolumler": eps[::-1]
                    }
            except:
                continue
                
    except Exception as e:
        print(f"❌ Ana Hata: {e}")

    create_html(series_data)

def create_html(series_data):
    file_name = "nowtv_vod.html"
    json_str = json.dumps(series_data, ensure_ascii=False)
    
    html = f'''<!DOCTYPE html>
<html lang="tr">
<head>
    <title>NOW TV VOD</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://code.jquery.com/jquery-3.5.1.min.js"></script>
    <style>
        body {{ margin: 0; background: #0b0c10; color: white; font-family: sans-serif; }}
        .aramapanel {{ width: 100%; height: 70px; background: #1f2833; border-bottom: 2px solid #66fcf1; padding: 10px 20px; box-sizing: border-box; display: flex; justify-content: space-between; align-items: center; position: sticky; top: 0; z-index: 1000; }}
        .logo-area {{ font-weight: bold; color: #66fcf1; font-size: 20px; }}
        .search-area input {{ background: #0b0c10; border: 1px solid #45a29e; color: white; padding: 8px 15px; border-radius: 5px; outline: none; }}
        .filmpaneldis {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 20px; padding: 20px; }}
        .filmpanel {{ background: #1f2833; border-radius: 8px; overflow: hidden; cursor: pointer; transition: 0.3s; position: relative; border: 1px solid transparent; }}
        .filmpanel:hover {{ border-color: #66fcf1; transform: translateY(-5px); }}
        .filmresim img {{ width: 100%; aspect-ratio: 2/3; object-fit: cover; }}
        .filmisimpanel {{ padding: 10px; text-align: center; font-size: 14px; background: rgba(0,0,0,0.7); }}
        .hidden {{ display: none !important; }}
        .playerpanel {{ position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: black; z-index: 9999; display: none; }}
        . geri-btn {{ background: #45a29e; color: white; padding: 10px 20px; border: none; cursor: pointer; margin: 15px; border-radius: 5px; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="aramapanel">
        <div class="logo-area">NOW TV VOD</div>
        <div class="search-area"><input type="text" id="seriesSearch" placeholder="Dizi ara..." oninput="search()"></div>
    </div>
    <div id="diziListesiContainer" class="filmpaneldis"></div>
    <div id="bolumContainer" class="hidden"><button class="geri-btn" onclick="geriDon()">← DİZİLERE DÖN</button><div id="bolumListesi" class="filmpaneldis"></div></div>
    <div id="playerpanel" class="playerpanel"><button class="geri-btn" onclick="geriPlayer()">← KAPAT</button><div id="main-player" style="height: calc(100% - 80px);"></div></div>

    <script>
        var diziler = {json_str};
        const BRADMAX = "{BRADMAX_PLAYER}";

        function init() {{
            const c = document.getElementById("diziListesiContainer");
            Object.keys(diziler).forEach(k => {{
                const item = document.createElement("div");
                item.className = "filmpanel";
                item.innerHTML = `<div class="filmresim"><img src="${{diziler[k].resim}}"></div><div class="filmisimpanel">${{diziler[k].isim}}</div>`;
                item.onclick = () => {{
                    document.getElementById("diziListesiContainer").classList.add("hidden");
                    document.getElementById("bolumContainer").classList.remove("hidden");
                    const bl = document.getElementById("bolumListesi");
                    bl.innerHTML = "";
                    diziler[k].bolumler.forEach(e => {{
                        const bi = document.createElement("div");
                        bi.className = "filmpanel";
                        bi.innerHTML = `<div class="filmresim"><img src="${{diziler[k].resim}}"></div><div class="filmisimpanel">${{e.ad}}</div>`;
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
            $("#diziListesiContainer .filmpanel").each(function() {{
                $(this).toggle($(this).text().toLowerCase().includes(v));
            }});
        }}
        init();
    </script>
</body>
</html>'''

    with open(file_name, "w", encoding="utf-8") as f: f.write(html)
    commit_and_push(file_name)

if __name__ == "__main__":
    run_scraper()

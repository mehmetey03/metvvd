import cloudscraper
from bs4 import BeautifulSoup
import json
import time
import re
import subprocess
import os

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
        time.sleep(0.3) # Bot korumasına takılmamak için hafif gecikme
        r = scraper.get(bolum_url, timeout=10)
        # m3u8 linkini regex ile yakala
        m3u8_match = re.search(r'(https?://[^\s"\']+\.m3u8[^\s"\']*)', r.text)
        if m3u8_match:
            return m3u8_match.group(0).replace('\\/', '/')
        return bolum_url
    except:
        return bolum_url

def commit_and_push(file_name):
    print(f"\n📤 {file_name} GitHub'a gönderiliyor...")
    try:
        # Git yapılandırması
        subprocess.run(["git", "config", "--global", "user.name", "github-actions[bot]"], check=True)
        subprocess.run(["git", "config", "--global", "user.email", "github-actions[bot]@users.noreply.github.com"], check=True)
        
        # Sadece mevcut dosyayı ekle
        subprocess.run(["git", "add", file_name], check=True)
        
        # Değişiklik kontrolü
        status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout
        if status:
            subprocess.run(["git", "commit", "-m", "🔄 NOW TV Arşivi Güncellendi"], check=True)
            subprocess.run(["git", "push"], check=True)
            print("🚀 GitHub'a başarıyla yüklendi!")
        else:
            print("✨ Değişiklik yok, push atlanıyor.")
    except Exception as e:
        print(f"❌ Git Hatası: {e}")

def run_scraper():
    print("🚀 NOW TV Kapsamlı Scraper Başlatıldı...")
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
    series_data = {}
    
    try:
        resp = scraper.get(ARCHIVE_URL, timeout=20)
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Arşivdeki tüm dizileri yakala
        # .list-item sınıfı NowTV'de hem diziler hem bölümler için kullanılır
        cards = soup.select('.list-item')
        print(f"📂 Sayfada {len(cards)} öğe bulundu. Diziler ayrıştırılıyor...")

        for card in cards:
            link_tag = card.find('a', href=True)
            if not link_tag: continue
            
            # Sadece dizi ana linklerini al (bölüm veya fragman linklerini ele)
            href = link_tag['href']
            if "/izle" not in href and "/bolumler" not in href:
                # Bazı linkler doğrudan /dizi-adi şeklindedir
                if href.count('/') > 2: continue 

            title_tag = card.select_one('.program-name strong') or card.select_one('.program-name')
            if not title_tag: continue
            
            title = title_tag.get_text(strip=True)
            dizi_id = slugify(title)
            
            # Bölümler sayfasına yönlen
            bolumler_url = (BASE_URL + href if href.startswith('/') else href).split('/izle')[0].rstrip('/') + "/bolumler"

            print(f"\n📺 {title} taranıyor...")
            
            try:
                b_resp = scraper.get(bolumler_url, timeout=15)
                b_soup = BeautifulSoup(b_resp.text, 'html.parser')
                
                # 'list-item' sınıfı NowTV'de tüm bölümleri içerir
                b_cards = b_soup.select('.list-item')
                
                eps = []
                for bc in b_cards:
                    b_link = bc.find('a', href=True)
                    # Sadece gerçek bölümleri al, fragmanları (ekstra/parça) atla
                    if b_link and "/bolum/" in b_link['href']:
                        full_b_url = BASE_URL + b_link['href'] if b_link['href'].startswith('/') else b_link['href']
                        b_name_tag = bc.select_one('.program-name')
                        b_title = b_name_tag.get_text(strip=True) if b_name_tag else "Bölüm"
                        
                        # M3U8 Linkini Çek
                        m3u8 = get_now_m3u8(scraper, full_b_url)
                        
                        # Listeye ekle (Tekrar eden bölümleri m3u8'e göre engelle)
                        if not any(e['link'] == m3u8 for e in eps):
                            eps.append({"ad": b_title, "link": m3u8})
                            print(f"  ✅ {b_title}")

                if eps:
                    img = card.find('img')
                    poster = img.get('data-src') or img.get('src', '')
                    if not poster.startswith('http'): poster = BASE_URL + poster
                    
                    series_data[dizi_id] = {
                        "isim": title,
                        "resim": poster,
                        "bolumler": eps # Site zaten yeni bölümleri en üstte verir
                    }
            except Exception as e:
                print(f"  ⚠️ {title} bölümleri çekilirken hata oluştu.")

    except Exception as e:
        print(f"❌ Kritik Hata: {e}")

    create_html(series_data)

def create_html(series_data):
    file_name = "nowtv_vod.html"
    json_data = json.dumps(series_data, ensure_ascii=False)
    
    html = f'''<!DOCTYPE html>
<html lang="tr">
<head>
    <title>METV NOW TV VOD</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://code.jquery.com/jquery-3.5.1.min.js"></script>
    <style>
        body {{ margin: 0; background: #000; color: #fff; font-family: sans-serif; }}
        .header {{ background: #1a1a1a; padding: 15px; border-bottom: 2px solid #ff0055; display: flex; justify-content: space-between; align-items: center; position: sticky; top: 0; z-index: 100; }}
        .search-input {{ padding: 8px; border-radius: 5px; border: none; width: 200px; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 15px; padding: 20px; }}
        .card {{ background: #111; border-radius: 8px; overflow: hidden; cursor: pointer; border: 1px solid #333; transition: 0.2s; }}
        .card:hover {{ border-color: #ff0055; transform: translateY(-3px); }}
        .card img {{ width: 100%; aspect-ratio: 2/3; object-fit: cover; }}
        .card-name {{ padding: 8px; font-size: 12px; text-align: center; }}
        .hidden {{ display: none !important; }}
        .player-box {{ position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: #000; z-index: 1000; display: none; }}
        .btn {{ background: #ff0055; color: #fff; border: none; padding: 10px 15px; border-radius: 5px; cursor: pointer; margin: 10px; }}
    </style>
</head>
<body>
    <div class="header">
        <div style="font-weight: bold; color: #ff0055;">NOW TV VOD</div>
        <input type="text" id="search" class="search-input" placeholder="Ara..." oninput="search()">
    </div>

    <div id="mainView" class="grid"></div>
    <div id="epView" class="grid hidden"></div>

    <div id="playerView" class="player-box">
        <button class="btn" onclick="closePlayer()">✕ KAPAT</button>
        <div id="vidFrame" style="height: calc(100% - 70px);"></div>
    </div>

    <script>
        const series = {json_data};
        const BRADMAX = "{BRADMAX_PLAYER}";

        function init() {{
            const main = document.getElementById("mainView");
            Object.keys(series).forEach(id => {{
                const div = document.createElement("div");
                div.className = "card";
                div.innerHTML = `<img src="${{series[id].resim}}"><div class="card-name">${{series[id].isim}}</div>`;
                div.onclick = () => openSeries(id);
                main.appendChild(div);
            }});
        }}

        function openSeries(id) {{
            document.getElementById("mainView").classList.add("hidden");
            const epView = document.getElementById("epView");
            epView.classList.remove("hidden");
            epView.innerHTML = `<div style="grid-column: 1/-1"><button class="btn" onclick="goBack()">← GERİ</button><h3>${{series[id].isim}}</h3></div>`;
            
            series[id].bolumler.forEach(ep => {{
                const div = document.createElement("div");
                div.className = "card";
                div.innerHTML = `<img src="${{series[id].resim}}"><div class="card-name">${{ep.ad}}</div>`;
                div.onclick = () => play(ep.link);
                epView.appendChild(div);
            }});
        }}

        function play(link) {{
            document.getElementById("playerView").style.display = "block";
            let url = link.includes(".m3u8") ? BRADMAX + encodeURIComponent(link) : link;
            document.getElementById("vidFrame").innerHTML = `<iframe src="${{url}}&autoplay=true" width="100%" height="100%" frameborder="0" allowfullscreen></iframe>`;
        }}

        function closePlayer() {{
            document.getElementById("playerView").style.display = "none";
            document.getElementById("vidFrame").innerHTML = "";
        }}

        function goBack() {{
            document.getElementById("epView").classList.add("hidden");
            document.getElementById("mainView").classList.remove("hidden");
        }}

        function search() {{
            const q = document.getElementById("search").value.toLowerCase();
            document.querySelectorAll(".card").forEach(c => {{
                c.style.display = c.innerText.toLowerCase().includes(q) ? "block" : "none";
            }});
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

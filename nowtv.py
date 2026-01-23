import cloudscraper
from bs4 import BeautifulSoup
import json
import time
import re
import subprocess

# Ayarlar
BASE_URL = "https://www.nowtv.com.tr"
# NowTV tüm arşivi tek seferde çekmek için bazen query parametreleri ister, 
# ancak en güvenli yol ana sayfadan başlayıp tüm linkleri toplamaktır.
ARCHIVE_URL = "https://www.nowtv.com.tr/dizi-arsivi"
BRADMAX_PLAYER = "https://bradmax.com/client/embed-player/d9decbf0d308f4bb91825c3f3a2beb7b0aaee2f6_8493?mediaUrl="

def slugify(text):
    mapping = {'ç':'c','ğ':'g','ı':'i','ö':'o','ş':'s','ü':'u','İ':'i','I':'i'}
    text = text.lower()
    for tr, en in mapping.items(): text = text.replace(tr, en)
    return re.sub(r'[^a-z0-9]+', '-', text).strip('-')

def get_now_m3u8(scraper, bolum_url):
    try:
        time.sleep(0.5) # Banlanmamak için kısa bekleme
        r = scraper.get(bolum_url, timeout=15)
        # Sayfa içindeki m3u8 linkini ara
        m3u8_match = re.search(r'(https?://[^\s"\']+\.m3u8[^\s"\']*)', r.text)
        if m3u8_match:
            return m3u8_match.group(0).replace('\\/', '/')
        return bolum_url
    except:
        return bolum_url

def run_scraper():
    print("🚀 NOW TV Kapsamlı Scraper Başlatıldı...")
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
    series_data = {}
    
    try:
        # 1. Adım: Arşiv sayfasındaki tüm dizileri bul
        resp = scraper.get(ARCHIVE_URL, timeout=20)
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # 'Daha fazla' butonuna basılmış gibi tüm dizi linklerini topla
        # Not: NowTV bazen tüm dizileri sayfada gizli tutar veya AJAX ile getirir.
        # Bu kod mevcut sayfadaki tüm dizileri (genellikle 40-50+ dizi) çeker.
        cards = soup.select('.list-item')
        print(f"📂 Toplam {len(cards)} potansiyel dizi bulundu. İşleniyor...")

        for card in cards:
            link_tag = card.find('a', href=True)
            if not link_tag: continue
            
            href = link_tag['href']
            # Sadece dizi linklerini al
            if "/diziler/" not in href and "/izle" not in href: continue
            
            title = card.select_one('.program-name strong')
            title = title.get_text(strip=True) if title else "Dizi"
            dizi_id = slugify(title)
            img = card.find('img')
            poster = img.get('data-src') or img.get('src', '')
            if not poster.startswith('http'): poster = BASE_URL + poster

            print(f"\n📺 {title} - Tüm bölümler aranıyor...")
            
            # Bölümler sayfasına git (/bolumler kısmı tüm bölümleri içerir)
            if "/izle" in href:
                bolumler_url = (BASE_URL + href if href.startswith('/') else href).replace('/izle', '/bolumler')
            else:
                bolumler_url = (BASE_URL + href if href.startswith('/') else href).rstrip('/') + "/bolumler"

            try:
                b_resp = scraper.get(bolumler_url, timeout=15)
                b_soup = BeautifulSoup(b_resp.text, 'html.parser')
                # Sayfadaki tüm bölüm kartlarını bul
                b_cards = b_soup.select('.list-item')
                
                eps = []
                for bc in b_cards: # Sınır yok, hepsini alıyoruz
                    b_link = bc.find('a', href=True)
                    b_title_tag = bc.select_one('.program-name')
                    
                    if b_link and "/bolum/" in b_link['href']:
                        full_b_url = BASE_URL + b_link['href'] if b_link['href'].startswith('/') else b_link['href']
                        b_title = b_title_tag.get_text(strip=True) if b_title_tag else "Bölüm"
                        
                        m3u8 = get_now_m3u8(scraper, full_b_url)
                        eps.append({"ad": b_title, "link": m3u8})
                        print(f"  ✅ {b_title[:30]}")

                if eps:
                    series_data[dizi_id] = {
                        "isim": title,
                        "resim": poster,
                        "bolumler": eps[::-1] # Eskiden yeniye sırala
                    }
            except Exception as e:
                print(f"  ❌ Bölüm çekilemedi: {e}")
                
    except Exception as e:
        print(f"❌ Kritik Hata: {e}")

    create_html(series_data)

def create_html(series_data):
    file_name = "nowtv_vod.html"
    json_data = json.dumps(series_data, ensure_ascii=False)
    
    html = f'''<!DOCTYPE html>
<html lang="tr">
<head>
    <title>METV NOW TV ARŞİV</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://code.jquery.com/jquery-3.5.1.min.js"></script>
    <style>
        body {{ margin: 0; background: #000; color: #fff; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }}
        .navbar {{ position: sticky; top: 0; background: #111; padding: 15px; display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #f50057; z-index: 100; }}
        .search-box {{ padding: 8px; border-radius: 5px; border: none; width: 250px; }}
        .container {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 15px; padding: 20px; }}
        .card {{ background: #1a1a1a; border-radius: 10px; overflow: hidden; cursor: pointer; transition: 0.3s; border: 1px solid #333; }}
        .card:hover {{ transform: scale(1.05); border-color: #f50057; }}
        .card img {{ width: 100%; aspect-ratio: 2/3; object-fit: cover; }}
        .card-title {{ padding: 10px; font-size: 12px; text-align: center; font-weight: bold; }}
        .hidden {{ display: none !important; }}
        .player-overlay {{ position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: #000; z-index: 2000; display: none; }}
        .btn-back {{ background: #f50057; color: white; border: none; padding: 10px 20px; cursor: pointer; border-radius: 5px; margin: 10px; }}
    </style>
</head>
<body>
    <div class="navbar">
        <div style="font-size: 20px; color: #f50057; font-weight: bold;">NOW VOD</div>
        <input type="text" class="search-box" id="search" placeholder="Dizi/Bölüm Ara..." oninput="doSearch()">
    </div>

    <div id="mainView" class="container"></div>
    <div id="episodeView" class="container hidden"></div>
    
    <div id="playerView" class="player-overlay">
        <button class="btn-back" onclick="closePlayer()">✕ KAPAT</button>
        <div id="videoContainer" style="height: calc(100% - 70px);"></div>
    </div>

    <script>
        const data = {json_data};
        const BRADMAX = "{BRADMAX_PLAYER}";

        function init() {{
            const main = document.getElementById("mainView");
            Object.keys(data).forEach(id => {{
                const card = document.createElement("div");
                card.className = "card";
                card.innerHTML = `<img src="${{data[id].resim}}"><div class="card-title">${{data[id].isim}}</div>`;
                card.onclick = () => showEpisodes(id);
                main.appendChild(card);
            }});
        }}

        function showEpisodes(id) {{
            const epView = document.getElementById("episodeView");
            const mainView = document.getElementById("mainView");
            mainView.classList.add("hidden");
            epView.classList.remove("hidden");
            
            epView.innerHTML = `<div style="grid-column: 1/-1"><button class="btn-back" onclick="goBack()">← DİZİLERE DÖN</button><h3>${{data[id].isim}} - Tüm Bölümler</h3></div>`;
            
            data[id].bolumler.forEach(ep => {{
                const card = document.createElement("div");
                card.className = "card";
                card.innerHTML = `<img src="${{data[id].resim}}"><div class="card-title">${{ep.ad}}</div>`;
                card.onclick = () => playVideo(ep.link);
                epView.appendChild(card);
            }});
        }}

        function playVideo(link) {{
            const playerView = document.getElementById("playerView");
            const container = document.getElementById("videoContainer");
            playerView.style.display = "block";
            let finalUrl = link.includes(".m3u8") ? BRADMAX + encodeURIComponent(link) : link;
            container.innerHTML = `<iframe src="${{finalUrl}}&autoplay=true" width="100%" height="100%" frameborder="0" allowfullscreen></iframe>`;
        }}

        function closePlayer() {{
            document.getElementById("playerView").style.display = "none";
            document.getElementById("videoContainer").innerHTML = "";
        }}

        function goBack() {{
            document.getElementById("episodeView").classList.add("hidden");
            document.getElementById("mainView").classList.remove("hidden");
        }}

        function doSearch() {{
            const query = document.getElementById("search").value.toLowerCase();
            document.querySelectorAll(".card").forEach(card => {{
                card.style.display = card.innerText.toLowerCase().includes(query) ? "block" : "none";
            }});
        }}

        init();
    </script>
</body>
</html>'''

    with open(file_name, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✅ {file_name} oluşturuldu. GitHub'a gönderiliyor...")
    # commit_and_push(file_name) # Bu fonksiyonu yukarıdaki örneğinizden ekleyebilirsiniz.

if __name__ == "__main__":
    run_scraper()

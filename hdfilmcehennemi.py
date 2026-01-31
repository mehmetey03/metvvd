import requests
from bs4 import BeautifulSoup
import json
import time
import re
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from urllib.parse import urljoin

# ============================================================================
# AYARLAR VE SABİTLER
# ============================================================================
PAGES_TO_SCRAPE = int(sys.argv[1]) if len(sys.argv) > 1 else 10
BASE_URL = "https://www.hdfilmcehennemi.com"
GITHUB_JSON_URL = "https://raw.githubusercontent.com/mehmetey03/metvvd/refs/heads/main/hdfilmcehennemi.json"

HEADERS_PAGE = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": f"{BASE_URL}/",
    "X-Requested-With": "fetch",
    "Accept": "application/json",
}

MAX_WORKERS = 15
MAX_RETRIES = 2
data_lock = Lock()
session = requests.Session()

# ============================================================================
# YARDIMCI FONKSİYONLAR
# ============================================================================

def get_soup(url):
    try:
        response = session.get(url, headers=HEADERS_PAGE, timeout=10)
        if response.status_code == 200:
            return BeautifulSoup(response.content, "html.parser")
    except:
        return None
    return None

def slugify(text):
    text = text.lower()
    tr_map = str.maketrans("ığüşöç", "igusoc")
    text = text.translate(tr_map)
    text = re.sub(r'[^a-z0-9]', '-', text)
    return re.sub(r'-+', '-', text).strip('-')

def process_film_detail(film_info, filmler_data):
    """Film detay sayfasından video linkini çeker"""
    try:
        target_url = urljoin(BASE_URL, film_info['film_link'])
        soup = get_soup(target_url)
        video_url = ""
        
        if soup:
            iframe = soup.find('iframe', {'class': 'close'})
            if iframe and iframe.get('data-src'):
                ds = iframe.get('data-src')
                if "rapidrame_id=" in ds:
                    video_url = f"{BASE_URL}/rplayer/{ds.split('rapidrame_id=')[1]}"
                else:
                    video_url = ds

        film_id = slugify(film_info['film_adi'])
        with data_lock:
            filmler_data[film_id] = {
                "isim": film_info['film_adi'],
                "resim": film_info['poster_url'] or "https://via.placeholder.com/300x450",
                "link": video_url
            }
        return True
    except:
        return False

# ============================================================================
# ANA SÜREÇ
# ============================================================================

def main():
    print(f"🚀 Başlatıldı: {PAGES_TO_SCRAPE} sayfa taranıyor...")
    filmler_data = {}
    all_film_links = []

    # 1. AŞAMA: Tüm sayfalardaki film linklerini topla
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_page = {executor.submit(session.get, f"{BASE_URL}/load/page/{p}/categories/film-izle-2/", headers=HEADERS_PAGE): p for p in range(1, PAGES_TO_SCRAPE + 1)}
        
        for future in as_completed(future_to_page):
            try:
                resp = future.result()
                data = resp.json()
                soup = BeautifulSoup(data.get('html', ''), 'html.parser')
                for a in soup.find_all('a', class_='poster'):
                    img = a.find('img')
                    all_film_links.append({
                        'film_adi': a.get('title', '').strip(),
                        'film_link': a.get('href'),
                        'poster_url': (img.get('data-src') or img.get('src', '')).split('?')[0] if img else ""
                    })
            except:
                continue

    print(f"🔗 {len(all_film_links)} film linki bulundu. Detaylar çekiliyor...")

    # 2. AŞAMA: Film detaylarını paralel işle
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(process_film_detail, f, filmler_data) for f in all_film_links]
        for i, _ in enumerate(as_completed(futures)):
            if i % 20 == 0: print(f"⌛ İlerleme: %{int((i/len(all_film_links))*100)}")

    create_files(filmler_data)

def create_files(data):
    # JSON Kaydet
    with open("hdfilmcehennemi.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    # HTML Kaydet
    first_99 = dict(list(data.items())[:99])
    create_html_file(first_99, len(data))

def create_html_file(embedded_data, total_count):
    json_str = json.dumps(embedded_data, ensure_ascii=False)
    
    # Python f-string'de {{ }} kullanımı JS süslü parantezlerini korur
    html_content = f'''<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="utf-8">
    <title>ME TV FİLM VOD</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://code.jquery.com/jquery-3.5.1.min.js"></script>
    <script src="https://kit.fontawesome.com/bbe955c5ed.js" crossorigin="anonymous"></script>
    <style>
        body {{ background: #00040d; color: white; font-family: sans-serif; margin: 0; }}
        .aramapanel {{ position: sticky; top: 0; background: #15161a; padding: 10px; display: flex; justify-content: space-between; z-index: 100; border-bottom: 1px solid #323442; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 15px; padding: 20px; }}
        .card {{ background: #15161a; border-radius: 10px; overflow: hidden; border: 1px solid #323442; transition: 0.3s; cursor: pointer; }}
        .card:hover {{ border-color: #572aa7; transform: scale(1.05); }}
        .card img {{ width: 100%; height: 220px; object-fit: cover; }}
        .card-title {{ padding: 8px; font-size: 12px; text-align: center; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
        .search-input {{ background: #000; border: 1px solid #323442; color: #fff; padding: 8px; border-radius: 5px; }}
    </style>
</head>
<body>
    <div class="aramapanel">
        <div><strong>ME TV</strong></div>
        <input type="text" id="search" placeholder="Film Ara..." class="search-input" onkeyup="searchFilms(this.value)">
        <div id="stat" style="font-size:12px; color:#888;">Yükleniyor...</div>
    </div>
    
    <div class="grid" id="container"></div>

    <script>
        let localData = {json_str};
        let masterDB = {{ ...localData }};
        const remoteURL = "{GITHUB_JSON_URL}";

        function render(data) {{
            const container = document.getElementById('container');
            container.innerHTML = Object.values(data).map(film => `
                <div class="card" onclick="window.open('${{film.link}}', '_blank')">
                    <img src="${{film.resim}}" onerror="this.src='https://via.placeholder.com/300x450'">
                    <div class="card-title">${{film.isim}}</div>
                </div>
            `).join('');
        }}

        async function loadRemote() {{
            try {{
                const r = await fetch(remoteURL);
                const full = await r.json();
                masterDB = {{ ...masterDB, ...full }};
                document.getElementById('stat').innerText = Object.keys(masterDB).length + " Film Mevcut";
            }} catch(e) {{
                document.getElementById('stat').innerText = "Çevrimdışı Mod";
            }}
        }}

        function searchFilms(q) {{
            q = q.toLowerCase();
            const filtered = Object.values(masterDB).filter(f => f.isim.toLowerCase().includes(q));
            render(filtered);
        }}

        render(localData);
        loadRemote();
    </script>
</body>
</html>'''

    with open("hdfilmcehennemi.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    print("✅ Dosyalar başarıyla oluşturuldu.")

if __name__ == "__main__":
    main()

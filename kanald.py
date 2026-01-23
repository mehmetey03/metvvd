import cloudscraper
from bs4 import BeautifulSoup
import json
import time
import re
import os

BASE_URL = "https://www.kanald.com.tr"

def slugify(text):
    text = text.lower()
    tr_map = {'ı': 'i', 'ğ': 'g', 'ü': 'u', 'ş': 's', 'ö': 'o', 'ç': 'c', 'İ': 'i'}
    for tr, en in tr_map.items():
        text = text.replace(tr, en)
    text = re.sub(r'[^a-z0-9]+', '-', text)
    return text.strip('-')

def extract_episode_number(name):
    match = re.search(r'(\d+)', name)
    return int(match.group(1)) if match else 999

def get_kanald_series():
    print("🚀 Kanal D Derin Tarama Başlatıldı...")
    scraper = cloudscraper.create_scraper(
        browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True}
    )
    
    series_data = {}
    
    try:
        # Arşiv ve güncel dizileri kapsayan geniş liste
        response = scraper.get(f"{BASE_URL}/diziler", timeout=30)
        soup = BeautifulSoup(response.text, 'html.parser')
        cards = soup.select('a.poster-card, .series-card a')
        
        print(f"✅ {len(cards)} potansiyel dizi bulundu.\n")
        
        for idx, card in enumerate(cards[:20], 1): # İlk 20 diziyi tara
            href = card.get('href', '')
            if not href or 'bolum' in href: continue
            
            full_series_url = BASE_URL + href if href.startswith('/') else href
            title = card.get('title') or (card.find('img').get('alt') if card.find('img') else "Dizi")
            
            print(f"[{idx}] 📺 {title} taranıyor...")
            
            # Bölümler sekmesine direkt git
            episodes = get_series_episodes(scraper, full_series_url, title)
            
            if episodes:
                series_id = slugify(title)
                img_tag = card.find('img')
                poster = img_tag.get('data-src') or img_tag.get('src') if img_tag else ""
                
                series_data[series_id] = {
                    "resim": poster if poster.startswith('http') else "https:" + poster,
                    "bolumler": episodes
                }
                print(f"    ✨ {len(episodes)} bölüm başarıyla eklendi.")
            else:
                print(f"    ⚠️ Bölüm içeriğine ulaşılamadı.")
            
            time.sleep(1) 

        return series_data
    except Exception as e:
        print(f"❌ Ana hata: {e}")
        return {}

def get_series_episodes(scraper, series_url, series_name):
    episodes = []
    # Bölümlerin listelendiği muhtemel URL
    target_url = series_url.rstrip('/') + "/bolumler"
    
    try:
        resp = scraper.get(target_url, timeout=20)
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Kanal D'nin 'story-card' yapısını hedefle
        episode_cards = soup.select('.story-card, a[href*="/bolum/"]')
        
        for ep in episode_cards:
            ep_href = ep.get('href')
            if not ep_href: continue
            
            ep_title_tag = ep.select_one('.title') or ep
            ep_title = ep_title_tag.get_text(strip=True)
            
            if "Bölüm" in ep_title:
                full_ep_url = BASE_URL + ep_href if ep_href.startswith('/') else ep_href
                
                # Video linkini çekmeye çalış (opsiyonel, hızı artırmak için direkt sayfa linki verilebilir)
                episodes.append({
                    "ad": ep_title,
                    "link": full_ep_url, # Direkt izleme sayfası
                    "num": extract_episode_number(ep_title)
                })
        
        return sorted(episodes, key=lambda x: x['num'], reverse=True)
    except:
        return []

def create_html(data):
    # JSON verisini içine gömerek HTML oluştur
    json_data = json.dumps(data, ensure_ascii=False)
    
    # HTML şablonu (Kullanıcı arayüzü)
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8"><title>Kanal D Arşivi</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{ background: #0b0e14; color: white; font-family: sans-serif; padding: 20px; }}
            .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 20px; }}
            .card {{ background: #1a1d24; border-radius: 10px; overflow: hidden; cursor: pointer; border: 1px solid #333; }}
            .card img {{ width: 100%; height: 280px; object-fit: cover; }}
            .card-title {{ padding: 10px; text-align: center; font-weight: bold; font-size: 14px; }}
            #episodes-view {{ display: none; }}
            .ep-item {{ background: #252932; padding: 15px; margin: 5px 0; border-radius: 5px; display: block; color: #4facfe; text-decoration: none; }}
            .btn {{ background: #4facfe; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; margin-bottom: 20px; }}
        </style>
    </head>
    <body>
        <h1>📺 Kanal D Video Arşivi</h1>
        
        <div id="main-view">
            <div class="grid" id="series-grid"></div>
        </div>

        <div id="episodes-view">
            <button class="btn" onclick="showMain()">← Geri Dön</button>
            <h2 id="selected-title"></h2>
            <div id="episodes-list"></div>
        </div>

        <script>
            const data = {json_data};
            const grid = document.getElementById('series-grid');

            Object.keys(data).forEach(id => {{
                const item = data[id];
                const div = document.createElement('div');
                div.className = 'card';
                div.innerHTML = `<img src="${{item.resim}}"><div class="card-title">${{id.replace(/-/g, ' ').toUpperCase()}}</div>`;
                div.onclick = () => showEpisodes(id);
                grid.appendChild(div);
            }});

            function showEpisodes(id) {{
                document.getElementById('main-view').style.display = 'none';
                document.getElementById('episodes-view').style.display = 'block';
                document.getElementById('selected-title').innerText = id.replace(/-/g, ' ').toUpperCase();
                const list = document.getElementById('episodes-list');
                list.innerHTML = '';
                data[id].bolumler.forEach(ep => {{
                    const a = document.createElement('a');
                    a.className = 'ep-item';
                    a.href = ep.link;
                    a.target = '_blank';
                    a.innerText = ep.ad;
                    list.appendChild(a);
                }});
            }}

            function showMain() {{
                document.getElementById('main-view').style.display = 'block';
                document.getElementById('episodes-view').style.display = 'none';
            }}
        </script>
    </body>
    </html>
    """
    
    file_path = os.path.join(os.getcwd(), "kanald_archive.html")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    return file_path

if __name__ == "__main__":
    data = get_kanald_series()
    if data:
        path = create_html(data)
        print(f"\n✅ İŞLEM TAMAMLANDI!")
        print(f"📂 Dosya şurada oluşturuldu: {path}")
    else:
        print("❌ Hiç veri çekilemedi.")

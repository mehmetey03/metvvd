import cloudscraper
from bs4 import BeautifulSoup
import json
import re
import subprocess
import time

BASE_URL = "https://www.nowtv.com.tr"
AJAX_URL = "https://www.nowtv.com.tr/ajax/get_archive_programs"

def slugify(text):
    mapping = {'ç':'c','ğ':'g','ı':'i','ö':'o','ş':'s','ü':'u','İ':'i','I':'i'}
    text = text.lower()
    for tr, en in mapping.items(): text = text.replace(tr, en)
    return re.sub(r'[^a-z0-9]+', '-', text).strip('-')

def get_m3u8(scraper, url):
    try:
        r = scraper.get(url, timeout=10)
        match = re.search(r'(https?://[^\s"\']+\.m3u8[^\s"\']*)', r.text)
        return match.group(0).replace('\\/', '/') if match else url
    except: return url

def run_scraper():
    print("🚀 NOW TV Gerçek Arşiv Taraması (Ajax Mode) Başlatıldı...")
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome','platform': 'windows','desktop': True})
    
    # Sunucuyu kandırmak için gerekli kritik başlıklar
    scraper.headers.update({
        'X-Requested-With': 'XMLHttpRequest',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Referer': 'https://www.nowtv.com.tr/dizi-arsivi'
    })

    series_data = {}
    
    # Toplamda 106 içerik varsa 11-12 sayfa denemeliyiz
    for page in range(1, 13):
        print(f"📂 Sayfa {page} yükleniyor (Daha Fazla butonu simüle ediliyor)...")
        
        payload = {
            'filter': 'archive',
            'rows': '106',
            'page': str(page),
            'count': '10',
            'type': 'series',
            'orderby': 'id',
            'sorting': 'desc'
        }

        try:
            resp = scraper.post(AJAX_URL, data=payload, timeout=15)
            # NowTV Ajax yanıtı genelde JSON döner ve içinde 'html' anahtarı olur
            data_json = resp.json()
            html_chunk = data_json.get('html', '')
            
            if not html_chunk or "list-item" not in html_chunk:
                print(f"🏁 Sayfa {page}'de yeni veri yok. Bitti.")
                break
                
            soup = BeautifulSoup(html_chunk, 'html.parser')
            cards = soup.select('.list-item')
            print(f"🔎 Bu sayfada {len(cards)} yeni dizi bulundu.")

            for card in cards:
                title_tag = card.find('strong') or card.find(class_='program-name')
                link_tag = card.find('a', href=True)
                if not title_tag or not link_tag: continue

                title = title_tag.get_text(strip=True)
                dizi_id = slugify(title)
                
                if dizi_id in series_data:
                    continue # Zaten eklenmişse atla

                print(f"  🎬 {title}...")
                
                # Bölümlere git
                b_url = (BASE_URL + link_tag['href']).replace('/izle', '/bolumler')
                try:
                    b_resp = scraper.get(b_url, timeout=10)
                    b_soup = BeautifulSoup(b_resp.text, 'html.parser')
                    b_links = b_soup.find_all('a', href=re.compile(r'/bolum/'))
                    
                    eps = []
                    for bl in b_links:
                        b_title_el = bl.find_next(class_='program-name') or bl.find_next('strong')
                        b_name = b_title_el.get_text(strip=True) if b_title_el else "Bölüm"
                        
                        full_url = BASE_URL + bl['href'] if bl['href'].startswith('/') else bl['href']
                        m3u8 = get_m3u8(scraper, full_url)
                        
                        if not any(e['ad'] == b_name for e in eps):
                            eps.append({"ad": b_name, "link": m3u8})
                    
                    if eps:
                        img = card.find('img')
                        poster = img.get('src') or img.get('data-src', '')
                        if poster and not poster.startswith('http'): poster = BASE_URL + poster
                        
                        series_data[dizi_id] = {
                            "isim": title,
                            "resim": poster,
                            "bolumler": eps
                        }
                except: continue

            time.sleep(1) # Ban yememek için

        except Exception as e:
            print(f"❌ Sayfa {page} hatası: {e}")
            break

    if series_data:
        save_and_push(series_data)
    else:
        print("🚨 Maalesef veri çekilemedi. Header ayarlarını NOW TV reddediyor olabilir.")

def save_and_push(series_data):
    # HTML oluşturma ve Git işlemleri (Senin için tam stabil hale getirdim)
    file_name = "nowtv_vod.html"
    json_str = json.dumps(series_data, ensure_ascii=False)
    
    html_content = f'''<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>NOW VOD ARŞİV</title>
    <style>
        body {{ background:#000; color:#fff; font-family: sans-serif; margin:0; }}
        .nav {{ background: #111; padding: 15px; position: sticky; top:0; z-index:10; border-bottom: 2px solid red; display:flex; justify-content: space-between; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 10px; padding: 15px; }}
        .card {{ background: #1a1a1a; border-radius: 8px; overflow: hidden; cursor: pointer; border: 1px solid #333; transition: 0.2s; }}
        .card:hover {{ transform: scale(1.05); border-color: red; }}
        .card img {{ width: 100%; aspect-ratio: 2/3; object-fit: cover; }}
        .card-title {{ padding: 8px; font-size: 13px; text-align: center; font-weight: bold; }}
        .player-modal {{ position: fixed; top:0; left:0; width:100%; height:100%; background: #000; display:none; z-index: 100; }}
        .close-btn {{ position: absolute; top: 20px; right: 20px; background: red; color: #fff; border: none; padding: 10px 20px; cursor: pointer; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="nav">
        <span>NOW TV VOD ({len(series_data)} Dizi)</span>
        <input type="text" id="search" placeholder="Dizi ara..." oninput="filterList()" style="padding:5px;">
    </div>
    <div id="main-grid" class="grid"></div>
    <div id="player-modal" class="player-modal">
        <button class="close-btn" onclick="closePlayer()">KAPAT</button>
        <div id="video-container" style="width:100%; height:100%;"></div>
    </div>

    <script>
        const data = {json_str};
        function renderMain() {{
            const grid = document.getElementById('main-grid');
            grid.innerHTML = "";
            Object.keys(data).forEach(id => {{
                const item = data[id];
                const div = document.createElement('div');
                div.className = 'card';
                div.innerHTML = `<img src="${{item.resim}}"><div class="card-title">${{item.isim}}</div>`;
                div.onclick = () => renderEpisodes(id);
                grid.appendChild(div);
            }});
        }}

        function renderEpisodes(id) {{
            window.scrollTo(0,0);
            const grid = document.getElementById('main-grid');
            grid.innerHTML = `<div style="grid-column: 1/-1"><button onclick="renderMain()" style="padding:10px; margin-bottom:10px; cursor:pointer;">← ANA SAYFAYA DÖN</button><h2>${{data[id].isim}}</h2></div>`;
            data[id].bolumler.forEach(ep => {{
                const div = document.createElement('div');
                div.className = 'card';
                div.innerHTML = `<img src="${{data[id].resim}}"><div class="card-title">${{ep.ad}}</div>`;
                div.onclick = () => openPlayer(ep.link);
                grid.appendChild(div);
            }});
        }}

        function openPlayer(link) {{
            const modal = document.getElementById('player-modal');
            const container = document.getElementById('video-container');
            modal.style.display = "block";
            let finalUrl = link.includes('m3u8') ? "https://bradmax.com/client/embed-player/d9decbf0d308f4bb91825c3f3a2beb7b0aaee2f6_8493?mediaUrl=" + encodeURIComponent(link) : link;
            container.innerHTML = `<iframe src="${{finalUrl}}" width="100%" height="100%" frameborder="0" allowfullscreen></iframe>`;
        }}

        function closePlayer() {{
            document.getElementById('player-modal').style.display = "none";
            document.getElementById('video-container').innerHTML = "";
        }}

        function filterList() {{
            let q = document.getElementById('search').value.toLowerCase();
            document.querySelectorAll('.card').forEach(c => {{
                c.style.display = c.innerText.toLowerCase().includes(q) ? "" : "none";
            }});
        }}
        renderMain();
    </script>
</body>
</html>'''

    with open(file_name, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    try:
        subprocess.run(["git", "config", "--global", "user.name", "github-actions[bot]"], check=True)
        subprocess.run(["git", "config", "--global", "user.email", "github-actions[bot]@users.noreply.github.com"], check=True)
        subprocess.run(["git", "add", "nowtv_vod.html"], check=True)
        subprocess.run(["git", "commit", "-m", "🔄 TÜM ARŞİV GÜNCELLENDİ"], check=True)
        subprocess.run(["git", "push"], check=True)
        print("🚀 GitHub'a başarıyla gönderildi!")
    except Exception as e:
        print(f"❌ Git hatası: {e}")

if __name__ == "__main__":
    run_scraper()

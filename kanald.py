import cloudscraper
from bs4 import BeautifulSoup
import json
import time
import re
import os
import webbrowser

BASE_URL = "https://www.kanald.com.tr"

def slugify(text):
    mapping = {'ç':'c','ğ':'g','ı':'i','ö':'o','ş':'s','ü':'u','İ':'i'}
    text = text.lower()
    for tr, en in mapping.items(): text = text.replace(tr, en)
    return re.sub(r'[^a-z0-9]+', '-', text).strip('-')

def get_series_episodes(scraper, series_url):
    episodes = []
    target_url = series_url.rstrip('/') + "/bolumler"
    try:
        resp = scraper.get(target_url, timeout=15)
        soup = BeautifulSoup(resp.text, 'html.parser')
        # Kanal D'nin standart bölüm kartlarını yakala
        cards = soup.select('.story-card, .content-card')
        for card in cards:
            link = card.find('a', href=True) or (card if card.name == 'a' else None)
            title_tag = card.select_one('.title, h3, h2')
            if link and title_tag:
                episodes.append({
                    "ad": title_tag.get_text(strip=True),
                    "link": BASE_URL + link['href'] if link['href'].startswith('/') else link['href']
                })
        return episodes[:30] # Sayfa başına max 30 bölüm
    except: return []

def run_scraper():
    print("🚀 Kanal D Arşiv Oluşturucu Başlatıldı...")
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
    
    series_data = {}
    try:
        response = scraper.get(f"{BASE_URL}/diziler", timeout=20)
        soup = BeautifulSoup(response.text, 'html.parser')
        cards = soup.select('a.poster-card')

        for idx, card in enumerate(cards[:15], 1):
            title = card.get('title') or card.find('img').get('alt', 'Dizi')
            href = card.get('href')
            print(f"[{idx}/15] 📺 {title} taranıyor...")
            
            full_url = BASE_URL + href if href.startswith('/') else href
            eps = get_series_episodes(scraper, full_url)
            
            if eps:
                img = card.find('img')
                poster = img.get('data-src') or img.get('src', '')
                series_data[slugify(title)] = {
                    "resim": poster if poster.startswith('http') else "https:" + poster,
                    "bolumler": eps
                }
                print(f"    ✅ {len(eps)} bölüm bulundu.")
            time.sleep(0.5)

        # HTML OLUŞTURMA
        file_name = "kanald_archive.html"
        full_path = os.path.abspath(file_name)
        
        html_template = f"""
        <!DOCTYPE html>
        <html lang="tr">
        <head>
            <meta charset="UTF-8">
            <title>Kanal D Arşivi</title>
            <style>
                body {{ background: #050a12; color: white; font-family: 'Segoe UI', sans-serif; padding: 20px; }}
                .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 15px; }}
                .card {{ background: #111827; border: 1px solid #1f2937; border-radius: 8px; overflow: hidden; cursor: pointer; transition: 0.3s; }}
                .card:hover {{ transform: scale(1.05); border-color: #3b82f6; }}
                .card img {{ width: 100%; height: 250px; object-fit: cover; }}
                .card div {{ padding: 10px; font-size: 13px; text-align: center; font-weight: bold; }}
                #detail {{ display: none; background: #111827; padding: 20px; border-radius: 12px; }}
                .ep-link {{ display: block; padding: 12px; background: #1f2937; margin: 5px 0; color: #60a5fa; text-decoration: none; border-radius: 6px; }}
                .ep-link:hover {{ background: #374151; }}
                .back-btn {{ background: #3b82f6; color: white; border: none; padding: 10px 20px; border-radius: 6px; cursor: pointer; margin-bottom: 20px; }}
            </style>
        </head>
        <body>
            <h1>Kanal D Arşiv</h1>
            <div id="main-grid" class="grid"></div>
            <div id="detail">
                <button class="back-btn" onclick="location.reload()">← Geri Dön</button>
                <h2 id="det-title"></h2>
                <div id="ep-list"></div>
            </div>
            <script>
                const data = {json.dumps(series_data, ensure_ascii=False)};
                const grid = document.getElementById('main-grid');
                
                Object.keys(data).forEach(key => {{
                    const d = data[key];
                    const el = document.createElement('div');
                    el.className = 'card';
                    el.innerHTML = `<img src="${{d.resim}}"><div>${{key.replace(/-/g,' ').toUpperCase()}}</div>`;
                    el.onclick = () => {{
                        document.getElementById('main-grid').style.display = 'none';
                        document.getElementById('detail').style.display = 'block';
                        document.getElementById('det-title').innerText = key.replace(/-/g,' ').toUpperCase();
                        const list = document.getElementById('ep-list');
                        list.innerHTML = '';
                        d.bolumler.forEach(ep => {{
                            list.innerHTML += `<a href="${{ep.link}}" class="ep-link" target="_blank">${{ep.ad}}</a>`;
                        }});
                    }};
                    grid.appendChild(el);
                }});
            </script>
        </body>
        </html>
        """
        
        with open(file_name, "w", encoding="utf-8") as f:
            f.write(html_template)
        
        print(f"\n✨ BAŞARILI!")
        print(f"📂 DOSYA YOLU: {full_path}")
        
        # Dosyayı otomatik açmayı dene
        try:
            webbrowser.open('file://' + full_path)
        except:
            pass

    except Exception as e:
        print(f"❌ Hata oluştu: {e}")

if __name__ == "__main__":
    run_scraper()

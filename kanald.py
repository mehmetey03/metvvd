import cloudscraper
from bs4 import BeautifulSoup
import json
import re

def get_kanald_data():
    print("🚀 Kanal D korumalı veriler çekiliyor...")
    
    # Cloudflare ve Bot korumalarını aşmak için scraper oluştur
    scraper = cloudscraper.create_scraper()
    
    # Taranacak ana sayfalar
    urls = [
        "https://www.kanald.com.tr/diziler",
        "https://www.kanald.com.tr/programlar"
    ]
    
    series_list = []

    for url in urls:
        try:
            print(f"🔗 {url} taranıyor...")
            response = scraper.get(url, timeout=20)
            if response.status_code != 200:
                print(f"⚠️ Bağlantı sorunu: {response.status_code}")
                continue

            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Kanal D'nin kart yapıları: 'card', 'content-card' veya doğrudan <a> etiketleri
            # Genellikle tüm içerikler <a> etiketleri içinde 'card' class'ına sahiptir
            cards = soup.select('a[href*="/diziler/"], a[href*="/programlar/"]')
            
            for card in cards:
                # Başlık tespiti
                title = card.get('title') or ""
                if not title:
                    img = card.find('img')
                    title = img.get('alt') or img.get('title') if img else ""
                
                if not title or len(title) < 3 or "Tümünü Gör" in title:
                    continue

                # Link tespiti
                href = card.get('href')
                full_url = "https://www.kanald.com.tr" + href if href.startswith('/') else href
                
                # Resim tespiti
                img_tag = card.find('img')
                poster = ""
                if img_tag:
                    poster = img_tag.get('data-src') or img_tag.get('src') or ""

                series_list.append({
                    "name": title.strip(),
                    "url": full_url,
                    "resim": poster
                })
        except Exception as e:
            print(f"❌ Hata oluştu: {e}")

    # Duplikeleri temizle
    unique_data = {s['name']: s for s in series_list}.values()
    print(f"✅ {len(unique_data)} adet içerik toplandı.")
    return list(unique_data)

def create_html(data):
    json_data = json.dumps(data, ensure_ascii=False)
    html = f"""
    <!DOCTYPE html>
    <html lang="tr">
    <head>
        <meta charset="UTF-8">
        <title>Kanal D Kütüphanesi</title>
        <style>
            body {{ background: #0b0f19; color: white; font-family: sans-serif; padding: 20px; }}
            .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 20px; }}
            .item {{ background: #161d2f; border-radius: 12px; padding: 15px; text-align: center; border: 1px solid #232d45; transition: 0.3s; }}
            .item:hover {{ border-color: #3a86ff; transform: translateY(-5px); }}
            .item img {{ width: 100%; border-radius: 8px; height: 260px; object-fit: cover; margin-bottom: 10px; }}
            a {{ color: #3a86ff; text-decoration: none; font-weight: bold; }}
        </style>
    </head>
    <body>
        <h1>📺 Kanal D Arşivi</h1>
        <div class="grid" id="list"></div>
        <script>
            const data = {json_data};
            const list = document.getElementById('list');
            data.forEach(item => {{
                const div = document.createElement('div');
                div.className = 'item';
                div.innerHTML = `<img src="${{item.resim}}"><h3>${{item.name}}</h3><a href="${{item.url}}" target="_blank">DETAYLAR</a>`;
                list.appendChild(div);
            }});
        </script>
    </body>
    </html>
    """
    with open("kanald_library.html", "w", encoding="utf-8") as f:
        f.write(html)

if __name__ == "__main__":
    results = get_kanald_data()
    create_html(results)
    print("✨ kanald_library.html oluşturuldu.")

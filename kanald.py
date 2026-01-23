import cloudscraper
from bs4 import BeautifulSoup
import json

def get_kanald_data():
    print("🚀 Kanal D İçerik Kartları Taranıyor...")
    
    # Gerçek tarayıcı taklidi
    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'desktop': True
        }
    )
    
    urls = [
        "https://www.kanald.com.tr/diziler",
        "https://www.kanald.com.tr/programlar"
    ]
    
    series_list = []

    for url in urls:
        try:
            print(f"🔗 {url} kaynağından veriler okunuyor...")
            response = scraper.get(url, timeout=30)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Senin paylaştığın yapı: class="poster-card" olan <a> etiketlerini bul
            cards = soup.find_all('a', class_='poster-card')
            
            for card in cards:
                # Başlığı alt etiketinden veya href'ten al
                img_tag = card.find('img')
                title = ""
                if img_tag:
                    title = img_tag.get('alt') or img_tag.get('title')
                
                # Eğer başlık hala yoksa linkten temizle
                if not title:
                    title = card.get('href', '').replace('/', '').replace('-', ' ').title()

                # Link
                href = card.get('href', '')
                full_url = "https://www.kanald.com.tr" + href if href.startswith('/') else href
                
                # Resim (data-src veya src)
                poster = ""
                if img_tag:
                    poster = img_tag.get('data-src') or img_tag.get('src')

                if title and len(title) > 2:
                    series_list.append({
                        "name": title.strip(),
                        "url": full_url,
                        "resim": poster
                    })
        except Exception as e:
            print(f"❌ Hata: {e}")

    # Duplikeleri temizle
    unique_data = []
    seen = set()
    for item in series_list:
        if item['name'] not in seen:
            unique_data.append(item)
            seen.add(item['name'])

    print(f"✅ Toplam {len(unique_data)} adet benzersiz içerik yakalandı.")
    return unique_data

def create_html(data):
    json_data = json.dumps(data, ensure_ascii=False)
    html = f"""
    <!DOCTYPE html>
    <html lang="tr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Kanal D Arşivi</title>
        <style>
            body {{ background: #0b0f19; color: white; font-family: 'Segoe UI', sans-serif; margin: 0; padding: 20px; }}
            h1 {{ text-align: center; color: #3a86ff; margin-bottom: 30px; text-transform: uppercase; letter-spacing: 2px; }}
            .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 20px; max-width: 1200px; margin: 0 auto; }}
            .card {{ background: #161d2f; border-radius: 12px; overflow: hidden; border: 1px solid #232d45; transition: 0.3s; text-decoration: none; color: inherit; }}
            .card:hover {{ transform: translateY(-5px); border-color: #3a86ff; box-shadow: 0 10px 20px rgba(0,0,0,0.5); }}
            .img-container {{ position: relative; width: 100%; padding-top: 140%; }}
            .img-container img {{ position: absolute; top: 0; left: 0; width: 100%; height: 100%; object-fit: cover; }}
            .info {{ padding: 15px; text-align: center; }}
            .info h3 {{ margin: 0; font-size: 16px; height: 40px; overflow: hidden; display: flex; align-items: center; justify-content: center; }}
        </style>
    </head>
    <body>
        <h1>📺 Kanal D Arşivi ({len(data)} İçerik)</h1>
        <div class="grid" id="main-grid"></div>
        <script>
            const data = {json_data};
            const grid = document.getElementById('main-grid');
            data.forEach(item => {{
                const a = document.createElement('a');
                a.className = 'card';
                a.href = item.url;
                a.target = '_blank';
                a.innerHTML = `
                    <div class="img-container">
                        <img src="${{item.resim}}" loading="lazy">
                    </div>
                    <div class="info">
                        <h3>${{item.name}}</h3>
                    </div>
                `;
                grid.appendChild(a);
            }});
        </script>
    </body>
    </html>
    """
    with open("kanald_library.html", "w", encoding="utf-8") as f:
        f.write(html)

if __name__ == "__main__":
    data = get_kanald_data()
    create_html(data)

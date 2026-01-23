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
            # Kanal D bazen hızlı istekleri bloklar, timeout'u koruyoruz
            response = scraper.get(url, timeout=30)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Paylaştığın yapıdaki ana sınıf
            cards = soup.find_all('a', class_='poster-card')
            
            for card in cards:
                img_tag = card.find('img')
                title = ""
                if img_tag:
                    # data-src varsa onu al (lazy load koruması)
                    title = img_tag.get('alt') or img_tag.get('title')
                
                if not title:
                    href = card.get('href', '')
                    title = href.replace('/', '').replace('-', ' ').title()

                href = card.get('href', '')
                full_url = "https://www.kanald.com.tr" + href if href.startswith('/') else href
                
                poster = ""
                if img_tag:
                    # Sırasıyla en kaliteli resmi arıyoruz
                    poster = img_tag.get('data-src') or img_tag.get('src')
                    if poster and poster.startswith("//"):
                        poster = "https:" + poster

                if title and len(title) > 2:
                    series_list.append({
                        "name": title.strip(),
                        "url": full_url,
                        "resim": poster
                    })
        except Exception as e:
            print(f"❌ {url} taranırken hata oluştu: {e}")

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
            body {{ background: #0b0f19; color: white; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; }}
            h1 {{ text-align: center; color: #3a86ff; margin-bottom: 30px; text-transform: uppercase; letter-spacing: 2px; }}
            .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 20px; max-width: 1300px; margin: 0 auto; }}
            .card {{ background: #161d2f; border-radius: 12px; overflow: hidden; border: 1px solid #232d45; transition: 0.3s; text-decoration: none; color: inherit; display: block; }}
            .card:hover {{ transform: translateY(-8px); border-color: #3a86ff; box-shadow: 0 12px 25px rgba(0,0,0,0.6); }}
            .img-container {{ position: relative; width: 100%; padding-top: 145%; background: #05080f; }}
            .img-container img {{ position: absolute; top: 0; left: 0; width: 100%; height: 100%; object-fit: cover; }}
            .info {{ padding: 12px; text-align: center; background: linear-gradient(to top, #161d2f, transparent); }}
            .info h3 {{ margin: 0; font-size: 14px; height: 36px; overflow: hidden; display: flex; align-items: center; justify-content: center; line-height: 1.2; }}
        </style>
    </head>
    <body>
        <h1>📺 KANAL D ARŞİVİ ({len(data)} İÇERİK)</h1>
        <div class="grid" id="main-grid"></div>
        <script>
            const streamData = {json_data};
            const grid = document.getElementById('main-grid');
            streamData.forEach(item => {{
                const card = document.createElement('a');
                card.className = 'card';
                card.href = item.url;
                card.target = '_blank';
                card.innerHTML = `
                    <div class="img-container">
                        <img src="${{item.resim}}" loading="lazy" onerror="this.src='https://via.placeholder.com/264x365?text=Resim+Yok'">
                    </div>
                    <div class="info">
                        <h3>${{item.name}}</h3>
                    </div>
                `;
                grid.appendChild(card);
            }});
        </script>
    </body>
    </html>
    """
    with open("kanald_library.html", "w", encoding="utf-8") as f:
        f.write(html)

if __name__ == "__main__":
    content_data = get_kanald_data()
    if content_data:
        create_html(content_data)
        print("✨ İşlem başarılı! 'kanald_library.html' dosyasını tarayıcında açabilirsin.")
    else:
        print("❌ Hiç veri çekilemedi.")

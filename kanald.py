import cloudscraper
import json
import re

def get_kanald_data():
    print("🚀 Kanal D JSON Veri Madenciliği Başlatıldı...")
    scraper = cloudscraper.create_scraper()
    
    urls = [
        "https://www.kanald.com.tr/diziler",
        "https://www.kanald.com.tr/programlar"
    ]
    
    final_data = []

    for url in urls:
        try:
            print(f"🔗 {url} kaynağından veri sızdırılıyor...")
            response = scraper.get(url, timeout=30)
            
            # Kanal D veriyi 'window.__PRELOADED_STATE__' değişkeninde saklıyor
            # Bu regex ile sayfa içindeki dev JSON verisini buluyoruz
            match = re.search(r'window\.__PRELOADED_STATE__\s*=\s*({.*?});', response.text, re.DOTALL)
            
            if match:
                json_raw = match.group(1)
                data = json.loads(json_raw)
                
                # JSON hiyerarşisinde ilerle (Kanal D'nin güncel JSON yapısı)
                # Not: Bu yapı site değiştikçe 'items' veya 'data' olarak güncellenebilir
                categories = data.get('content', {}).get('data', [])
                
                for item in categories:
                    title = item.get('title') or item.get('name')
                    path = item.get('url')
                    img = item.get('image') or item.get('thumbnail')
                    
                    if title and path:
                        final_data.append({
                            "name": title,
                            "url": "https://www.kanald.com.tr" + path if path.startswith('/') else path,
                            "resim": img
                        })
            else:
                print(f"⚠️ {url} içinde JSON bloğu bulunamadı, klasik yönteme geçiliyor...")
                # Eğer JSON yoksa klasik HTML ayıklamaya dön
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.text, 'html.parser')
                items = soup.find_all('a', href=True)
                for i in items:
                    href = i['href']
                    if '/diziler/' in href or '/programlar/' in href:
                        t = i.get('title') or i.text.strip()
                        if len(t) > 3:
                            final_data.append({"name": t, "url": "https://www.kanald.com.tr"+href, "resim": ""})

        except Exception as e:
            print(f"❌ Hata: {e}")

    # Duplikeleri temizle
    unique = {s['name']: s for s in final_data if s['name']}.values()
    print(f"✅ Sonuç: {len(unique)} içerik bulundu.")
    return list(unique)

def create_html(data):
    json_str = json.dumps(data, ensure_ascii=False)
    html = f"""
    <!DOCTYPE html>
    <html lang="tr">
    <head><meta charset="UTF-8"><title>Kanal D Arşivi</title></head>
    <body style="background:#0b0f19; color:white; font-family:sans-serif;">
        <h1>📺 Kanal D Kütüphanesi ({len(data)} İçerik)</h1>
        <div id="app" style="display:grid; grid-template-columns:repeat(auto-fill, minmax(200px, 1fr)); gap:20px;"></div>
        <script>
            const data = {json_str};
            const app = document.getElementById('app');
            data.forEach(item => {{
                const card = document.createElement('div');
                card.style = "background:#161d2f; padding:10px; border-radius:8px; text-align:center;";
                card.innerHTML = `<img src="${{item.resim}}" style="width:100%; height:250px; object-fit:cover; border-radius:5px;">
                                  <h4>${{item.name}}</h4><a href="${{item.url}}" target="_blank" style="color:#3a86ff;">İzle</a>`;
                app.appendChild(card);
            }});
        </script>
    </body>
    </html>
    """
    with open("kanald_library.html", "w", encoding="utf-8") as f:
        f.write(html)

if __name__ == "__main__":
    d = get_kanald_data()
    create_html(d)

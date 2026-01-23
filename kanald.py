import requests
from bs4 import BeautifulSoup
import json
from urllib.parse import urljoin

BASE_URL = "https://www.kanald.com.tr"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7"
}

def get_soup(url):
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        return BeautifulSoup(response.content, "html.parser")
    except Exception as e:
        print(f"Bağlantı Hatası: {e}")
        return None

def get_all_series():
    print("🚀 Kanal D serileri taranıyor (Genişletilmiş Tarama)...")
    series_list = []
    # Gereksiz olabilecek anahtar kelimeler
    exclude = ["TÜMÜNÜ GÖR", "DİZİLER", "PROGRAMLAR", "ARŞİV", "CANLI YAYIN", "HABER", "YAYIN AKIŞI"]

    # Hem ana sayfayı hem de alt kategorileri tara
    target_paths = ['/', '/diziler', '/programlar']
    
    for path in target_paths:
        soup = get_soup(urljoin(BASE_URL, path))
        if not soup: continue
        
        # Sitedeki TÜM linkleri tara ve dizi/program olanları ayıkla
        links = soup.find_all('a', href=True)
        
        for link in links:
            href = link['href']
            # Sadece dizi veya program detayına giden linkleri al
            if '/diziler/' in href or '/programlar/' in href:
                # Başlığı bulmaya çalış (Link metni, title özniteliği veya içindeki img alt metni)
                title = link.get('title') or link.get_text(strip=True)
                
                img_tag = link.find('img')
                if not title and img_tag:
                    title = img_tag.get('alt') or img_tag.get('data-original-title')
                
                if not title or any(x in title.upper() for x in exclude) or len(title) < 3:
                    continue

                full_url = urljoin(BASE_URL, href)
                
                # Resim URL'si
                poster = ""
                if img_tag:
                    poster = img_tag.get('data-src') or img_tag.get('src') or ""

                if full_url not in [s['url'] for s in series_list]:
                    series_list.append({
                        "name": title.strip(),
                        "url": full_url,
                        "poster": urljoin(BASE_URL, poster) if poster else ""
                    })
    
    # İsme göre duplikeleri temizle
    unique_series = {s['name']: s for s in series_list}.values()
    print(f"✅ {len(unique_series)} benzersiz içerik bulundu.")
    return list(unique_series)

def create_html(data):
    json_str = json.dumps(data, ensure_ascii=False)
    html_content = f'''<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <title>Kanal D Kütüphanesi</title>
    <style>
        body {{ background: #050a12; color: #eee; font-family: sans-serif; text-align: center; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 20px; padding: 20px; }}
        .card {{ background: #121a2d; border-radius: 10px; overflow: hidden; border: 1px solid #222; transition: 0.3s; }}
        .card:hover {{ border-color: #007bff; transform: scale(1.02); }}
        .card img {{ width: 100%; height: 280px; object-fit: cover; }}
        .info {{ padding: 10px; font-weight: bold; }}
    </style>
</head>
<body>
    <h1>Kanal D İçerik Listesi</h1>
    <div id="grid" class="grid"></div>
    <script>
        const data = {json_str};
        const grid = document.getElementById('grid');
        Object.values(data).forEach(item => {{
            const d = document.createElement('div');
            d.className = 'card';
            d.innerHTML = `<img src="${{item.resim}}"><div class="info">${{item.name}}</div>`;
            grid.appendChild(d);
        }});
    </script>
</body>
</html>'''
    with open("kanald_library.html", "w", encoding="utf-8") as f:
        f.write(html_content)

if __name__ == "__main__":
    series = get_all_series()
    data_map = {s['name']: s for s in series}
    create_html(data_map)
    print("✨ İşlem tamamlandı.")

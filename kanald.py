import cloudscraper
from bs4 import BeautifulSoup
import json
import re

BASE_URL = "https://www.kanald.com.tr"

# Bot korumasını aşmak için profesyonel scraper
scraper = cloudscraper.create_scraper(
    browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True}
)

def slugify(text):
    tr_map = str.maketrans("ığüşöçİĞÜŞÖÇ", "igusoicigusoic")
    text = text.translate(tr_map).lower()
    text = re.sub(r'[^a-z0-9]', '', text)
    return text

def main():
    print("🚀 Kanal D İçerikleri Taranıyor...")
    
    # Kanal D'nin ana içerik sayfaları
    targets = [
        {"url": "/diziler", "label": "Diziler"},
        {"url": "/programlar", "label": "Programlar"}
    ]
    
    diziler_data = {}

    for target in targets:
        print(f"📍 {target['label']} sayfası taranıyor...")
        try:
            response = scraper.get(BASE_URL + target['url'], timeout=20)
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Paylaştığın HTML yapısındaki 'poster-card' class'ını hedef alıyoruz
            cards = soup.find_all("a", class_="poster-card")
            
            if not cards:
                print(f"  ⚠️ {target['label']} sayfasında kart bulunamadı (Bot koruması veya değişen yapı).")
                continue

            for card in cards:
                # Dizi adını img alt etiketinden alıyoruz
                img_tag = card.find("img")
                if not img_tag: continue
                
                dizi_adi = img_tag.get("alt", "İsimsiz İçerik").strip()
                dizi_link = BASE_URL + card.get("href", "")
                dizi_id = slugify(dizi_adi)
                
                # Afiş URL'si (Paylaştığın koddaki data-src önceliklidir)
                poster_url = img_tag.get("data-src") or img_tag.get("src") or ""
                if poster_url.startswith("//"):
                    poster_url = "https:" + poster_url

                # Veri setine ekle
                diziler_data[dizi_id] = {
                    "ad": dizi_adi,
                    "resim": poster_url,
                    "link": dizi_link,
                    "bolumler": [
                        {"ad": "Tüm Bölümler", "link": dizi_link + "/bolumler"}
                    ]
                }
                print(f"  [+] {dizi_adi} eklendi.")

        except Exception as e:
            print(f"  ❌ Hata oluştu: {e}")

    # Sonuçları kaydet
    if diziler_data:
        save_to_file(diziler_data)
        print(f"\n✨ İşlem Tamam! {len(diziler_data)} içerik kanald.html dosyasına hazırlandı.")

def save_to_file(data):
    # Veriyi Show TV projesindeki gibi JSON olarak HTML içine gömer
    json_output = json.dumps(data, ensure_ascii=False)
    html_template = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Kanal D Arşivi</title>
        <style>
            body {{ background: #0b0e14; color: white; font-family: sans-serif; padding: 20px; }}
            .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 20px; }}
            .card {{ background: #1a1d24; border-radius: 8px; overflow: hidden; transition: 0.3s; cursor: pointer; }}
            .card:hover {{ transform: scale(1.05); }}
            .card img {{ width: 100%; height: 230px; object-fit: cover; }}
            .card-title {{ padding: 10px; font-size: 13px; text-align: center; font-weight: bold; }}
        </style>
    </head>
    <body>
        <h2 style="color: #f5cf00;">Kanal D İçerikleri</h2>
        <div class="grid" id="main-grid"></div>
        <script>
            const veriler = {json_output};
            const grid = document.getElementById('main-grid');
            for (let id in veriler) {{
                const item = veriler[id];
                grid.innerHTML += `
                    <div class="card" onclick="window.open('${{item.link}}', '_blank')">
                        <img src="${{item.resim}}" alt="${{item.ad}}">
                        <div class="card-title">${{item.ad}}</div>
                    </div>
                `;
            }}
        </script>
    </body>
    </html>
    """
    with open("kanald.html", "w", encoding="utf-8") as f:
        f.write(html_template)

if __name__ == "__main__":
    main()

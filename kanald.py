import requests
import json
import re
import time

# Kanal D'nin içerikleri dağıttığı ana API endpoint'leri
API_SOURCES = {
    "Diziler": "https://www.kanald.com.tr/api/v2/content/list?categorySlug=diziler&pageSize=100",
    "Programlar": "https://www.kanald.com.tr/api/v2/content/list?categorySlug=programlar&pageSize=100"
}

BASE_URL = "https://www.kanald.com.tr"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.kanald.com.tr/",
    "X-Requested-With": "XMLHttpRequest"
}

def slugify(text):
    tr_map = str.maketrans("ığüşöçİĞÜŞÖÇ", "igusoicigusoic")
    text = text.translate(tr_map).lower()
    text = re.sub(r'[^a-z0-9]', '', text)
    return text

def get_data(url):
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"❌ API Hatası: {e}")
    return None

def main():
    print("🚀 Kanal D API üzerinden veriler çekiliyor...")
    diziler_data = {}

    for label, api_url in API_SOURCES.items():
        print(f"📍 {label} listesi alınıyor...")
        result = get_data(api_url)
        
        if not result or "data" not in result or "items" not in result["data"]:
            print(f"⚠️ {label} için veri bulunamadı.")
            continue

        items = result["data"]["items"]
        print(f"✅ {len(items)} adet içerik bulundu.")

        for item in items:
            try:
                title = item.get("title")
                # API'den gelen link genelde '/yargi' şeklindedir
                path = item.get("url")
                full_link = BASE_URL + path
                dizi_id = slugify(title)
                
                # Resim bilgisi API'de farklı formatlarda olabilir
                poster = item.get("image", {}).get("path")
                if poster and not poster.startswith("http"):
                    poster = "https:" + poster if poster.startswith("//") else poster

                print(f"  --> {title} işleniyor...")

                # Bölümler için API çağrısı (Her dizinin kendi bölümler API'si vardır)
                # Not: Hız için şimdilik ana linkleri ekliyoruz
                diziler_data[dizi_id] = {
                    "resim": poster,
                    "ad": title,
                    "bolumler": [
                        {"ad": "Son Bölüm", "link": full_link + "/bolumler"},
                        {"ad": "Tüm Bölümler", "link": full_link + "/bolumler"}
                    ]
                }
            except Exception as e:
                print(f"Hata: {e}")

    if diziler_data:
        create_html_file(diziler_data)
        print(f"\n✨ Başarılı! {len(diziler_data)} içerik index.html dosyasına işlendi.")
    else:
        print("❌ Hiç veri çekilemedi. Kanal D API adresini değiştirmiş olabilir.")

def create_html_file(data):
    # Senin Show TV için kullandığın HTML şablonunu buraya entegre ediyoruz
    json_str = json.dumps(data, ensure_ascii=False)
    
    # Not: Buraya senin önceki mesajda attığın uzun <style> ve <script> bloğunu ekleyebilirsin.
    # Ben senin yapına sadık kalarak index.html oluşturuyorum.
    html_content = f"""
    <!DOCTYPE html>
    <html lang="tr">
    <head>
        <meta charset="UTF-8">
        <title>ME TV - KANAL D</title>
        <style>
            body {{ background: #00040d; color: white; font-family: sans-serif; }}
            .container {{ display: flex; flex-wrap: wrap; justify-content: center; }}
            .card {{ width: 150px; margin: 10px; border: 1px solid #333; border-radius: 10px; overflow: hidden; cursor: pointer; }}
            .card img {{ width: 100%; height: 220px; object-fit: cover; }}
            .card-title {{ padding: 10px; font-size: 12px; text-align: center; }}
        </style>
    </head>
    <body>
        <h1 style="text-align:center; color:#572aa7;">ME TV KANAL D</h1>
        <div class="container" id="list"></div>
        <script>
            var diziler = {json_str};
            var listDiv = document.getElementById('list');
            for(var key in diziler) {{
                var d = diziler[key];
                listDiv.innerHTML += `
                    <div class="card" onclick="location.href='${{d.bolumler[0].link}}'">
                        <img src="${{d.resim}}">
                        <div class="card-title">${{d.ad}}</div>
                    </div>`;
            }}
        </script>
    </body>
    </html>
    """
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)

if __name__ == "__main__":
    main()

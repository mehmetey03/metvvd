import json
import os

def generate_nowtv_vod():
    # JSON oku
    json_path = 'nowtv_data.json'
    if not os.path.exists(json_path):
        print(f"❌ Hata: {json_path} bulunamadı!")
        return

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # HTML Şablonu
    html_content = """
    <!DOCTYPE html>
    <html lang="tr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>NOW TV - VOD</title>
        <style>
            body { background: #0a0a0a; color: white; font-family: 'Segoe UI', sans-serif; margin: 0; padding: 20px; }
            .header { border-left: 5px solid #ff0044; padding-left: 15px; margin-bottom: 30px; }
            .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 20px; }
            .movie-card { background: #1a1a1a; border-radius: 10px; overflow: hidden; transition: 0.3s; cursor: pointer; border: 1px solid #333; }
            .movie-card:hover { transform: scale(1.05); border-color: #ff0044; box-shadow: 0 0 15px rgba(255, 0, 68, 0.4); }
            .movie-card img { width: 100%; height: 280px; object-fit: cover; }
            .movie-info { padding: 12px; text-align: center; }
            .movie-title { font-weight: bold; font-size: 14px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        </style>
    </head>
    <body>
        <div class="header"><h1>NOW TV ARŞİV</h1></div>
        <div class="grid">
    """

    for key, item in data.items():
        html_content += f"""
            <div class="movie-card" onclick="window.location.href='{item['link']}'">
                <img src="{item['resim']}" alt="{item['isim']}">
                <div class="movie-info">
                    <div class="movie-title">{item['isim']}</div>
                </div>
            </div>
        """

    html_content += """
        </div>
    </body>
    </html>
    """

    # HTML Yaz
    with open('nowtv_vod.html', 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"✅ {len(data)} adet dizi tespit edildi.")
    print("🚀 nowtv_vod.html başarıyla oluşturuldu!")

if __name__ == "__main__":
    generate_nowtv_vod()

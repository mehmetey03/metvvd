import json
import re
from bs4 import BeautifulSoup
import cloudscraper # NOW TV korumasını geçmek için

def build_now_vod():
    # 1. Ham veriyi işle (Senin yukarıda paylaştığın HTML bloğu)
    raw_html = """[BURAYA PAYLAŞTIĞIN TÜM HTML METNİ GELECEK]"""
    soup = BeautifulSoup(raw_html, 'html.parser')
    items = soup.select('.list-item')
    
    series_db = {}
    scraper = cloudscraper.create_scraper()

    print(f"🚀 {len(items)} dizi tespit edildi. İşleniyor...")

    for item in items:
        try:
            name_el = item.find('strong')
            link_el = item.find('a', href=True)
            img_el = item.find('img')
            
            if not name_el: continue
            
            title = name_el.get_text(strip=True)
            slug = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')
            href = link_el['href']
            img = img_el.get('src') or img_el.get('data-src')

            # URL tamamlama
            if not href.startswith('http'): href = "https://www.nowtv.com.tr" + href
            if img and not img.startswith('http'): img = "https://www.nowtv.com.tr" + img

            # Bölüm verilerini çekmek için dizi sayfasına istek (Örnek mantık)
            # Not: Gerçek m3u8 çekimi için her dizi linkine gidip 'data-hope-video' benzeri yapıları arar.
            
            series_db[slug] = {
                "isim": title,
                "resim": img,
                "link": href,
                "bolumler": [
                    {
                        "ad": "Son Bölüm",
                        "link": href.replace("/izle", "/bolumler") # Gerçek m3u8 burada dinamik çekilmeli
                    }
                ]
            }
        except Exception as e:
            print(f"Hata: {e}")

    # 2. JSON Dosyasını Kaydet
    with open('nowtv_data.json', 'w', encoding='utf-8') as f:
        json.dump(series_db, f, ensure_ascii=False, indent=4)

    # 3. HTML Arayüzünü Oluştur (Senin verdiğin tasarım yapısında)
    generate_html(series_db)

def generate_html(data):
    json_str = json.dumps(data, ensure_ascii=False)
    
    html_content = f'''
    <!DOCTYPE html>
    <html lang="tr">
    <head>
        <title>NOW TV VOD PLAYER</title>
        <meta charset="utf-8">
        <style>
            /* Senin verdiğin CSS stilleri buraya (Show TV tarzı) */
            body {{ background: #00040d; color: white; font-family: sans-serif; }}
            .filmpanel {{ width: 180px; height: 260px; background: #15161a; float: left; margin: 10px; border-radius: 10px; overflow: hidden; cursor: pointer; border: 1px solid #323442; transition: 0.3s; }}
            .filmpanel:hover {{ border-color: #572aa7; transform: scale(1.05); }}
            .filmresim img {{ width: 100%; height: 200px; object-fit: cover; }}
            .filmisim {{ padding: 10px; font-size: 13px; text-align: center; }}
            #player-modal {{ display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: black; z-index: 9999; }}
            iframe {{ width: 100%; height: 100%; border: none; }}
            .close-btn {{ position: absolute; top: 20px; right: 20px; background: red; color: white; padding: 10px; cursor: pointer; z-index: 10001; }}
        </style>
    </head>
    <body>
        <div id="main-container"></div>
        <div id="player-modal">
            <div class="close-btn" onclick="closePlayer()">KAPAT</div>
            <div id="player-frame"></div>
        </div>

        <script>
            const data = {json_str};
            const container = document.getElementById('main-container');

            Object.keys(data).forEach(slug => {{
                const item = data[slug];
                const div = document.createElement('div');
                div.className = 'filmpanel';
                div.innerHTML = `<div class="filmresim"><img src="${{item.resim}}"></div><div class="filmisim">${{item.isim}}</div>`;
                div.onclick = () => openPlayer(item.bolumler[0].link);
                container.appendChild(div);
            }});

            function openPlayer(url) {{
                document.getElementById('player-modal').style.display = 'block';
                // Bradmax veya HLS Player entegrasyonu
                document.getElementById('player-frame').innerHTML = `<iframe src="https://bradmax.com/client/embed-player/YOUR_ID?mediaUrl=${{url}}"></iframe>`;
            }}

            function closePlayer() {{
                document.getElementById('player-modal').style.display = 'none';
                document.getElementById('player-frame').innerHTML = '';
            }}
        </script>
    </body>
    </html>
    '''
    
    with open('nowtv_vod.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    print("✅ nowtv_vod.html oluşturuldu!")

if __name__ == "__main__":
    build_now_vod()

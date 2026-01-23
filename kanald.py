import cloudscraper
from bs4 import BeautifulSoup
import json
import re

def scrape_kanald():
    scraper = cloudscraper.create_scraper()
    base_url = "https://www.kanald.com.tr"
    sources = [
        f"{base_url}/diziler",
        f"{base_url}/programlar"
    ]
    
    all_data = {}

    print("🚀 Kanal D İçerik Kartları Taranıyor...")
    
    for url in sources:
        try:
            response = scraper.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Senin bulduğun poster-card yapısı
            cards = soup.find_all('div', class_='poster-card')
            
            for card in cards:
                title_tag = card.find('span', class_='title')
                link_tag = card.find('a')
                img_tag = card.find('img', class_='lazy')
                
                if title_tag and link_tag:
                    title = title_tag.get_text(strip=True)
                    link = base_url + link_tag['href']
                    # data-src varsa onu al, yoksa src al
                    img = img_tag.get('data-src') if img_tag else ""
                    if not img and img_tag:
                        img = img_tag.get('src')
                    
                    # Başlığı ID'ye uygun hale getir (Küçük harf, boşluksuz)
                    safe_id = re.sub(r'\W+', '', title.lower())
                    
                    all_data[safe_id] = {
                        "resim": img,
                        "ad": title,
                        "bolumler": [
                            {"ad": "Tüm Bölümler", "link": link},
                            {"ad": "Son Bölüm", "link": link + "/bolumler"}
                        ]
                    }
        except Exception as e:
            print(f"❌ Hata oluştu ({url}): {e}")

    return all_data

# Verileri çek
diziler_data = scrape_kanald()

# Senin HTML Şablonun
html_content = f"""<!DOCTYPE html>
<html lang="tr">
<head>
    <title>ME TV YERLİ VOD</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, user-scalable=no, initial-scale=1.0">
    <link href="https://fonts.googleapis.com/css?family=PT+Sans:700i" rel="stylesheet">
    <script src="https://code.jquery.com/jquery-3.5.1.min.js"></script>
    <script src="https://kit.fontawesome.com/bbe955c5ed.js" crossorigin="anonymous"></script>
    <style>
        *:not(input):not(textarea) {{ -moz-user-select: none; -webkit-user-select: none; user-select: none; }}
        body {{ margin: 0; padding: 0; background: #00040d; font-family: sans-serif; font-size: 15px; font-style: italic; color: #fff; }}
        .aramapanel {{ width: 100%; height: 60px; background: #15161a; border-bottom: 1px solid #323442; padding: 10px; box-sizing: border-box; display: flex; justify-content: space-between; align-items: center; }}
        .logo {{ display: flex; align-items: center; gap: 10px; }}
        .logo img {{ width: 40px; height: 40px; }}
        .filmpaneldis {{ display: flex; flex-wrap: wrap; padding: 10px; gap: 10px; justify-content: center; }}
        .filmpanel {{ width: 140px; height: 210px; background: #15161a; border-radius: 10px; border: 1px solid #323442; overflow: hidden; position: relative; cursor: pointer; transition: 0.3s; }}
        .filmpanel:hover {{ border: 3px solid #572aa7; transform: scale(1.05); }}
        .filmresim img {{ width: 100%; height: 100%; object-fit: cover; }}
        .filmisim {{ position: absolute; bottom: 0; background: rgba(0,0,0,0.7); width: 100%; padding: 5px; font-size: 12px; text-align: center; }}
        .baslik {{ width: 100%; padding: 15px; font-size: 20px; font-weight: bold; color: #572aa7; }}
        .hidden {{ display: none; }}
        .bolum-liste-item {{ background: #15161a; margin: 5px; padding: 15px; border-radius: 5px; cursor: pointer; border: 1px solid #323442; text-align: center; }}
        .bolum-liste-item:hover {{ background: #572aa7; }}
        .geri-btn {{ background: #572aa7; color: #fff; padding: 10px 20px; border-radius: 5px; cursor: pointer; margin: 10px; display: inline-block; }}
    </style>
</head>
<body>
    <div class="aramapanel">
        <div class="logo">
            <img src="https://i.hizliresim.com/t6e66bt.png">
            <span>ME TV - KANAL D</span>
        </div>
    </div>

    <div id="anaSayfa">
        <div class="baslik">GÜNCEL İÇERİKLER ({len(diziler_data)} Adet)</div>
        <div class="filmpaneldis" id="diziListesi"></div>
    </div>

    <div id="bolumEkrani" class="hidden">
        <div class="geri-btn" onclick="anaSayfayaDon()">⬅ GERİ DÖN</div>
        <div id="bolumListesi" style="padding: 20px;"></div>
    </div>

    <script>
        var diziler = {json.dumps(diziler_data, ensure_ascii=False)};

        function listele() {{
            const container = document.getElementById('diziListesi');
            for (let id in diziler) {{
                const dizi = diziler[id];
                container.innerHTML += `
                    <div class="filmpanel" onclick="bolumleriGoster('${{id}}')">
                        <div class="filmresim"><img src="${{dizi.resim}}"></div>
                        <div class="filmisim">${{dizi.ad}}</div>
                    </div>`;
            }}
        }}

        function bolumleriGoster(id) {{
            document.getElementById('anaSayfa').classList.add('hidden');
            document.getElementById('bolumEkrani').classList.remove('hidden');
            const list = document.getElementById('bolumListesi');
            list.innerHTML = `<h2 style="color:#572aa7">${{diziler[id].ad}}</h2>`;
            diziler[id].bolumler.forEach(b => {{
                list.innerHTML += `<div class="bolum-liste-item" onclick="window.open('${{b.link}}', '_blank')">${{b.ad}}</div>`;
            }});
        }}

        function anaSayfayaDon() {{
            document.getElementById('anaSayfa').classList.remove('hidden');
            document.getElementById('bolumEkrani').classList.add('hidden');
        }}

        listele();
    </script>
</body>
</html>"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_content)

print(f"✅ Başarılı! {len(diziler_data)} içerik index.html dosyasına işlendi.")

import cloudscraper
from bs4 import BeautifulSoup
import json
import time
import re

# Kanal D kök adresi
BASE_URL = "https://www.kanald.com.tr"

# Bot korumasını aşmak için scraper
scraper = cloudscraper.create_scraper(
    browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True}
)

def get_soup(url):
    try:
        response = scraper.get(url, timeout=20)
        return BeautifulSoup(response.text, "html.parser")
    except Exception as e:
        print(f"  ❌ Hata (Bağlantı): {e}")
        return None

def slugify(text):
    tr_map = str.maketrans("ığüşöçİĞÜŞÖÇ", "igusoicigusoic")
    text = text.translate(tr_map).lower()
    text = re.sub(r'[^a-z0-9]', '', text)
    return text

def main():
    print("🚀 Kanal D Profesyonel Arşiv Tarayıcı Başlatıldı...")
    
    # Diziler ve Programlar sayfalarını tara
    targets = ["/diziler", "/programlar"]
    diziler_data = {}

    for target in targets:
        print(f"\n📍 {target[1:].upper()} listesi çekiliyor...")
        soup = get_soup(BASE_URL + target)
        if not soup: continue

        cards = soup.find_all("a", class_="poster-card")
        print(f"🔎 {len(cards)} içerik bulundu. Detaylar ve bölümler taranıyor...")

        for card in cards:
            try:
                img_tag = card.find("img")
                dizi_adi = img_tag.get("alt", "").strip() if img_tag else ""
                if not dizi_adi: continue
                
                dizi_id = slugify(dizi_adi)
                dizi_href = card.get("href", "")
                dizi_link = BASE_URL + dizi_href if dizi_href.startswith("/") else dizi_href
                poster_url = img_tag.get("data-src") or img_tag.get("src") or ""
                if poster_url.startswith("//"): poster_url = "https:" + poster_url

                print(f"  --> {dizi_adi} işleniyor...")

                # BÖLÜMLERİ ÇEKME
                bolumler = []
                # Kanal D'de bölümler genellikle /bolumler sayfasındadır
                bolum_sayfasi_url = dizi_link + "/bolumler"
                bolum_soup = get_soup(bolum_sayfasi_url)

                if bolum_soup:
                    # Bölüm kartlarını bul (genellikle poster-card veya benzeri)
                    bolum_cards = bolum_soup.find_all("a", class_="poster-card")
                    for b_card in bolum_cards:
                        b_title = b_card.find("span", class_="title")
                        b_adi = b_title.get_text(strip=True) if b_title else "Bölüm"
                        b_href = b_card.get("href", "")
                        
                        # Video sayfasının linki
                        b_video_url = BASE_URL + b_href if b_href.startswith("/") else b_href
                        
                        # KANAL D ÖZEL: Video kaynağını çekme (Genellikle iframe veya data-src içinde)
                        # Not: Kanal D'de m3u8 çekmek için video sayfasına girmek gerekir.
                        # Hız için şimdilik sayfa linkini bırakıyoruz, 
                        # Arzu edersen her bölümün içine giren derin taramayı da ekleyebiliriz.
                        bolumler.append({
                            "ad": b_adi,
                            "link": b_video_url 
                        })

                # Eğer hiç bölüm bulunamadıysa ana sayfayı ekle
                if not bolumler:
                    bolumler.append({"ad": "Tüm Bölümler", "link": dizi_link})

                diziler_data[dizi_id] = {
                    "ad": dizi_adi,
                    "resim": poster_url,
                    "bolumler": bolumler
                }
                
                time.sleep(0.2) # Sunucuyu yormayalım

            except Exception as e:
                print(f"  ⚠️ {dizi_adi} işlenirken hata: {e}")

    create_html_file(diziler_data)

def create_html_file(data):
    json_str = json.dumps(data, ensure_ascii=False)
    
    # Paylaştığın Show TV Stilindeki Template
    html_template = f'''<!DOCTYPE html>
<html lang="tr">
<head>
    <title>KANAL D ME TV VOD</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, user-scalable=no, initial-scale=1.0">
    <link href="https://fonts.googleapis.com/css?family=PT+Sans:700i" rel="stylesheet">
    <script src="https://code.jquery.com/jquery-3.5.1.min.js"></script>
    <script src="https://kit.fontawesome.com/bbe955c5ed.js" crossorigin="anonymous"></script>
    <style>
        /* Senin paylaştığın CSS kodlarının aynısı */
        body {{ margin: 0; padding: 0; background: #00040d; font-family: sans-serif; color: white; }}
        .aramapanel {{ width: 100%; height: 60px; background: #15161a; border-bottom: 1px solid #323442; padding: 10px; box-sizing: border-box; display: flex; justify-content: space-between; align-items: center; }}
        .filmpaneldis {{ padding: 20px; display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 15px; }}
        .filmpanel {{ background: #15161a; border: 1px solid #323442; border-radius: 10px; overflow: hidden; cursor: pointer; transition: 0.3s; position: relative; }}
        .filmpanel:hover {{ border-color: #572aa7; transform: translateY(-5px); }}
        .filmresim img {{ width: 100%; aspect-ratio: 2/3; object-fit: cover; }}
        .filmisimpanel {{ padding: 10px; background: linear-gradient(transparent, black); position: absolute; bottom: 0; width: 100%; }}
        .filmisim {{ font-size: 14px; text-align: center; font-weight: bold; }}
        .hidden {{ display: none; }}
        .bolum-container {{ padding: 20px; }}
        .geri-btn {{ background: #572aa7; color: white; padding: 10px 20px; border-radius: 5px; cursor: pointer; display: inline-block; margin-bottom: 20px; }}
    </style>
</head>
<body>
    <div class="aramapanel">
        <div style="display:flex; align-items:center;">
            <div style="width:40px; margin-right:10px;"><img src="https://i.hizliresim.com/t6e66bt.png" width="100%"></div>
            <div style="font-size:20px; font-weight:bold;">KANAL D VOD</div>
        </div>
    </div>

    <div class="filmpaneldis" id="diziListesiContainer"></div>

    <div id="bolumler" class="bolum-container hidden">
        <div class="geri-btn" onclick="geriDon()">← Geri Dön</div>
        <div id="bolumListesi" class="filmpaneldis"></div>
    </div>

    <script>
        var diziler = {json_str};

        function renderDiziler() {{
            const container = document.getElementById("diziListesiContainer");
            Object.keys(diziler).forEach(key => {{
                const dizi = diziler[key];
                const div = document.createElement("div");
                div.className = "filmpanel";
                div.onclick = () => showBolumler(key);
                div.innerHTML = `
                    <div class="filmresim"><img src="${{dizi.resim}}"></div>
                    <div class="filmisimpanel"><div class="filmisim">${{dizi.ad}}</div></div>
                `;
                container.appendChild(div);
            }});
        }}

        function showBolumler(id) {{
            const list = document.getElementById("bolumListesi");
            list.innerHTML = "";
            diziler[id].bolumler.forEach(b => {{
                const div = document.createElement("div");
                div.className = "filmpanel";
                div.onclick = () => window.open(b.link, "_blank");
                div.innerHTML = `
                    <div class="filmresim"><img src="${{diziler[id].resim}}"></div>
                    <div class="filmisimpanel"><div class="filmisim">${{b.ad}}</div></div>
                `;
                list.appendChild(div);
            }});
            document.getElementById("diziListesiContainer").classList.add("hidden");
            document.getElementById("bolumler").classList.remove("hidden");
        }}

        function geriDon() {{
            document.getElementById("diziListesiContainer").classList.remove("hidden");
            document.getElementById("bolumler").classList.add("hidden");
        }}

        renderDiziler();
    </script>
</body>
</html>'''
    
    with open("kanald_pro.html", "w", encoding="utf-8") as f:
        f.write(html_template)
    print("\n✨ İşlem Başarılı! 'kanald_pro.html' oluşturuldu.")

if __name__ == "__main__":
    main()

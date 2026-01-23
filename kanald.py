import requests
from bs4 import BeautifulSoup
import json
import time
import re
import os

# Web sitesi kök adresi
BASE_URL = "https://www.kanald.com.tr"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

MAX_RETRIES = 3
RETRY_DELAY = 2

def get_soup(url, retry_count=0):
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        return BeautifulSoup(response.content, "html.parser")
    except Exception as e:
        if retry_count < MAX_RETRIES:
            print(f"      ⚠ Hata: {e}. Yeniden deneniyor... ({retry_count + 1}/{MAX_RETRIES})")
            time.sleep(RETRY_DELAY)
            return get_soup(url, retry_count + 1)
        return None

def slugify(text):
    text = text.lower()
    text = text.replace('ı', 'i').replace('ğ', 'g').replace('ü', 'u').replace('ş', 's').replace('ö', 'o').replace('ç', 'c')
    text = re.sub(r'[^a-z0-9]', '', text)
    return text

def extract_episode_number(name):
    match = re.search(r'(\d+)\.\s*Bölüm', name)
    return int(match.group(1)) if match else 9999

def main():
    print("🚀 Kanal D Dizileri ve Bölümleri taranıyor...")
    
    # Diziler ve Programlar sayfalarını tara
    dizi_kaynaklari = ["/diziler", "/programlar"]
    diziler_data = {}

    for kaynak in dizi_kaynaklari:
        soup = get_soup(BASE_URL + kaynak)
        if not soup: continue

        # Kanal D'nin kart yapısı: 'poster-card'
        kutu_listesi = soup.find_all("div", class_="poster-card")
        print(f"📍 {kaynak} sayfasında {len(kutu_listesi)} içerik bulundu.")

        for kutu in kutu_listesi:
            try:
                link_tag = kutu.find("a")
                if not link_tag: continue

                dizi_adi = kutu.find("span", class_="title").text.strip()
                dizi_link = BASE_URL + link_tag.get("href")
                dizi_id = slugify(dizi_adi)
                
                img_tag = kutu.find("img")
                poster_url = img_tag.get("data-src") or img_tag.get("src")
                if poster_url and poster_url.startswith("//"): poster_url = "https:" + poster_url

                print(f"  --> İşleniyor: {dizi_adi}")

                # Bölümler sayfasına git
                detail_soup = get_soup(dizi_link + "/bolumler")
                if not detail_soup: continue

                final_bolumler = []
                # Kanal D bölüm listesi: 'sub-content-list' içindeki 'card' yapıları
                bolum_kartlari = detail_soup.select(".sub-content-list .card")
                
                for b_kutu in bolum_kartlari:
                    b_link_tag = b_kutu.find("a")
                    b_title_tag = b_kutu.find("div", class_="title")
                    
                    if b_link_tag and b_title_tag:
                        b_adi = b_title_tag.text.strip()
                        # Video linki doğrudan sayfa linkidir (Embed player içindedir)
                        b_link = BASE_URL + b_link_tag.get("href")
                        
                        final_bolumler.append({
                            "ad": b_adi,
                            "link": b_link,
                            "episode_num": extract_episode_number(b_adi)
                        })

                if final_bolumler:
                    # Eskiden yeniye sırala
                    final_bolumler = sorted(final_bolumler, key=lambda x: x['episode_num'])
                    
                    diziler_data[dizi_id] = {
                        "resim": poster_url,
                        "ad": dizi_adi, # Arayüzde düzgün görünmesi için eklendi
                        "bolumler": [{"ad": x["ad"], "link": x["link"]} for x in final_bolumler]
                    }
                    print(f"    [✓] {len(final_bolumler)} bölüm eklendi.")

            except Exception as e:
                print(f"  [!] Hata: {e}")

    create_html_file(diziler_data)

def create_html_file(data):
    json_str = json.dumps(data, ensure_ascii=False)
    
    # HTML template senin verdiğin şablonla aynı, sadece başlığı ve ID yönetimini Kanal D'ye göre güncelledim
    html_template = f'''<!DOCTYPE html>
<html lang="tr">
<head>
    <title>ME TV KANAL D VOD</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, user-scalable=no, initial-scale=1.0">
    <link href="https://fonts.googleapis.com/css?family=PT+Sans:700i" rel="stylesheet">
    <script src="https://code.jquery.com/jquery-3.5.1.min.js"></script>
    <script src="https://kit.fontawesome.com/bbe955c5ed.js" crossorigin="anonymous"></script>
    <style>
        /* Senin verdiğin CSS stilleri buraya gelecek */
        *:not(input):not(textarea) {{ -webkit-user-select: none; user-select: none; }}
        body {{ margin: 0; padding: 0; background: #00040d; font-family: sans-serif; font-style: italic; color: #fff; }}
        .filmpaneldis {{ background: #15161a; width: 100%; padding: 10px; display: flex; flex-wrap: wrap; justify-content: center; }}
        .filmpanel {{ width: 140px; height: 210px; background: #15161a; margin: 10px; border-radius: 10px; border: 1px solid #323442; overflow: hidden; cursor: pointer; transition: 0.3s; }}
        .filmpanel:hover {{ border: 3px solid #572aa7; transform: scale(1.05); }}
        .filmresim img {{ width: 100%; height: 100%; object-fit: cover; }}
        .filmisim {{ padding: 5px; font-size: 12px; text-align: center; background: rgba(0,0,0,0.8); position: absolute; bottom: 0; width: 100%; }}
        .hidden {{ display: none; }}
        .aramapanel {{ width: 100%; height: 60px; background: #15161a; border-bottom: 1px solid #323442; padding: 10px; display: flex; align-items: center; }}
        .logo {{ width: 40px; height: 40px; margin-right: 10px; }}
        .geri-btn {{ background: #572aa7; color: #white; padding: 10px; border-radius: 5px; cursor: pointer; margin: 10px; display: inline-block; }}
    </style>
</head>
<body>
    <div class="aramapanel">
        <img src="https://i.hizliresim.com/t6e66bt.png" class="logo">
        <div class="logoisim">ME TV - KANAL D</div>
    </div>

    <div id="anaSayfa">
        <div id="diziListesi" class="filmpaneldis"></div>
    </div>

    <div id="bolumEkrani" class="hidden">
        <div class="geri-btn" onclick="anaSayfayaDon()">⬅ GERİ DÖN</div>
        <div id="bolumListesi" class="filmpaneldis"></div>
    </div>

    <script>
        var diziler = {json_str};

        function init() {{
            const container = document.getElementById('diziListesi');
            for (let id in diziler) {{
                const dizi = diziler[id];
                const div = document.createElement('div');
                div.className = 'filmpanel';
                div.onclick = () => showBolumler(id);
                div.innerHTML = `<div class="filmresim" style="position:relative;height:100%"><img src="${{dizi.resim}}"><div class="filmisim">${{dizi.ad}}</div></div>`;
                container.appendChild(div);
            }}
        }}

        function showBolumler(id) {{
            document.getElementById('anaSayfa').classList.add('hidden');
            document.getElementById('bolumEkrani').classList.remove('hidden');
            const list = document.getElementById('bolumListesi');
            list.innerHTML = '';
            diziler[id].bolumler.forEach(b => {{
                const item = document.createElement('div');
                item.className = 'filmpanel';
                item.onclick = () => window.open(b.link, '_blank');
                item.innerHTML = `<div class="filmresim" style="position:relative;height:100%"><img src="${{diziler[id].resim}}"><div class="filmisim">${{b.ad}}</div></div>`;
                list.appendChild(item);
            }});
        }}

        function anaSayfayaDon() {{
            document.getElementById('anaSayfa').classList.remove('hidden');
            document.getElementById('bolumEkrani').classList.add('hidden');
        }}

        init();
    </script>
</body>
</html>'''

    with open("kanald.html", "w", encoding="utf-8") as f:
        f.write(html_template)
    print(f"\n✅ İşlem Tamam! kanald.html oluşturuldu.")

if __name__ == "__main__":
    main()

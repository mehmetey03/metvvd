import requests
from bs4 import BeautifulSoup
import json
import time
import re

BASE_URL = "https://www.showtv.com.tr"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7"
}

MAX_RETRIES = 5
RETRY_DELAY = 2


def get_soup(url, retry_count=0, is_json=False):
    """URL'den BeautifulSoup veya JSON döndürür. Timeout hatalarında yeniden dener."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=20)
        response.raise_for_status()
        if is_json:
            return response.json()
        return BeautifulSoup(response.content, "html.parser")
    except requests.exceptions.Timeout:
        if retry_count < MAX_RETRIES:
            print(f"      ⚠ Timeout hatası! Yeniden deneniyor... ({retry_count + 1}/{MAX_RETRIES})")
            time.sleep(RETRY_DELAY)
            return get_soup(url, retry_count + 1, is_json)
        print(f"      ✗ Maksimum deneme sayısına ulaşıldı. URL atlanıyor: {url}")
        return None
    except Exception as e:
        if retry_count < MAX_RETRIES:
            print(f"      ⚠ Hata: {e}. Yeniden deneniyor... ({retry_count + 1}/{MAX_RETRIES})")
            time.sleep(RETRY_DELAY)
            return get_soup(url, retry_count + 1, is_json)
        print(f"      ✗ Maksimum deneme sayısına ulaşıldı. Hata: {e}")
        return None


def slugify(text):
    text = text.lower()
    text = (text.replace('ı', 'i').replace('ğ', 'g').replace('ü', 'u')
                .replace('ş', 's').replace('ö', 'o').replace('ç', 'c'))
    text = re.sub(r'[^a-z0-9]', '', text)
    return text


def extract_episode_number(name):
    match = re.search(r'(\d+)\.\s*Bölüm', name)
    if match:
        return int(match.group(1))
    return 9999


def extract_episode_number_only(name):
    match = re.search(r'(\d+)\.\s*Bölüm', name)
    if match:
        return f"{match.group(1)}. Bölüm"
    match = re.search(r'Bölüm\s*(\d+)', name, re.IGNORECASE)
    if match:
        return f"{match.group(1)}. Bölüm"
    match = re.search(r'(\d+)\s*Bölüm', name, re.IGNORECASE)
    if match:
        return f"{match.group(1)}. Bölüm"
    return name


def get_image_url(img_tag):
    """Resim URL'sini en güvenilir yerden bulur."""
    if not img_tag:
        return ""
    
    # 1. src
    src = img_tag.get("src")
    if src and not src.startswith("data:") and "placeholder" not in src and "resimyok" not in src.lower():
        return src.split("?")[0]

    # 2. data-src
    data_src = img_tag.get("data-src")
    if data_src and not data_src.startswith("data:"):
        return data_src.split("?")[0]

    # 3. srcset (ilk URL'yi al)
    srcset = img_tag.get("srcset")
    if srcset:
        first_url = srcset.split(",")[0].strip().split(" ")[0]
        if first_url and not first_url.startswith("data:"):
            return first_url.split("?")[0]

    return ""


def find_series_cards(soup):
    results = {}
    for card in soup.select("div[data-box='type1']"):
        a = card.select_one("a[href^='/dizi/tanitim/']")
        if not a: continue
        href = a.get("href")
        if not href: continue

        title = a.get("title")
        if not title:
            span = card.select_one("figcaption span")
            if span: title = span.get_text(strip=True)
        if not title:
            img = a.find("img")
            if img: title = img.get("alt")
        if not title:
            title = href.strip("/").split("/")[-2].replace("-", " ").title()

        img_tag = a.find("img")
        poster = get_image_url(img_tag)

        if href not in results:
            results[href] = {"title": title.strip(), "poster": poster}
    return results


def load_all_series():
    """Tüm dizi listesini (ilk sayfa + AJAX) yükler."""
    print("Dizi listesi yükleniyor...")
    soup = get_soup(f"{BASE_URL}/diziler")
    if not soup: return {}

    all_series = find_series_cards(soup)
    print(f"İlk sayfadan {len(all_series)} dizi alındı.")
    
    # Daha fazla göster butonunu bul (sayfa numarası)
    load_more_btn = soup.find("button", attrs={"data-load-more": True})
    if not load_more_btn:
        print("Sayfalama butonu bulunamadı, sadece ilk sayfa alındı.")
        return all_series
        
    endpoint = load_more_btn.get("data-endpoint", "/diziler/daha-fazla")
    page = int(load_more_btn.get("data-page", "2"))
    batch = int(load_more_btn.get("data-batch", "12"))
    
    print(f"Sayfalama başlıyor: {endpoint}, sayfa boyutu: {batch}")
    
    while True:
        ajax_url = f"{BASE_URL}{endpoint}?page={page}"
        # Gerekirse JSON isteği ile çek, genelde HTML döner
        ajax_soup = get_soup(ajax_url)
        if not ajax_soup:
            break
            
        new_series = find_series_cards(ajax_soup)
        if not new_series:
            print("Yeni dizi bulunamadı. Sayfalama bitti.")
            break
            
        added = 0
        for href, info in new_series.items():
            if href not in all_series:
                all_series[href] = info
                added += 1
                
        print(f"Sayfa {page} işlendi. {added} yeni dizi eklendi. Toplam: {len(all_series)}")
        
        if added == 0:
            print("Yeni dizi gelmediği için döngü kırıldı.")
            break
            
        page += 1
        time.sleep(0.5) # Sunucuya nazik davran
    
    return all_series


def main():
    print("Diziler ve Bölümler taranıyor... (MP4 & M3U8 + Otomatik Yeniden Deneme)")

    series = load_all_series()
    
    if not series:
        print("Hiç dizi bulunamadı!")
        create_html_file({})
        return

    diziler_data = {}

    for dizi_href, info in series.items():
        try:
            dizi_link = BASE_URL + dizi_href if dizi_href.startswith("/") else dizi_href
            dizi_adi = info["title"]
            dizi_id = slugify(dizi_adi)
            poster_url = info["poster"]

            if not dizi_adi or not dizi_id:
                continue

            print(f"\n--> İşleniyor: {dizi_adi}")

            detail_soup = get_soup(dizi_link)
            if not detail_soup:
                print(f"    [✗] Detay sayfası yüklenemedi, atlanıyor.")
                continue

            # Detay sayfasından daha iyi bir poster varsa onu kullan
            og = detail_soup.find("meta", property="og:image")
            if og and og.get("content") and "showtv_social_media" not in og["content"]:
                poster_url = og["content"].split("?")[0]

            raw_links = []
            seen_urls = set()

            # 1) Dropdown seçenekleri
            for opt in detail_soup.find_all("option", attrs={"data-href": True}):
                rel_link = opt.get("data-href")
                bolum_adi = opt.text.strip()
                if rel_link and "/tum_bolumler/" in rel_link:
                    full = BASE_URL + rel_link if rel_link.startswith("/") else rel_link
                    if full not in seen_urls:
                        raw_links.append({"ad": bolum_adi, "page_url": full})
                        seen_urls.add(full)

            # 2) Detay sayfasındaki doğrudan bölüm linkleri
            for a in detail_soup.select("a[href*='/tum_bolumler/']"):
                href = a.get("href")
                if not href: continue
                full = BASE_URL + href if href.startswith("/") else href
                if full in seen_urls: continue
                name = a.get("title") or a.get_text(strip=True) or "Bölüm"
                raw_links.append({"ad": name, "page_url": full})
                seen_urls.add(full)

            print(f"    [i] {len(raw_links)} adet bölüm linki bulundu. Videolar çekiliyor...")

            final_bolumler = []

            for idx, item in enumerate(raw_links, 1):
                print(f"    [{idx}/{len(raw_links)}] {item['ad'][:50]}...")

                video_soup = get_soup(item["page_url"])
                if not video_soup:
                    print(f"      [✗] Sayfa yüklenemedi, atlanıyor.")
                    continue

                page_title = video_soup.title.string if video_soup.title else item["ad"]
                clean_name = (page_title or "").replace("İzle", "").replace("Show TV", "").strip()
                display_name = clean_name if "Bölüm" in clean_name else item["ad"]
                episode_only = extract_episode_number_only(display_name)

                video_div = video_soup.find("div", class_="hope-video")
                if video_div and video_div.get("data-hope-video"):
                    try:
                        v_data = json.loads(video_div.get("data-hope-video"))
                        video_url = ""
                        fmt = ""
                        if "media" in v_data:
                            media = v_data["media"]
                            if "m3u8" in media and len(media["m3u8"]) > 0:
                                video_url = media["m3u8"][0]["src"]
                                fmt = "M3U8"
                            elif "mp4" in media and len(media["mp4"]) > 0:
                                video_url = media["mp4"][0]["src"]
                                fmt = "MP4"
                        if video_url:
                            video_url = video_url.replace("//ht/", "/ht/").replace("com//", "com/")
                            final_bolumler.append({
                                "ad": episode_only,
                                "link": video_url,
                                "episode_num": extract_episode_number(display_name)
                            })
                            print(f"      [✓] {episode_only} [{fmt}]")
                        else:
                            print(f"      [✗] Video kaynağı yok.")
                    except Exception as e:
                        print(f"      [!] JSON hatası: {e}")

                time.sleep(0.1)

            if final_bolumler:
                final_bolumler.sort(key=lambda x: x["episode_num"])
                cleaned = [{"ad": x["ad"], "link": x["link"]} for x in final_bolumler]
                diziler_data[dizi_id] = {
                    "isim": dizi_adi,
                    "resim": poster_url,
                    "bolumler": cleaned,
                }
                print(f"    [✓] {len(cleaned)} bölüm eklendi.\n")
            else:
                print(f"    [✗] Hiç bölüm bulunamadı.\n")

        except Exception as e:
            print(f"[HATA] {dizi_adi}: {e}\n")

    print("\n" + "=" * 50)
    print(f"Toplam {len(diziler_data)} dizi başarıyla işlendi!")
    print("=" * 50)

    create_html_file(diziler_data)


def create_html_file(data):
    json_str = json.dumps(data, ensure_ascii=False)

    html_template = '''<!DOCTYPE html>
<html lang="tr">
<head>
    <title>ME TV YERLİ VOD</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, user-scalable=no, initial-scale=1.0">
    <link href="https://fonts.googleapis.com/css?family=PT+Sans:700i" rel="stylesheet">
    <script src="https://code.jquery.com/jquery-3.5.1.min.js"></script>
    <script src="https://kit.fontawesome.com/bbe955c5ed.js" crossorigin="anonymous"></script>
    <script src="https://cdn.jsdelivr.net/npm/@splidejs/splide@4.1.4/dist/js/splide.min.js"></script>
    <style>
        *:not(input):not(textarea) {
            -moz-user-select: -moz-none;
            -khtml-user-select: none;
            -webkit-user-select: none;
            -o-user-select: none;
            -ms-user-select: none;
            user-select: none
        }
        body {
            margin: 0; padding: 0; background: #00040d; font-family: sans-serif;
            font-size: 15px; -webkit-tap-highlight-color: transparent; font-style: italic;
            line-height: 20px; -webkit-text-size-adjust: 100%; overflow-x: hidden;
        }
        .filmpaneldis { background: #15161a; width: 100%; margin: 20px auto; overflow: hidden; padding: 10px 5px; box-sizing: border-box; }
        .baslik { width: 96%; color: #fff; padding: 15px 10px; box-sizing: border-box; }
        .filmpanel { width: 12%; height: 200px; background: #15161a; float: left; margin: 1.14%;
            color: #fff; border-radius: 15px; box-sizing: border-box;
            box-shadow: 1px 5px 10px rgba(0,0,0,0.1); border: 1px solid #323442; padding: 0px;
            overflow: hidden; transition: border 0.3s ease, box-shadow 0.3s ease; cursor: pointer; }
        .filmisimpanel { width: 100%; height: 200px; position: relative; margin-top: -200px;
            background: linear-gradient(to bottom, rgba(0,0,0,0) 0%, rgba(0,0,0,1) 100%); }
        .filmpanel:hover { color: #fff; border: 3px solid #572aa7; box-shadow: 0 0 10px rgba(87,42,167,0.5); }
        .filmresim { width: 100%; height: 100%; margin-bottom: 0px; overflow: hidden; position: relative; }
        .filmresim img { width: 100%; height: 100%; transition: transform 0.4s ease; object-fit: cover; }
        .filmpanel:hover .filmresim img { transform: scale(1.1); }
        .filmisim { width: 100%; font-size: 14px; text-decoration: none; white-space: nowrap;
            overflow: hidden; text-overflow: ellipsis; padding: 0px 5px; box-sizing: border-box;
            color: #fff; position: absolute; bottom: 5px; }
        .aramapanel { width: 100%; height: 60px; background: #15161a; border-bottom: 1px solid #323442;
            margin: 0px auto; padding: 10px; box-sizing: border-box; overflow: hidden; z-index: 11111; }
        .aramapanelsag { width: auto; height: 40px; box-sizing: border-box; overflow: hidden; float: right; }
        .aramapanelsol { width: 50%; height: 40px; box-sizing: border-box; overflow: hidden; float: left; }
        .aramapanelyazi { height: 40px; width: 120px; border: 1px solid #ccc; box-sizing: border-box;
            padding: 0px 10px; color: #000; margin: 0px 5px; }
        .aramapanelbuton { height: 40px; width: 40px; text-align: center; background-color: #572aa7;
            border: none; color: #fff; box-sizing: border-box; overflow: hidden; float: right; transition: .35s; }
        .aramapanelbuton:hover { background-color: #fff; color: #000; }
        .logo { width: 40px; height: 40px; float: left; }
        .logo img { width: 100%; }
        .logoisim { font-size: 15px; width: 70%; height: 40px; line-height: 40px; font-weight: 500; color: #fff; }
        .hidden { display: none; }
        .bolum-container { background: #15161a; padding: 10px; margin-top: 10px; border-radius: 5px; }
        .geri-btn { background: #572aa7; color: white; padding: 10px; text-align: center;
            border-radius: 5px; cursor: pointer; margin-top: 10px; margin-bottom: 10px;
            display: none; width: 100px; }
        .geri-btn:hover { background: #6b3ec7; transition: background 0.3s; }
        .playerpanel { width: 100%; height: 100vh; position: fixed; top: 0; left: 0;
            background: #0a0e17; z-index: 9999; display: none; flex-direction: column; overflow: hidden; }
        #main-player { width: 100%; height: 100%; background: #000; }
        #bradmax-iframe { width: 100%; height: 100%; border: none; }
        .player-geri-btn { background: #572aa7; color: white; padding: 10px; text-align: center;
            border-radius: 5px; cursor: pointer; margin: 10px; width: 100px; position: absolute;
            top: 10px; left: 10px; z-index: 10000; }
        .hataekran i { color: #572aa7; font-size: 80px; text-align: center; width: 100%; }
        .hataekran { width: 80%; margin: 20px auto; color: #fff; background: #15161a;
            border: 1px solid #323442; padding: 10px; box-sizing: border-box; border-radius: 10px; }
        .hatayazi { color: #fff; font-size: 15px; text-align: center; width: 100%; margin: 20px 0px; }
        @media(max-width:550px) {
            .filmpanel { width: 31.33%; height: 190px; margin: 1%; }
            #main-player { height: 100%; }
        }
    </style>
</head>
<body>
    <div class="aramapanel">
        <div class="aramapanelsol">
            <div class="logo"><img src="https://i.hizliresim.com/t6e66bt.png"></div>
            <div class="logoisim">ME TV</div>
        </div>
        <div class="aramapanelsag">
            <form action="" name="ara" method="GET" onsubmit="return searchSeries()">
                <input type="text" id="seriesSearch" placeholder="Dizi Adını Giriniz..!" class="aramapanelyazi" oninput="resetSeriesSearch()">
                <input type="submit" value="ARA" class="aramapanelbuton">
            </form>
        </div>
    </div>

    <div class="filmpaneldis" id="diziListesiContainer">
        <div class="baslik">SHOWTV DİZİLERİ</div>
    </div>

    <div id="bolumler" class="bolum-container hidden">
        <div id="geriBtn" class="geri-btn" onclick="geriDon()">Geri</div>
        <div id="bolumListesi" class="filmpaneldis"></div>
    </div>

    <div id="playerpanel" class="playerpanel">
        <div class="player-geri-btn" onclick="geriPlayer()">Geri</div>
        <div id="main-player"></div>
    </div>

    <script>
        const BRADMAX_BASE_URL = "https://bradmax.com/client/embed-player/d9decbf0d308f4bb91825c3f3a2beb7b0aaee2f6_8493?mediaUrl=";
        const BRADMAX_PARAMS = "&autoplay=true&fs=true";

        var diziler = ''' + json_str + ''';

        document.addEventListener('DOMContentLoaded', function() {
            var container = document.getElementById("diziListesiContainer");
            Object.keys(diziler).forEach(function(key) {
                var dizi = diziler[key];
                var item = document.createElement("div");
                item.className = "filmpanel";
                item.onclick = function() { showBolumler(key); };
                var displayName = (dizi.isim || key).toUpperCase();
                
                // Resim yoksa placeholder
                var imgUrl = dizi.resim || "";
                var imgTag = imgUrl ? `<img src="${imgUrl}" onerror="this.onerror=null;this.src='https://via.placeholder.com/300x450?text=Resim+Yok';">` : `<div style="display:flex; align-items:center; justify-content:center; height:100%; background:#2a2a2a; color:#888;">Resim Yok</div>`;
                
                item.innerHTML = `
                    <div class="filmresim">${imgTag}</div>
                    <div class="filmisimpanel">
                        <div class="filmisim">${displayName}</div>
                    </div>
                `;
                container.appendChild(item);
            });
        });

        function showBolumler(diziID) {
            sessionStorage.setItem('currentDiziID', diziID);
            var listContainer = document.getElementById("bolumListesi");
            listContainer.innerHTML = "";
            if (diziler[diziID]) {
                diziler[diziID].bolumler.forEach(function(bolum) {
                    var item = document.createElement("div");
                    item.className = "filmpanel";
                    var imgUrl = diziler[diziID].resim || "";
                    var imgTag = imgUrl ? `<img src="${imgUrl}" onerror="this.onerror=null;this.src='https://via.placeholder.com/300x450?text=Resim+Yok';">` : `<div style="display:flex; align-items:center; justify-content:center; height:100%; background:#2a2a2a; color:#888;">Resim Yok</div>`;
                    
                    item.innerHTML = `
                        <div class="filmresim">${imgTag}</div>
                        <div class="filmisimpanel">
                            <div class="filmisim">${bolum.ad}</div>
                        </div>
                    `;
                    item.onclick = function() { showPlayer(bolum.link, diziID); };
                    listContainer.appendChild(item);
                });
            }
            document.querySelector("#diziListesiContainer").classList.add("hidden");
            document.getElementById("bolumler").classList.remove("hidden");
            document.getElementById("geriBtn").style.display = "block";
        }

        function showPlayer(streamUrl) {
            document.getElementById("playerpanel").style.display = "flex";
            document.getElementById("bolumler").classList.add("hidden");
            document.getElementById("main-player").innerHTML = "";
            const fullUrl = BRADMAX_BASE_URL + encodeURIComponent(streamUrl) + BRADMAX_PARAMS;
            document.getElementById("main-player").innerHTML =
                `<iframe id="bradmax-iframe" src="${fullUrl}" allowfullscreen tabindex="0" autofocus></iframe>`;
        }

        function geriPlayer() {
            document.getElementById("playerpanel").style.display = "none";
            document.getElementById("bolumler").classList.remove("hidden");
            document.getElementById("main-player").innerHTML = "";
        }

        function geriDon() {
            sessionStorage.removeItem('currentDiziID');
            document.querySelector("#diziListesiContainer").classList.remove("hidden");
            document.getElementById("bolumler").classList.add("hidden");
            document.getElementById("geriBtn").style.display = "none";
        }

        function searchSeries() {
            var term = document.getElementById('seriesSearch').value.toLowerCase();
            var container = document.getElementById('diziListesiContainer');
            var panels = container.querySelectorAll('.filmpanel');
            var found = false;
            panels.forEach(function(panel) {
                var name = panel.querySelector('.filmisim').textContent.toLowerCase();
                if (name.includes(term)) { panel.style.display = 'block'; found = true; }
                else { panel.style.display = 'none'; }
            });
            var old = container.querySelector('.hataekran');
            if (old) old.remove();
            if (!found) {
                var no = document.createElement('div');
                no.className = 'hataekran';
                no.innerHTML = '<i class="fas fa-search"></i><div class="hatayazi">Sonuç bulunamadı!</div>';
                container.appendChild(no);
            }
            return false;
        }

        function resetSeriesSearch() {
            var container = document.getElementById('diziListesiContainer');
            container.querySelectorAll('.filmpanel').forEach(p => p.style.display = 'block');
            var no = container.querySelector('.hataekran');
            if (no) no.remove();
        }
    </script>
</body>
</html>'''

    with open("showtv.html", "w", encoding="utf-8") as f:
        f.write(html_template)

    print("HTML dosyası 'showtv.html' oluşturuldu!")


if __name__ == "__main__":
    main()

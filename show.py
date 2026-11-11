import requests
from bs4 import BeautifulSoup
import json
import time
import re

# Web sitesi kök adresi
BASE_URL = "https://www.showtv.com.tr"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

MAX_RETRIES = 5
RETRY_DELAY = 2


def get_soup(url, retry_count=0):
    """URL'den BeautifulSoup nesnesi döndürür. Timeout hatalarında yeniden dener."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        return BeautifulSoup(response.content, "html.parser")
    except requests.exceptions.Timeout:
        if retry_count < MAX_RETRIES:
            print(f"      ⚠ Timeout hatası! Yeniden deneniyor... ({retry_count + 1}/{MAX_RETRIES})")
            time.sleep(RETRY_DELAY)
            return get_soup(url, retry_count + 1)
        else:
            print(f"      ✗ Maksimum deneme sayısına ulaşıldı. URL atlanıyor: {url}")
            return None
    except Exception as e:
        if retry_count < MAX_RETRIES:
            print(f"      ⚠ Hata: {e}. Yeniden deneniyor... ({retry_count + 1}/{MAX_RETRIES})")
            time.sleep(RETRY_DELAY)
            return get_soup(url, retry_count + 1)
        else:
            print(f"      ✗ Maksimum deneme sayısına ulaşıldı. Hata: {e}")
            return None


def slugify(text):
    """Metni ID olarak kullanılabilecek formata çevirir"""
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
    """Resim etiketinden en iyi URL'yi çıkarır (src, data-src, srcset)."""
    if not img_tag:
        return ""
    
    # 1. src
    src = img_tag.get("src")
    if src and not src.startswith("data:") and "placeholder" not in src:
        return src.split("?")[0]

    # 2. data-src
    data_src = img_tag.get("data-src")
    if data_src and not data_src.startswith("data:"):
        return data_src.split("?")[0]

    # 3. srcset (ilk URL'yi al)
    srcset = img_tag.get("srcset")
    if srcset:
        first_url = srcset.split(",")[0].strip().split(" ")[0]
        if not first_url.startswith("data:"):
            return first_url.split("?")[0]

    return ""


def find_series_links(soup):
    """Yeni tasarımda dizi kartlarını a[href^='/dizi/tanitim/'] üzerinden bulur."""
    results = {}
    
    for a in soup.select("a[href^='/dizi/tanitim/']"):
        href = a.get("href")
        if not href:
            continue
            
        # Dizi adını çek: 1) title, 2) alt (img), 3) iç metin
        title = a.get("title")
        if not title:
            img = a.find("img")
            if img:
                title = img.get("alt")
        if not title:
            title = a.get_text(strip=True)
            
        # Eğer hala boşsa URL'den çıkar (son parça)
        if not title:
            title = href.strip("/").split("/")[-1].replace("-", " ").title()

        # Tekilleştirme: aynı href birden fazla yerde olabilir
        if href not in results:
            results[href] = title.strip()
            
    return results


def extract_poster(detail_soup, fallback_img=None):
    """Detay sayfasından dizi afişini çekmeye çalışır."""
    # 1. og:image (en güvenilir)
    og = detail_soup.find("meta", property="og:image")
    if og and og.get("content"):
        return og["content"].split("?")[0]

    # 2. Detay sayfasındaki ilk büyük resim
    img = detail_soup.select_one("img[src*='/showtv/iu/']")
    if img:
        url = get_image_url(img)
        if url:
            return url

    # 3. Fallback: anasayfadaki kart resmi
    if fallback_img:
        return get_image_url(fallback_img)

    return ""


def main():
    print("Diziler ve Bölümler taranıyor... (Yeni tasarım + MP4 & M3U8 + Otomatik Yeniden Deneme)")

    all_series = {}

    # Hem anasayfa hem /diziler sayfasını tara
    for page_url in [BASE_URL, f"{BASE_URL}/diziler"]:
        print(f"\n--> Taranıyor: {page_url}")
        soup = get_soup(page_url)
        if not soup:
            print("    [✗] Sayfa yüklenemedi, atlanıyor.")
            continue
        
        # Her bir dizi linki için karttaki img'yi de saklayalım
        series_links = find_series_links(soup)
        print(f"    [i] {len(series_links)} dizi linki bulundu.")
        
        for href, title in series_links.items():
            if href not in all_series:
                # Aynı linkin kartındaki img'yi bulmaya çalış
                a_tag = soup.find("a", href=href)
                fallback_img = a_tag.find("img") if a_tag else None
                all_series[href] = {"title": title, "img": fallback_img}

    print(f"\nToplam benzersiz {len(all_series)} dizi bulundu.\n")

    if not all_series:
        print("Hiç dizi bulunamadı! Seçici değişmiş olabilir.")
        create_html_file({})
        return

    diziler_data = {}

    for dizi_href, info in all_series.items():
        try:
            dizi_link = BASE_URL + dizi_href if dizi_href.startswith("/") else dizi_href
            dizi_adi = info["title"]
            dizi_id = slugify(dizi_adi)
            fallback_img = info["img"]

            if not dizi_adi or not dizi_id:
                continue

            print(f"\n--> İşleniyor: {dizi_adi}")

            detail_soup = get_soup(dizi_link)
            if not detail_soup:
                print(f"    [✗] Dizi detay sayfası yüklenemedi, atlanıyor.")
                continue

            poster_url = extract_poster(detail_soup, fallback_img)

            raw_links = []
            seen_urls = set()

            # Dropdown'dan bölüm linkleri
            options = detail_soup.find_all("option", attrs={"data-href": True})
            for opt in options:
                rel_link = opt.get("data-href")
                bolum_adi = opt.text.strip()
                if rel_link and "/tum_bolumler/" in rel_link:
                    full = BASE_URL + rel_link if rel_link.startswith("/") else rel_link
                    if full not in seen_urls:
                        raw_links.append({"ad": bolum_adi, "page_url": full})
                        seen_urls.add(full)

            # Sayfa içindeki doğrudan bölüm linkleri
            for a in detail_soup.select("a[href*='/tum_bolumler/']"):
                href = a.get("href")
                if not href:
                    continue
                full = BASE_URL + href if href.startswith("/") else href
                if full in seen_urls:
                    continue
                name = a.get("title") or a.get_text(strip=True)
                raw_links.append({"ad": name or "Bölüm", "page_url": full})
                seen_urls.add(full)

            print(f"    [i] {len(raw_links)} adet bölüm linki bulundu. Videolar çekiliyor...")

            final_bolumler = []

            for idx, item in enumerate(raw_links, 1):
                print(f"    [{idx}/{len(raw_links)}] İşleniyor: {item['ad'][:50]}...")

                video_soup = get_soup(item["page_url"])
                if not video_soup:
                    print(f"      [✗] Sayfa yüklenemedi, atlanıyor.")
                    continue

                page_title = video_soup.title.string if video_soup.title else item["ad"]
                clean_name = (page_title or "").replace("İzle", "").replace("Show TV", "").strip()

                if "Bölüm" in clean_name:
                    display_name = clean_name
                else:
                    display_name = item["ad"]

                episode_only = extract_episode_number_only(display_name)

                video_div = video_soup.find("div", class_="hope-video")
                if video_div and video_div.get("data-hope-video"):
                    try:
                        v_data = json.loads(video_div.get("data-hope-video"))
                        video_url = ""
                        format_type = ""

                        if "media" in v_data:
                            media = v_data["media"]
                            if "m3u8" in media and len(media["m3u8"]) > 0:
                                video_url = media["m3u8"][0]["src"]
                                format_type = "M3U8"
                            elif "mp4" in media and len(media["mp4"]) > 0:
                                video_url = media["mp4"][0]["src"]
                                format_type = "MP4"

                        if video_url:
                            video_url = video_url.replace("//ht/", "/ht/").replace("com//", "com/")
                            final_bolumler.append({
                                "ad": episode_only,
                                "link": video_url,
                                "episode_num": extract_episode_number(display_name)
                            })
                            print(f"      [✓] {episode_only} [{format_type}] Eklendi")
                        else:
                            print(f"      [✗] Video Kaynağı (M3U8/MP4) Bulunamadı.")

                    except Exception as e:
                        print(f"      [!] Video JSON hatası: {e}")

                time.sleep(0.1)

            if final_bolumler:
                final_bolumler = sorted(final_bolumler, key=lambda x: x['episode_num'])
                cleaned_final = [{"ad": x["ad"], "link": x["link"]} for x in final_bolumler]

                diziler_data[dizi_id] = {
                    "isim": dizi_adi,  # <-- ÖNEMLİ: Artık isim de saklanıyor
                    "resim": poster_url,
                    "bolumler": cleaned_final
                }
                print(f"    [✓] Toplam {len(cleaned_final)} bölüm eklendi.\n")
            else:
                print(f"    [✗] Hiç bölüm bulunamadı.\n")

        except Exception as e:
            print(f"[HATA] Dizi işlenirken hata: {e}\n")

    print("\n" + "=" * 50)
    print(f"Toplam {len(diziler_data)} dizi başarıyla işlendi!")
    print("=" * 50)

    create_html_file(diziler_data)


def create_html_file(data):
    json_str = json.dumps(data, ensure_ascii=False)

    # HTML kısmında küçük bir değişiklik yapıldı:
    # Dizi adı artık `key.replace('-', ' ')` yerine `dizi.isim` üzerinden geliyor!
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
            line-height: 20px; -webkit-text-size-adjust: 100%; text-decoration: none;
            -webkit-text-decoration: none; overflow-x: hidden;
        }
        .slider-slide { background: #15161a; box-sizing: border-box; }
        .slidefilmpanel { transition: .35s; box-sizing: border-box; background: #15161a; overflow: hidden; }
        .slidefilmpanel:hover { background-color: #572aa7; }
        .slidefilmpanel:hover .filmresim img { transform: scale(1.2); }
        .slider { position: relative; padding-bottom: 0px; width: 100%; overflow: hidden;
            --tw-shadow: 0 25px 50px -12px rgb(0 0 0 / 0.25);
            --tw-shadow-colored: 0 25px 50px -12px var(--tw-shadow-color);
            box-shadow: var(--tw-ring-offset-shadow, 0 0 #0000), var(--tw-ring-shadow, 0 0 #0000), var(--tw-shadow); }
        .slider-container { display: flex; width: 100%; scroll-snap-type: x var(--tw-scroll-snap-strictness);
            --tw-scroll-snap-strictness: mandatory; align-items: center; overflow: auto; scroll-behavior: smooth; }
        .slider-container .slider-slide { aspect-ratio: 9/13.5; display: flex; flex-shrink: 0;
            flex-basis: 14.14%; scroll-snap-align: start; flex-wrap: nowrap; align-items: center; justify-content: center; }
        .slider-container::-webkit-scrollbar { width: 0px; }
        .clear { clear: both; }
        .hataekran i { color: #572aa7; font-size: 80px; text-align: center; width: 100%; }
        .hataekran { width: 80%; margin: 20px auto; color: #fff; background: #15161a;
            border: 1px solid #323442; padding: 10px; box-sizing: border-box; border-radius: 10px; }
        .hatayazi { color: #fff; font-size: 15px; text-align: center; width: 100%; margin: 20px 0px; }
        .filmpaneldis { background: #15161a; width: 100%; margin: 20px auto; overflow: hidden; padding: 10px 5px; box-sizing: border-box; }
        .aramafilmpaneldis { background: #15161a; width: 100%; margin: 20px auto; overflow: hidden; padding: 10px 5px; box-sizing: border-box; }
        .sliderfilmimdb { display: none; }
        .bos { width: 100%; height: 60px; background: #572aa7; }
        .baslik { width: 96%; color: #fff; padding: 15px 10px; box-sizing: border-box; }
        .filmpanel { width: 12%; height: 200px; background: #15161a; float: left; margin: 1.14%;
            color: #fff; border-radius: 15px; box-sizing: border-box;
            box-shadow: 1px 5px 10px rgba(0,0,0,0.1); border: 1px solid #323442; padding: 0px;
            overflow: hidden; transition: border 0.3s ease, box-shadow 0.3s ease; cursor: pointer; }
        .filmisimpanel { width: 100%; height: 200px; position: relative; margin-top: -200px;
            background: linear-gradient(to bottom, rgba(0, 0, 0, 0) 0%, rgba(0, 0, 0, 1) 100%); }
        .filmpanel:hover { color: #fff; border: 3px solid #572aa7; box-shadow: 0 0 10px rgba(87, 42, 167, 0.5); }
        .filmpanel:focus { outline: none; border: 3px solid #572aa7; box-shadow: 0 0 10px rgba(87, 42, 167, 0.5); }
        .filmresim { width: 100%; height: 100%; margin-bottom: 0px; overflow: hidden; position: relative; }
        .filmresim img { width: 100%; height: 100%; transition: transform 0.4s ease; object-fit: cover; }
        .filmpanel:hover .filmresim img { transform: scale(1.1); }
        .filmpanel:focus .filmresim img { transform: none; }
        .filmisim { width: 100%; font-size: 14px; text-decoration: none; white-space: nowrap;
            overflow: hidden; text-overflow: ellipsis; padding: 0px 5px; box-sizing: border-box;
            color: #fff; position: absolute; bottom: 5px; }
        .filmimdb { display: none; }
        .resimust { display: none; }
        .filmyil { display: none; }
        .filmdil { display: none; }
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
        #dahafazla { background: #572aa7; color: #fff; padding: 10px; margin: 20px auto;
            width: 200px; text-align: center; transition: .35s; }
        #dahafazla:hover { background: #fff; color: #000; }
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
                
                // DİKKAT: Dizi ismi artık slug (id) yerine dizi.isim'den alınıyor!
                var displayName = dizi.isim || key.replace(/-/g, ' ').toUpperCase();
                
                item.innerHTML = `
                    <div class="filmresim"><img src="${dizi.resim}" onerror="this.src='https://via.placeholder.com/200x300?text=Resim+Yok'"></div>
                    <div class="filmisimpanel">
                        <div class="filmisim">${displayName}</div>
                    </div>
                `;
                container.appendChild(item);
            });
            checkInitialState();
        });

        let currentScreen = 'anaSayfa';

        function showBolumler(diziID) {
            sessionStorage.setItem('currentDiziID', diziID);
            var listContainer = document.getElementById("bolumListesi");
            listContainer.innerHTML = "";
            if (diziler[diziID]) {
                diziler[diziID].bolumler.forEach(function(bolum) {
                    var item = document.createElement("div");
                    item.className = "filmpanel";
                    item.innerHTML = `
                        <div class="filmresim"><img src="${diziler[diziID].resim}" onerror="this.src='https://via.placeholder.com/200x300?text=Resim+Yok'"></div>
                        <div class="filmisimpanel">
                            <div class="filmisim">${bolum.ad}</div>
                        </div>
                    `;
                    item.onclick = function() { showPlayer(bolum.link, diziID); };
                    listContainer.appendChild(item);
                });
            } else {
                listContainer.innerHTML = "<p>Bu dizi için bölüm bulunamadı.</p>";
            }
            document.querySelector("#diziListesiContainer").classList.add("hidden");
            document.getElementById("bolumler").classList.remove("hidden");
            document.getElementById("geriBtn").style.display = "block";
            currentScreen = 'bolumler';
            history.replaceState({ page: 'bolumler', diziID: diziID }, '', '#bolumler-' + diziID);
        }

        function showPlayer(streamUrl, diziID) {
            document.getElementById("playerpanel").style.display = "flex";
            document.getElementById("bolumler").classList.add("hidden");
            currentScreen = 'player';
            history.pushState({ page: 'player', diziID: diziID, streamUrl: streamUrl }, '', '#player-' + diziID);
            document.getElementById("main-player").innerHTML = "";
            const fullUrl = BRADMAX_BASE_URL + encodeURIComponent(streamUrl) + BRADMAX_PARAMS;
            const iframeHtml = `<iframe id="bradmax-iframe" src="${fullUrl}" allowfullscreen tabindex="0" autofocus></iframe>`;
            document.getElementById("main-player").innerHTML = iframeHtml;
        }

        function geriPlayer() {
            document.getElementById("playerpanel").style.display = "none";
            document.getElementById("bolumler").classList.remove("hidden");
            document.getElementById("main-player").innerHTML = "";
            currentScreen = 'bolumler';
            var currentDiziID = sessionStorage.getItem('currentDiziID');
            history.replaceState({ page: 'bolumler', diziID: currentDiziID }, '', '#bolumler-' + currentDiziID);
        }

        function geriDon() {
            sessionStorage.removeItem('currentDiziID');
            document.querySelector("#diziListesiContainer").classList.remove("hidden");
            document.getElementById("bolumler").classList.add("hidden");
            document.getElementById("geriBtn").style.display = "none";
            currentScreen = 'anaSayfa';
            history.replaceState({ page: 'anaSayfa' }, '', '#anaSayfa');
        }

        window.addEventListener('popstate', function(event) {
            var currentDiziID = sessionStorage.getItem('currentDiziID');
            if (event.state && event.state.page === 'player' && event.state.diziID && event.state.streamUrl) {
                showBolumler(event.state.diziID);
                showPlayer(event.state.streamUrl, event.state.diziID);
            } else if (event.state && event.state.page === 'bolumler' && event.state.diziID) {
                showBolumler(event.state.diziID);
            } else {
                sessionStorage.removeItem('currentDiziID');
                document.querySelector("#diziListesiContainer").classList.remove("hidden");
                document.getElementById("bolumler").classList.add("hidden");
                document.getElementById("playerpanel").style.display = "none";
                document.getElementById("geriBtn").style.display = "none";
                currentScreen = 'anaSayfa';
            }
        });

        function checkInitialState() {
            var hash = window.location.hash;
            if (hash.startsWith('#bolumler-')) {
                var diziID = hash.replace('#bolumler-', '');
                showBolumler(diziID);
            } else if (hash.startsWith('#player-')) {
                var parts = hash.split('-');
                var diziID = parts[1];
                var streamUrl = sessionStorage.getItem('lastStreamUrl');
                if (streamUrl) {
                    showBolumler(diziID);
                    setTimeout(() => { showPlayer(streamUrl, diziID); }, 100);
                }
            }
        }

        function searchSeries() {
            var searchTerm = document.getElementById('seriesSearch').value.toLowerCase();
            var container = document.getElementById('diziListesiContainer');
            var panels = container.querySelectorAll('.filmpanel');
            var found = false;
            panels.forEach(function(panel) {
                var seriesName = panel.querySelector('.filmisim').textContent.toLowerCase();
                if (seriesName.includes(searchTerm)) {
                    panel.style.display = 'block';
                    found = true;
                } else {
                    panel.style.display = 'none';
                }
            });
            if (!found) {
                var noResults = document.createElement('div');
                noResults.className = 'hataekran';
                noResults.innerHTML = '<i class="fas fa-search"></i><div class="hatayazi">Sonuç bulunamadı!</div>';
                container.appendChild(noResults);
            }
            return false;
        }

        function resetSeriesSearch() {
            var container = document.getElementById('diziListesiContainer');
            var panels = container.querySelectorAll('.filmpanel');
            panels.forEach(function(panel) { panel.style.display = 'block'; });
            var noResults = container.querySelector('.hataekran');
            if (noResults) { noResults.remove(); }
        }

        window.addEventListener('load', function() { setTimeout(checkInitialState, 100); });
    </script>
</body>
</html>'''

    filename = "showtv.html"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html_template)

    print(f"HTML dosyası '{filename}' oluşturuldu!")


if __name__ == "__main__":
    main()

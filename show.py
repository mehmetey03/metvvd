import requests
from bs4 import BeautifulSoup
import json
import time
import re
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_URL = "https://www.showtv.com.tr"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

MAX_RETRIES = 5
RETRY_DELAY = 2

def get_soup(url, retry_count=0):
    try:
        response = requests.get(url, headers=HEADERS, timeout=20)
        response.raise_for_status()
        return BeautifulSoup(response.content, "html.parser")
    except Exception as e:
        if retry_count < MAX_RETRIES:
            print(f"      ⚠ Hata: {e}. Tekrar deneniyor ({retry_count + 1}/{MAX_RETRIES})")
            time.sleep(RETRY_DELAY)
            return get_soup(url, retry_count + 1)
        print(f"      ✗ Maksimum deneme aşıldı: {url}")
        return None

def slugify(text):
    text = text.lower()
    text = text.replace('ı', 'i').replace('ğ', 'g').replace('ü', 'u').replace('ş', 's').replace('ö', 'o').replace('ç', 'c')
    return re.sub(r'[^a-z0-9]', '', text)

def extract_episode_number(name):
    match = re.search(r'(\d+)\.\s*Bölüm', name)
    return int(match.group(1)) if match else 9999

def extract_episode_number_only(name):
    match = re.search(r'(\d+)\.\s*Bölüm', name)
    if match: return f"{match.group(1)}. Bölüm"
    match = re.search(r'Bölüm\s*(\d+)', name, re.IGNORECASE)
    if match: return f"{match.group(1)}. Bölüm"
    match = re.search(r'(\d+)\s*Bölüm', name, re.IGNORECASE)
    if match: return f"{match.group(1)}. Bölüm"
    return name

def get_image_url(img_tag):
    if not img_tag: return ""
    for attr in ["data-src", "srcset", "src"]:
        val = img_tag.get(attr)
        if val and not val.startswith("data:"):
            if attr == "srcset":
                val = val.split(",")[0].strip().split(" ")[0]
            return val.split("?")[0]
    return ""

def load_all_series_with_selenium():
    """Selenium ile tüm dizileri 'Daha Fazla Göster' butonuna tıklayarak yükler."""
    print("Selenium başlatılıyor...")
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-gpu")

    driver = webdriver.Chrome(options=chrome_options)
    all_series = {}

    try:
        print(f"Sayfa açılıyor: {BASE_URL}/diziler")
        driver.get(f"{BASE_URL}/diziler")
        time.sleep(3)

        # "Daha Fazla Göster" butonuna görünmez olana kadar tıkla
        click_count = 0
        while True:
            try:
                # Buton var mı ve tıklanabilir mi?
                load_more_btn = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "button[data-load-more]"))
                )
                # Buton disabled mı veya gizli mi?
                if not load_more_btn.is_displayed() or load_more_btn.get_attribute("data-exhausted") == "1":
                    print("Buton artık görünmüyor veya tükendi. Sayfalama bitti.")
                    break
                
                # Sayfayı butona kaydır ve tıkla
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", load_more_btn)
                time.sleep(0.5)
                load_more_btn.click()
                click_count += 1
                print(f"  'Daha Fazla Göster' tıklandı ({click_count}). Bekleniyor...")
                time.sleep(2)  # Yeni içeriğin yüklenmesini bekle
            except Exception as e:
                print(f"  Buton bulunamadı veya tıklanamadı: {e}. Sayfalama bitti.")
                break

        print(f"Toplam {click_count} kez 'Daha Fazla Göster' tıklandı.")

        # Şimdi tüm sayfa HTML'ini al ve BeautifulSoup ile parse et
        soup = BeautifulSoup(driver.page_source, "html.parser")
        for card in soup.find_all("div", attrs={"data-box": "type1"}):
            a = card.find("a", href=re.compile(r"^/dizi/tanitim/"))
            if not a: continue
            href = a.get("href")
            if not href: continue
            title = a.get("title") or (a.find("img").get("alt") if a.find("img") else href.strip("/").split("/")[-2].replace("-", " ").title())
            poster = get_image_url(card.find("img"))
            if href not in all_series:
                all_series[href] = {"title": title.strip(), "poster": poster}
        
        print(f"Toplam {len(all_series)} benzersiz dizi bulundu.")
    finally:
        driver.quit()

    return all_series

def main():
    print("Diziler ve Bölümler taranıyor...")

    # Selenium ile tüm dizileri yükle
    series = load_all_series_with_selenium()
    if not series:
        print("Hiç dizi bulunamadı!")
        create_html_file({})
        return

    diziler_data = {}

    for dizi_href, info in series.items():
        try:
            dizi_link = BASE_URL + dizi_href
            dizi_adi = info["title"]
            dizi_id = slugify(dizi_adi)
            poster_url = info["poster"]

            print(f"--> İşleniyor: {dizi_adi}")

            detail_soup = get_soup(dizi_link)
            if not detail_soup:
                print(f"    [✗] Detay sayfası yüklenemedi.")
                continue

            raw_links = []
            seen_urls = set()
            for opt in detail_soup.find_all("option", attrs={"data-href": True}):
                rel_link = opt.get("data-href")
                bolum_adi = opt.text.strip()
                if rel_link and "/tum_bolumler/" in rel_link:
                    full = BASE_URL + rel_link
                    if full not in seen_urls:
                        raw_links.append({"ad": bolum_adi, "page_url": full})
                        seen_urls.add(full)

            print(f"    [i] {len(raw_links)} bölüm linki bulundu.")
            final_bolumler = []

            for idx, item in enumerate(raw_links, 1):
                video_soup = get_soup(item["page_url"])
                if not video_soup: continue

                page_title = video_soup.title.string if video_soup.title else item["ad"]
                clean_name = page_title.replace("İzle", "").replace("Show TV", "").strip()
                display_name = clean_name if "Bölüm" in clean_name else item["ad"]
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
                            print(f"      [✓] {episode_only} [{format_type}]")
                    except Exception as e:
                        print(f"      [!] JSON hatası: {e}")

                time.sleep(0.1)

            if final_bolumler:
                final_bolumler.sort(key=lambda x: x['episode_num'])
                cleaned = [{"ad": x["ad"], "link": x["link"]} for x in final_bolumler]
                diziler_data[dizi_id] = {
                    "isim": dizi_adi,
                    "resim": poster_url,
                    "bolumler": cleaned
                }
                print(f"    [✓] {len(cleaned)} bölüm eklendi.")
            else:
                print(f"    [✗] Bölüm bulunamadı.")

        except Exception as e:
            print(f"[HATA] {dizi_adi}: {e}")

    print(f"\nToplam {len(diziler_data)} dizi işlendi.")
    create_html_file(diziler_data)

def create_html_file(data):
    json_str = json.dumps(data, ensure_ascii=False)
    html_template = '''<!DOCTYPE html>
<html lang="tr">
<head>
    <title>ME TV YERLİ VOD</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, user-scalable=no, initial-scale=1.0">
    <script src="https://code.jquery.com/jquery-3.5.1.min.js"></script>
    <script src="https://kit.fontawesome.com/bbe955c5ed.js" crossorigin="anonymous"></script>
    <style>
        *:not(input):not(textarea) { user-select: none }
        body { margin: 0; padding: 0; background: #00040d; font-family: sans-serif; font-size: 15px; overflow-x: hidden; }
        .filmpaneldis { background: #15161a; width: 100%; margin: 20px auto; overflow: hidden; padding: 10px 5px; box-sizing: border-box; }
        .baslik { width: 96%; color: #fff; padding: 15px 10px; box-sizing: border-box; }
        .filmpanel { width: 12%; height: 200px; background: #15161a; float: left; margin: 1.14%;
            color: #fff; border-radius: 15px; box-sizing: border-box;
            box-shadow: 1px 5px 10px rgba(0,0,0,0.1); border: 1px solid #323442; padding: 0px;
            overflow: hidden; transition: 0.3s; cursor: pointer; position: relative; }
        .filmisimpanel { width: 100%; height: 200px; position: absolute; bottom: 0; left: 0;
            background: linear-gradient(to bottom, rgba(0,0,0,0) 0%, rgba(0,0,0,1) 100%); }
        .filmpanel:hover { border: 3px solid #572aa7; box-shadow: 0 0 10px rgba(87,42,167,0.5); }
        .filmresim { width: 100%; height: 100%; overflow: hidden; }
        .filmresim img { width: 100%; height: 100%; object-fit: cover; transition: transform 0.3s; }
        .filmpanel:hover .filmresim img { transform: scale(1.1); }
        .filmisim { width: 100%; font-size: 14px; white-space: nowrap; overflow: hidden;
            text-overflow: ellipsis; padding: 0 5px; box-sizing: border-box;
            position: absolute; bottom: 5px; }
        .aramapanel { width: 100%; height: 60px; background: #15161a; border-bottom: 1px solid #323442;
            margin: 0 auto; padding: 10px; box-sizing: border-box; overflow: hidden; z-index: 11111; }
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
        .geri-btn:hover { background: #6b3ec7; }
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
                var displayName = dizi.isim ? dizi.isim.toUpperCase() : key.replace(/-/g, ' ').toUpperCase();
                var imgUrl = dizi.resim || "";
                item.innerHTML = `
                    <div class="filmresim"><img src="${imgUrl}" onerror="this.style.display='none'; this.parentNode.style.background='#2a2a2a';"></div>
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
                    item.innerHTML = `
                        <div class="filmresim"><img src="${imgUrl}" onerror="this.style.display='none'; this.parentNode.style.background='#2a2a2a';"></div>
                        <div class="filmisimpanel">
                            <div class="filmisim">${bolum.ad}</div>
                        </div>
                    `;
                    item.onclick = function() { showPlayer(bolum.link); };
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
            document.getElementById("main-player").innerHTML = `<iframe id="bradmax-iframe" src="${fullUrl}" allowfullscreen></iframe>`;
        }

        function geriPlayer() {
            document.getElementById("playerpanel").style.display = "none";
            document.getElementById("bolumler").classList.remove("hidden");
            document.getElementById("main-player").innerHTML = "";
        }

        function geriDon() {
            document.querySelector("#diziListesiContainer").classList.remove("hidden");
            document.getElementById("bolumler").classList.add("hidden");
            document.getElementById("geriBtn").style.display = "none";
        }

        function searchSeries() {
            var term = document.getElementById('seriesSearch').value.toLowerCase();
            var panels = document.querySelectorAll('#diziListesiContainer .filmpanel');
            panels.forEach(function(panel) {
                var name = panel.querySelector('.filmisim').textContent.toLowerCase();
                panel.style.display = name.includes(term) ? 'block' : 'none';
            });
            return false;
        }

        function resetSeriesSearch() {
            document.querySelectorAll('#diziListesiContainer .filmpanel').forEach(p => p.style.display = 'block');
        }
    </script>
</body>
</html>'''

    with open("showtv.html", "w", encoding="utf-8") as f:
        f.write(html_template)

    print("HTML dosyası 'showtv.html' oluşturuldu!")

if __name__ == "__main__":
    main()

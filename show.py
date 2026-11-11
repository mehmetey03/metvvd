import requests
from bs4 import BeautifulSoup
import json
import time
import re

BASE_URL = "https://www.showtv.com.tr"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
    "X-Requested-With": "XMLHttpRequest" # AJAX istekleri için önemli
}

MAX_RETRIES = 5
RETRY_DELAY = 2


def get_soup(url, retry_count=0):
    try:
        response = requests.get(url, headers=HEADERS, timeout=20)
        response.raise_for_status()
        return BeautifulSoup(response.content, "html.parser")
    except requests.exceptions.Timeout:
        if retry_count < MAX_RETRIES:
            print(f"      ⚠ Timeout hatası! Yeniden deneniyor... ({retry_count + 1}/{MAX_RETRIES})")
            time.sleep(RETRY_DELAY)
            return get_soup(url, retry_count + 1)
        print(f"      ✗ Maksimum deneme sayısına ulaşıldı. URL atlanıyor: {url}")
        return None
    except Exception as e:
        if retry_count < MAX_RETRIES:
            print(f"      ⚠ Hata: {e}. Yeniden deneniyor... ({retry_count + 1}/{MAX_RETRIES})")
            time.sleep(RETRY_DELAY)
            return get_soup(url, retry_count + 1)
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
    """Lazy-load yapısına uygun resim çekici."""
    if not img_tag:
        return ""
    
    # 1. data-src (Lazy load için en garantili)
    data_src = img_tag.get("data-src")
    if data_src and not data_src.startswith("data:"):
        return data_src.split("?")[0]
        
    # 2. srcset (Genelde yüksek çözünürlük burada olur)
    srcset = img_tag.get("srcset")
    if srcset:
        first_url = srcset.split(",")[0].strip().split(" ")[0]
        if first_url and not first_url.startswith("data:"):
            return first_url.split("?")[0]

    # 3. src
    src = img_tag.get("src")
    if src and not src.startswith("data:") and "placeholder" not in src.lower():
        return src.split("?")[0]

    return ""


def find_series_cards(soup):
    """Sayfadaki veya AJAX'tan gelen dizi kartlarını ayıklar."""
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
            title = href.strip("/").split("/")[-2].replace("-", " ").title()

        img_tag = a.find("img")
        poster = get_image_url(img_tag)

        if href not in results:
            results[href] = {"title": title.strip(), "poster": poster}
    return results


def load_all_series():
    """Sayfa 1'den başlayıp AJAX ile tüm dizileri çeker."""
    print("Dizi listesi yükleniyor (İlk Sayfa)...")
    soup = get_soup(f"{BASE_URL}/diziler")
    if not soup: return {}

    all_series = find_series_cards(soup)
    print(f"İlk sayfadan {len(all_series)} dizi alındı.")
    
    # Sayfalama parametrelerini oku
    load_more_btn = soup.find("button", attrs={"data-load-more": True})
    if not load_more_btn:
        print("Sayfalama butonu bulunamadı.")
        return all_series
        
    endpoint = load_more_btn.get("data-endpoint", "/diziler/daha-fazla")
    page = int(load_more_btn.get("data-page", "2"))
    
    while True:
        ajax_url = f"{BASE_URL}{endpoint}?page={page}"
        print(f"AJAX İsteği: {ajax_url}")
        
        # Sayfa bittiğinde 404 dönebilir, hata yönetimiyle yakalıyoruz
        ajax_soup = get_soup(ajax_url)
        if not ajax_soup:
            print("Yeni sayfa yüklenemedi, sayfalama bitti.")
            break
            
        new_series = find_series_cards(ajax_soup)
        if not new_series:
            print("Bu sayfada dizi bulunamadı, sayfalama bitti.")
            break
            
        added = 0
        for href, info in new_series.items():
            if href not in all_series:
                all_series[href] = info
                added += 1
                
        print(f"Sayfa {page}: {added} yeni dizi eklendi. (Toplam: {len(all_series)})")
        
        if added == 0:
            break
            
        page += 1
        time.sleep(0.5)
    
    return all_series


def main():
    print("Show TV VOD Scraper Başlıyor...")

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
                continue

            # Detay sayfasında daha iyi bir afiş varsa onu kullan
            og = detail_soup.find("meta", property="og:image")
            if og and og.get("content") and "showtv_social_media" not in og["content"]:
                poster_url = og["content"].split("?")[0]

            raw_links = []
            seen_urls = set()

            for opt in detail_soup.find_all("option", attrs={"data-href": True}):
                rel_link = opt.get("data-href")
                if rel_link and "/tum_bolumler/" in rel_link:
                    full = BASE_URL + rel_link if rel_link.startswith("/") else rel_link
                    if full not in seen_urls:
                        raw_links.append({"ad": opt.text.strip(), "page_url": full})
                        seen_urls.add(full)

            for a in detail_soup.select("a[href*='/tum_bolumler/']"):
                href = a.get("href")
                if not href: continue
                full = BASE_URL + href if href.startswith("/") else href
                if full not in seen_urls: 
                    name = a.get("title") or a.get_text(strip=True) or "Bölüm"
                    raw_links.append({"ad": name, "page_url": full})
                    seen_urls.add(full)

            print(f"    [i] {len(raw_links)} bölüm bulundu.")
            final_bolumler = []

            for idx, item in enumerate(raw_links, 1):
                video_soup = get_soup(item["page_url"])
                if not video_soup:
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
                        if "media" in v_data:
                            media = v_data["media"]
                            if "m3u8" in media and len(media["m3u8"]) > 0:
                                video_url = media["m3u8"][0]["src"]
                            elif "mp4" in media and len(media["mp4"]) > 0:
                                video_url = media["mp4"][0]["src"]
                                
                        if video_url:
                            video_url = video_url.replace("//ht/", "/ht/").replace("com//", "com/")
                            final_bolumler.append({
                                "ad": episode_only,
                                "link": video_url,
                                "episode_num": extract_episode_number(display_name)
                            })
                    except Exception:
                        pass
                time.sleep(0.1)

            if final_bolumler:
                final_bolumler.sort(key=lambda x: x["episode_num"])
                cleaned = [{"ad": x["ad"], "link": x["link"]} for x in final_bolumler]
                diziler_data[dizi_id] = {
                    "isim": dizi_adi,
                    "resim": poster_url,
                    "bolumler": cleaned,
                }
                print(f"    [✓] {len(cleaned)} bölüm eklendi.")

        except Exception as e:
            print(f"[HATA] {dizi_adi}: {e}")

    print(f"\nİşlem tamam! Toplam {len(diziler_data)} dizi.")
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
            border: 1px solid #323442; overflow: hidden; transition: 0.3s; cursor: pointer; position: relative; }
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
            padding: 10px; box-sizing: border-box; display: flex; justify-content: space-between; align-items: center;}
        .logoisim { font-size: 20px; font-weight: bold; color: #fff; margin-left: 10px; }
        .aramapanelyazi { height: 40px; width: 200px; padding: 0 10px; border: 1px solid #ccc; }
        .aramapanelbuton { height: 40px; width: 60px; background: #572aa7; color: #fff; border: none; cursor: pointer; }
        .hidden { display: none; }
        .bolum-container { background: #15161a; padding: 10px; margin-top: 10px; }
        .geri-btn { background: #572aa7; color: white; padding: 10px; width: 100px; text-align: center;
            cursor: pointer; margin-bottom: 10px; border-radius: 5px; }
        .playerpanel { width: 100%; height: 100vh; position: fixed; top: 0; left: 0;
            background: #0a0e17; z-index: 9999; display: none; flex-direction: column; }
        #main-player { width: 100%; height: 100%; }
        #bradmax-iframe { width: 100%; height: 100%; border: none; }
        .player-geri-btn { background: #572aa7; color: white; padding: 10px; width: 100px; position: absolute; top: 10px; left: 10px; z-index: 10000; cursor: pointer;}
        @media(max-width:550px) { .filmpanel { width: 31.33%; height: 180px; margin: 1%; } }
    </style>
</head>
<body>
    <div class="aramapanel">
        <div style="display:flex; align-items:center;">
            <img src="https://i.hizliresim.com/t6e66bt.png" style="width: 40px;">
            <div class="logoisim">ME TV</div>
        </div>
        <div>
            <form onsubmit="return searchSeries()">
                <input type="text" id="seriesSearch" placeholder="Dizi Ara..." class="aramapanelyazi" oninput="resetSeriesSearch()">
                <input type="submit" value="ARA" class="aramapanelbuton">
            </form>
        </div>
    </div>

    <div class="filmpaneldis" id="diziListesiContainer">
        <div class="baslik">TÜM DİZİLER</div>
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
                
                // Resim varsa göster, yoksa dizi adının baş harfini göster
                var imgHtml = dizi.resim 
                    ? `<img src="${dizi.resim}" onerror="this.style.display='none'; this.parentNode.innerHTML='<div style=\\'display:flex;align-items:center;justify-content:center;height:100%;background:#2a2a2a;font-size:24px;font-weight:bold;\\'>${dizi.isim.charAt(0)}</div>';">` 
                    : `<div style="display:flex;align-items:center;justify-content:center;height:100%;background:#2a2a2a;font-size:24px;font-weight:bold;">${dizi.isim.charAt(0)}</div>`;
                
                item.innerHTML = `
                    <div class="filmresim">${imgHtml}</div>
                    <div class="filmisimpanel">
                        <div class="filmisim">${dizi.isim.toUpperCase()}</div>
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
                    var imgHtml = diziler[diziID].resim 
                        ? `<img src="${diziler[diziID].resim}" onerror="this.style.display='none'; this.parentNode.innerHTML='<div style=\\'display:flex;align-items:center;justify-content:center;height:100%;background:#2a2a2a;font-size:24px;font-weight:bold;\\'>${diziler[diziID].isim.charAt(0)}</div>';">` 
                        : `<div style="display:flex;align-items:center;justify-content:center;height:100%;background:#2a2a2a;font-size:24px;font-weight:bold;">${diziler[diziID].isim.charAt(0)}</div>`;

                    item.innerHTML = `
                        <div class="filmresim">${imgHtml}</div>
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
        }

        function showPlayer(streamUrl) {
            document.getElementById("playerpanel").style.display = "flex";
            document.getElementById("bolumler").classList.add("hidden");
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

import requests
from bs4 import BeautifulSoup
import json
import time
import re
import os
import subprocess

# Web sitesi kök adresi
BASE_URL = "https://www.showtv.com.tr"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

MAX_RETRIES = 5  
RETRY_DELAY = 2  

def commit_and_push(file_name):
    """GitHub Actions ortamında dosyayı repoya push eder."""
    print(f"\n📤 {file_name} GitHub Reposuna yükleniyor...")
    try:
        subprocess.run(["git", "config", "--global", "user.name", "github-actions[bot]"], check=True)
        subprocess.run(["git", "config", "--global", "user.email", "github-actions[bot]@users.noreply.github.com"], check=True)
        subprocess.run(["git", "add", file_name], check=True)
        
        status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout
        if status:
            subprocess.run(["git", "commit", "-m", f"🔄 Show TV Arşivi Güncellendi: {file_name}"], check=True)
            subprocess.run(["git", "push"], check=True)
            print("🚀 GitHub Reponuza başarıyla yüklendi!")
        else:
            print("ℹ️ Herhangi bir değişiklik yok, push atlanıyor.")
    except Exception as e:
        print(f"❌ GitHub Push Hatası: {e}")

def get_soup(url, retry_count=0):
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        return BeautifulSoup(response.content, "html.parser")
    except Exception:
        if retry_count < MAX_RETRIES:
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

def extract_episode_number_only(name):
    match = re.search(r'(\d+)\.\s*Bölüm', name)
    if match: return f"{match.group(1)}. Bölüm"
    match = re.search(r'Bölüm\s*(\d+)', name, re.IGNORECASE)
    if match: return f"{match.group(1)}. Bölüm"
    return name

def main():
    print("🚀 Show TV Diziler ve Bölümler taranıyor...")
    soup = get_soup(f"{BASE_URL}/diziler")
    if not soup: return

    diziler_data = {}
    dizi_kutulari = soup.find_all("div", attrs={"data-name": "box-type6"})
    
    for kutu in dizi_kutulari[:15]: # Performans için ilk 15 dizi
        try:
            link_tag = kutu.find("a", class_="group")
            if not link_tag: continue
                
            dizi_link = BASE_URL + link_tag.get("href")
            dizi_adi = link_tag.get("title")
            dizi_id = slugify(dizi_adi)
            
            img_tag = kutu.find("img")
            poster_url = img_tag.get("data-src") or img_tag.get("src", "")
            if "?" in poster_url: poster_url = poster_url.split("?")[0]

            print(f"📺 {dizi_adi} işleniyor...")

            detail_soup = get_soup(dizi_link)
            if not detail_soup: continue

            raw_links = []
            seen_urls = set()
            options = detail_soup.find_all("option", attrs={"data-href": True})
            for opt in options:
                rel_link = opt.get("data-href")
                if "/tum_bolumler/" in rel_link:
                    full = BASE_URL + rel_link
                    if full not in seen_urls:
                        raw_links.append({"ad": opt.text.strip(), "page_url": full})
                        seen_urls.add(full)

            final_bolumler = []
            for item in raw_links[:30]:
                video_soup = get_soup(item["page_url"])
                if not video_soup: continue
                
                video_div = video_soup.find("div", class_="hope-video")
                if video_div and video_div.get("data-hope-video"):
                    try:
                        v_data = json.loads(video_div.get("data-hope-video"))
                        media = v_data.get("media", {})
                        video_url = ""
                        if media.get("m3u8"): video_url = media["m3u8"][0]["src"]
                        elif media.get("mp4"): video_url = media["mp4"][0]["src"]
                        
                        if video_url:
                            video_url = video_url.replace("//ht/", "/ht/").replace("com//", "com/")
                            final_bolumler.append({
                                "ad": extract_episode_number_only(item["ad"]),
                                "link": video_url,
                                "episode_num": extract_episode_number(item["ad"])
                            })
                    except: pass

            if final_bolumler:
                final_bolumler = sorted(final_bolumler, key=lambda x: x['episode_num'])
                diziler_data[dizi_id] = {
                    "resim": poster_url,
                    "bolumler": [{"ad": x["ad"], "link": x["link"]} for x in final_bolumler]
                }
                print(f"    ✅ {len(final_bolumler)} bölüm eklendi.")

        except Exception as e:
            print(f"❌ Hata: {e}")

    create_html_file(diziler_data)

def create_html_file(data):
    file_name = "showtv.html"
    json_str = json.dumps(data, ensure_ascii=False)
    
    # Senin sağladığın HTML Template'i buraya entegre edildi
    html_template = f'''<!DOCTYPE html>
<html lang="tr">
<head>
    <title>ME TV YERLİ VOD</title>
    <meta charset="utf-8">
    <style>
        /* Senin CSS kodların buraya otomatik gelecek */
        body {{ background: #00040d; color: white; font-family: sans-serif; }}
        .filmpanel {{ width: 150px; float: left; margin: 10px; cursor: pointer; border: 1px solid #333; }}
        .filmresim img {{ width: 100%; }}
        .hidden {{ display: none; }}
    </style>
</head>
<body>
    <div id="diziListesiContainer"></div>
    <div id="bolumler" class="hidden"><button onclick="location.reload()">Geri</button><div id="bolumListesi"></div></div>
    <script>
        var diziler = {json_str};
        var container = document.getElementById("diziListesiContainer");
        Object.keys(diziler).forEach(key => {{
            var div = document.createElement("div");
            div.className = "filmpanel";
            div.innerHTML = `<img src="${{diziler[key].resim}}"><p>${{key}}</p>`;
            div.onclick = () => showBolum(key);
            container.appendChild(div);
        }});
        function showBolum(key) {{
            container.classList.add("hidden");
            var list = document.getElementById("bolumListesi");
            document.getElementById("bolumler").classList.remove("hidden");
            diziler[key].bolumler.forEach(b => {{
                var btn = document.createElement("button");
                btn.innerText = b.ad;
                btn.onclick = () => window.open(b.link);
                list.appendChild(btn);
            }});
        }}
    </script>
</body>
</html>'''

    with open(file_name, "w", encoding="utf-8") as f:
        f.write(html_template)
    
    print(f"\n✨ {file_name} başarıyla oluşturuldu.")
    
    # GITHUB PUSH KONTROLÜ
    if os.getenv('GITHUB_ACTIONS') == 'true' or os.path.exists('.git'):
        commit_and_push(file_name)

if __name__ == "__main__":
    main()

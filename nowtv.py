import cloudscraper
from bs4 import BeautifulSoup
import json
import re
import subprocess

# Ayarlar
BASE_URL = "https://www.nowtv.com.tr"
ARCHIVE_URL = "https://www.nowtv.com.tr/dizi-arsivi"
BRADMAX_PLAYER = "https://bradmax.com/client/embed-player/d9decbf0d308f4bb91825c3f3a2beb7b0aaee2f6_8493?mediaUrl="

def slugify(text):
    mapping = {'ç':'c','ğ':'g','ı':'i','ö':'o','ş':'s','ü':'u','İ':'i','I':'i'}
    text = text.lower()
    for tr, en in mapping.items(): text = text.replace(tr, en)
    return re.sub(r'[^a-z0-9]+', '-', text).strip('-')

def get_now_m3u8(scraper, bolum_url):
    try:
        r = scraper.get(bolum_url, timeout=10)
        m3u8_match = re.search(r'(https?://[^\s"\']+\.m3u8[^\s"\']*)', r.text)
        if m3u8_match:
            return m3u8_match.group(0).replace('\\/', '/')
        return bolum_url
    except:
        return bolum_url

def run_scraper():
    print("🚀 NOW TV Scraper Zorlanıyor...")
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
    series_data = {}
    
    try:
        # 1. Sayfayı Çek
        resp = scraper.get(ARCHIVE_URL, timeout=20)
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Seçiciyi genişletiyoruz: Senin paylaştığın yapıdaki tüm kartları bul
        cards = soup.find_all('div', class_='list-item')
        print(f"🔎 Sitede {len(cards)} adet potansiyel dizi kartı bulundu.")

        for card in cards:
            link_tag = card.find('a', href=True)
            # Başlık bulma (Strong veya program-name içinden)
            title_tag = card.find('strong') or card.find(class_='program-name')
            
            if not link_tag or not title_tag:
                continue
            
            title = title_tag.get_text(strip=True)
            href = link_tag['href']
            
            # Linki temizle ve bölümler sayfasına yönlendir
            bolumler_url = (BASE_URL + href if href.startswith('/') else href).replace('/izle', '/bolumler')
            dizi_id = slugify(title)

            print(f"🎬 {title} için bölümler taranıyor...")
            
            try:
                b_resp = scraper.get(bolumler_url, timeout=15)
                b_soup = BeautifulSoup(b_resp.text, 'html.parser')
                # Bölüm linklerini topla
                b_links = b_soup.find_all('a', href=re.compile(r'/bolum/'))
                
                eps = []
                for b_link in b_links:
                    full_b_url = BASE_URL + b_link['href'] if b_link['href'].startswith('/') else b_link['href']
                    
                    # Bölüm adını bulmaya çalış
                    b_name = b_link.find_next(class_='program-name') or b_link.find_next('strong')
                    b_title = b_name.get_text(strip=True) if b_name else "Bölüm"
                    
                    # m3u8 çek (Daha hızlı olması için şimdilik sadece linki alıyoruz, 
                    # gerekirse get_now_m3u8 fonksiyonunu burada çağırabilirsin)
                    m3u8 = get_now_m3u8(scraper, full_b_url)
                    
                    if not any(e['link'] == m3u8 for e in eps):
                        eps.append({"ad": b_title, "link": m3u8})

                if eps:
                    # Resim bulma
                    img = card.find('img')
                    poster = img.get('src') or img.get('data-src', '')
                    if poster and not poster.startswith('http'): poster = BASE_URL + poster
                    
                    series_data[dizi_id] = {
                        "isim": title,
                        "resim": poster,
                        "bolumler": eps
                    }
                    print(f"   ✅ {len(eps)} bölüm eklendi.")
            except Exception as e:
                print(f"   ⚠️ {title} bölümleri çekilemedi: {e}")
                
    except Exception as e:
        print(f"❌ Ana sayfa hatası: {e}")

    # Eğer veri varsa HTML oluştur, yoksa hata bas
    if series_data:
        create_html(series_data)
    else:
        print("🚨 HATA: Hiçbir dizi verisi toplanamadı! HTML güncellenmiyor.")

def create_html(series_data):
    file_name = "nowtv_vod.html"
    json_embedded = json.dumps(series_data, ensure_ascii=False)
    
    html_content = f'''<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="utf-8">
    <title>NOW VOD</title>
    <style>
        body {{ background:#000; color:#fff; font-family:sans-serif; margin:0; }}
        .grid {{ display:grid; grid-template-columns:repeat(auto-fill, minmax(150px, 1fr)); gap:10px; padding:20px; }}
        .card {{ background:#111; border:1px solid #333; padding:10px; cursor:pointer; text-align:center; }}
        .card img {{ width:100%; height:200px; object-fit:cover; }}
        .player {{ position:fixed; top:0; left:0; width:100%; height:100%; background:#000; display:none; z-index:99; }}
        .close {{ position:absolute; top:10px; right:10px; background:red; color:white; border:none; padding:10px; cursor:pointer; }}
    </style>
</head>
<body>
    <div id="m-grid" class="grid"></div>
    <div id="p-view" class="player">
        <button class="close" onclick="closeP()">KAPAT</button>
        <div id="v-frame" style="width:100%; height:100%;"></div>
    </div>
    <script>
        const data = {json_embedded};
        const m = document.getElementById("m-grid");
        Object.keys(data).forEach(id => {{
            const c = document.createElement("div");
            c.className = "card";
            c.innerHTML = `<img src="${{data[id].resim}}"><div>${{data[id].isim}}</div>`;
            c.onclick = () => showEpisodes(id);
            m.appendChild(c);
        }});

        function showEpisodes(id) {{
            m.innerHTML = `<button onclick="location.reload()" style="padding:10px; margin:10px;">GERİ DÖN</button><h2>${{data[id].isim}}</h2>`;
            data[id].bolumler.forEach(ep => {{
                const d = document.createElement("div");
                d.className = "card";
                d.innerHTML = `<div>${{ep.ad}}</div>`;
                d.onclick = () => play(ep.link);
                m.appendChild(d);
            }});
        }}

        function play(link) {{
            document.getElementById("p-view").style.display = "block";
            let embed = link.includes(".m3u8") ? "https://bradmax.com/client/embed-player/d9decbf0d308f4bb91825c3f3a2beb7b0aaee2f6_8493?mediaUrl=" + encodeURIComponent(link) : link;
            document.getElementById("v-frame").innerHTML = `<iframe src="${{embed}}" width="100%" height="100%" frameborder="0" allowfullscreen></iframe>`;
        }}

        function closeP() {{ document.getElementById("p-view").style.display="none"; document.getElementById("v-frame").innerHTML=""; }}
    </script>
</body>
</html>'''

    with open(file_name, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    # Git işlemleri
    try:
        subprocess.run(["git", "config", "--global", "user.name", "github-actions[bot]"], check=True)
        subprocess.run(["git", "config", "--global", "user.email", "github-actions[bot]@users.noreply.github.com"], check=True)
        subprocess.run(["git", "add", file_name], check=True)
        subprocess.run(["git", "commit", "-m", "🔄 VOD İçerik Güncellendi"], check=True)
        subprocess.run(["git", "push"], check=True)
    except: pass

if __name__ == "__main__":
    run_scraper()

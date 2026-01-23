import cloudscraper
from bs4 import BeautifulSoup
import json
import re
import subprocess
import time

# Ayarlar
BASE_URL = "https://www.nowtv.com.tr"
AJAX_URL = "https://www.nowtv.com.tr/ajax/get_archive_programs" # Ajax'ın gittiği asıl uç nokta
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
    print("🚀 NOW TV Derin Arşiv Taraması Başlatıldı...")
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
    series_data = {}
    
    # Sayfa 0'dan başla (NowTV indexi 0 veya 1 olabilir, döngüyle hepsini deneyeceğiz)
    for page in range(0, 12): # 106 dizi varsa ortalama 11 sayfa (her sayfada 10 dizi) eder.
        print(f"📂 Veri kümesi {page} isteniyor...")
        
        # Paylaştığın butondaki parametreleri POST olarak gönderiyoruz
        payload = {
            'filter': 'archive',
            'rows': '106',
            'page': str(page),
            'count': '10',
            'type': 'series',
            'orderby': 'id',
            'sorting': 'desc'
        }
        
        try:
            # Ajax isteğini taklit et
            resp = scraper.post(AJAX_URL, data=payload, timeout=15)
            
            # NowTV bazen JSON bazen ham HTML döner. HTML parçasını ayıkla:
            html_content = ""
            if "application/json" in resp.headers.get('Content-Type', ''):
                html_content = resp.json().get('html', '')
            else:
                html_content = resp.text

            if not html_content or "list-item" not in html_content:
                print(f"🏁 Sayfa {page}'de yeni içerik yok, durduruluyor.")
                break
                
            soup = BeautifulSoup(html_content, 'html.parser')
            cards = soup.select('.list-item')
            
            for card in cards:
                link_tag = card.find('a', href=True)
                title_tag = card.find('strong') or card.find(class_='program-name')
                
                if not link_tag or not title_tag: continue
                
                title = title_tag.get_text(strip=True)
                href = link_tag['href']
                dizi_id = slugify(title)

                if dizi_id in series_data: continue

                print(f"  🎬 {title} bölümleri aranıyor...")
                bolumler_url = (BASE_URL + href if href.startswith('/') else href).replace('/izle', '/bolumler')
                
                try:
                    b_resp = scraper.get(bolumler_url, timeout=10)
                    b_soup = BeautifulSoup(b_resp.text, 'html.parser')
                    # Bölüm linklerini topla (hem /bolum/ hem video-card yapılarını kontrol et)
                    b_links = b_soup.find_all('a', href=re.compile(r'/bolum/|/izle'))
                    
                    eps = []
                    for b_link in b_links:
                        # Ana sayfaya giden linkleri ele (sadece bölüm linkleri kalsın)
                        if b_link['href'].endswith('/izle') and "/bolum/" not in b_link['href']: continue
                        
                        full_b_url = BASE_URL + b_link['href'] if b_link['href'].startswith('/') else b_link['href']
                        b_name = b_link.find_next(class_='program-name') or b_link.find_next('strong') or b_link.get('title')
                        b_title = b_name.get_text(strip=True) if hasattr(b_name, 'get_text') else (b_name if b_name else "Bölüm")
                        
                        # Kopya bölümleri engelle
                        if any(e['ad'] == b_title for e in eps): continue
                        
                        m3u8 = get_now_m3u8(scraper, full_b_url)
                        eps.append({"ad": b_title, "link": m3u8})

                    if eps:
                        img = card.find('img')
                        poster = img.get('src') or img.get('data-src', '')
                        if poster and not poster.startswith('http'): poster = BASE_URL + poster
                        
                        series_data[dizi_id] = {
                            "isim": title,
                            "resim": poster,
                            "bolumler": eps
                        }
                        print(f"    ✅ {len(eps)} bölüm eklendi.")
                except Exception as e:
                    print(f"    ⚠️ Bölüm hatası: {e}")
                    continue
            
            time.sleep(1) # Ban riskine karşı bekleme
            
        except Exception as e:
            print(f"❌ Ajax hatası (Sayfa {page}): {e}")
            break

    if series_data:
        # Öncekiyle aynı HTML oluşturma ve Git push fonksiyonlarını buraya ekle
        create_and_push(series_data)
    else:
        print("🚨 HATA: Hiçbir veri çekilemedi. Parametreler değişmiş olabilir.")

def create_and_push(series_data):
    # HTML tasarımı (Modern ve Grid Yapılı)
    file_name = "nowtv_vod.html"
    json_data = json.dumps(series_data, ensure_ascii=False)
    html = f'''<!DOCTYPE html><html lang="tr"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>NOW VOD</title><style>body{{background:#000;color:#fff;font-family:sans-serif;margin:0;}}.nav{{background:#111;padding:15px;display:flex;justify-content:space-between;border-bottom:2px solid red;position:sticky;top:0;z-index:99;}}.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:10px;padding:10px;}}.card{{background:#111;border:1px solid #333;border-radius:5px;overflow:hidden;cursor:pointer;text-align:center;font-size:12px;}}.card img{{width:100%;aspect-ratio:2/3;object-fit:cover;}}.player{{position:fixed;top:0;left:0;width:100%;height:100%;background:#000;display:none;z-index:100;}} iframe{{width:100%;height:100%;border:none;}}</style></head><body><div class="nav"><b>NOW TV (${{Object.keys(JSON.parse('{json_data}')).length}} Dizi)</b><input type="text" id="s" placeholder="Ara..." oninput="search()"></div><div id="g" class="grid"></div><div id="p" class="player"><button onclick="closeP()" style="position:absolute;right:10px;top:10px;z-index:101;background:red;color:#fff;border:none;padding:10px;">KAPAT</button><div id="f"></div></div><script>const d={json_data};const g=document.getElementById("g");function init(){{g.innerHTML="";Object.keys(d).forEach(i=>{{const c=document.createElement("div");c.className="card";c.innerHTML=`<img src="${{d[i].resim}}"><div>${{d[i].isim}}</div>`;c.onclick=()=>show(i);g.appendChild(c);}});}}function show(i){{window.scrollTo(0,0);g.innerHTML=`<div style="grid-column:1/-1"><button onclick="init()" style="padding:10px;margin-bottom:10px;">← GERİ</button><h2>${{d[i].isim}}</h2></div>`;d[i].bolumler.forEach(e=>{{const c=document.createElement("div");c.className="card";c.innerHTML=`<img src="${{d[i].resim}}"><div>${{e.ad}}</div>`;c.onclick=()=>play(e.link);g.appendChild(c);}});}}function play(l){{document.getElementById("p").style.display="block";const u=l.includes("m3u8")?"https://bradmax.com/client/embed-player/d9decbf0d308f4bb91825c3f3a2beb7b0aaee2f6_8493?mediaUrl="+encodeURIComponent(l):l;document.getElementById("f").innerHTML=`<iframe src="${{u}}&autoplay=true" allowfullscreen></iframe>`;}}function closeP(){{document.getElementById("p").style.display="none";document.getElementById("f").innerHTML="";}}function search(){{let q=document.getElementById("s").value.toLowerCase();document.querySelectorAll(".card").forEach(c=>c.style.display=c.innerText.toLowerCase().includes(q)?"":"none");}}init();</script></body></html>'''
    with open(file_name, "w", encoding="utf-8") as f: f.write(html)
    try:
        subprocess.run(["git", "config", "--global", "user.name", "github-actions[bot]"])
        subprocess.run(["git", "config", "--global", "user.email", "github-actions[bot]@users.noreply.github.com"])
        subprocess.run(["git", "add", file_name])
        subprocess.run(["git", "commit", "-m", "🔄 Tüm Arşiv Güncellendi"])
        subprocess.run(["git", "push"])
    except: pass

if __name__ == "__main__":
    run_scraper()

import cloudscraper
from bs4 import BeautifulSoup
import json
import time
import re
import subprocess

# Ayarlar
JSON_SOURCE_URL = "https://raw.githubusercontent.com/mehmetey03/metvvd/refs/heads/main/nowtv_data.json"
BASE_URL = "https://www.nowtv.com.tr"
BRADMAX_PLAYER = "https://bradmax.com/client/embed-player/d9decbf0d308f4bb91825c3f3a2beb7b0aaee2f6_8493?mediaUrl="

def slugify(text):
    mapping = {'ç':'c','ğ':'g','ı':'i','ö':'o','ş':'s','ü':'u','İ':'i','I':'i'}
    text = text.lower()
    for tr, en in mapping.items(): text = text.replace(tr, en)
    return re.sub(r'[^a-z0-9]+', '-', text).strip('-')

def get_now_m3u8(scraper, bolum_url):
    try:
        time.sleep(0.3)
        r = scraper.get(bolum_url, timeout=10)
        m3u8_match = re.search(r'(https?://[^\s"\']+\.m3u8[^\s"\']*)', r.text)
        if m3u8_match:
            return m3u8_match.group(0).replace('\\/', '/')
        return bolum_url
    except:
        return bolum_url

def commit_and_push(file_name):
    print(f"\n📤 {file_name} GitHub'a gönderiliyor...")
    try:
        subprocess.run(["git", "config", "--global", "user.name", "github-actions[bot]"], check=True)
        subprocess.run(["git", "config", "--global", "user.email", "github-actions[bot]@users.noreply.github.com"], check=True)
        subprocess.run(["git", "add", file_name], check=True)
        status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout
        if status:
            subprocess.run(["git", "commit", "-m", "🔄 NOW TV VOD Updated from JSON Source"], check=True)
            subprocess.run(["git", "push"], check=True)
            print("🚀 GitHub'a başarıyla yüklendi!")
    except Exception as e:
        print(f"❌ Git Hatası: {e}")

def get_all_episodes_from_api(scraper, program_id, season=1):
    """API'den tüm bölümleri getir"""
    all_episodes = []
    page = 1
    per_page = 50  # Tek seferde alınabilecek maksimum bölüm sayısı
    
    while True:
        api_url = f"https://www.nowtv.com.tr/ajax/load-more-video"
        payload = {
            'type': '2',  # Bölüm tipi (2 = bölümler)
            'filter': 'season',
            'program_id': program_id,
            'season': str(season),
            'orderby': 'id',
            'sorting': 'DESC',
            'page': str(page),
            'rows': str(per_page)
        }
        
        try:
            print(f"   📡 API Sayfa {page} isteniyor...")
            response = scraper.post(api_url, data=payload, timeout=15)
            
            if response.status_code != 200:
                print(f"   ⚠️ API hatası: {response.status_code}")
                break
                
            data = response.json()
            
            if not data.get('html'):
                print(f"   ✅ Tüm bölümler alındı (toplam {len(all_episodes)} bölüm)")
                break
                
            # HTML'i parse et
            soup = BeautifulSoup(data['html'], 'html.parser')
            episode_items = soup.find_all('div', class_='list-item')
            
            if not episode_items:
                break
                
            for item in episode_items:
                # Bölüm linkini bul
                link_tag = item.find('a', href=re.compile(r'/bolum/\d+'))
                if link_tag:
                    bolum_url = BASE_URL + link_tag['href'] if link_tag['href'].startswith('/') else link_tag['href']
                    
                    # Bölüm adını bul
                    title_tag = item.select_one('.program-name strong, .program-name')
                    bolum_title = title_tag.get_text(strip=True) if title_tag else "Bölüm"
                    
                    # Açıklamayı bul
                    desc_tag = item.select_one('.program-desc')
                    if desc_tag:
                        # ALT YAZILI kısmını temizle
                        for span in desc_tag.find_all('div', class_='icon'):
                            span.decompose()
                        bolum_desc = desc_tag.get_text(strip=True)
                    else:
                        bolum_desc = ""
                    
                    # Resim URL'sini bul
                    img_tag = item.find('img')
                    bolum_img = img_tag['src'] if img_tag and 'src' in img_tag.attrs else ""
                    
                    all_episodes.append({
                        'url': bolum_url,
                        'title': bolum_title,
                        'desc': bolum_desc,
                        'img': bolum_img
                    })
            
            print(f"   📥 Sayfa {page}: {len(episode_items)} bölüm eklendi")
            
            # Daha fazla veri var mı kontrol et
            if len(episode_items) < per_page:
                print(f"   ✅ Son sayfaya ulaşıldı (toplam {len(all_episodes)} bölüm)")
                break
                
            page += 1
            time.sleep(1)  # API'ye fazla yüklenmemek için
            
        except Exception as e:
            print(f"   ❌ API hatası: {e}")
            break
    
    return all_episodes

def get_program_id_from_page(scraper, bolumler_url):
    """Sayfadaki program_id'yi bul"""
    try:
        response = scraper.get(bolumler_url, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 1. Yöntem: Daha fazla butonundan program_id'yi al
        load_more_btn = soup.find('a', class_='ajax-load-more-video')
        if load_more_btn and 'data-program-id' in load_more_btn.attrs:
            return load_more_btn['data-program-id']
        
        # 2. Yöntem: Sayfa kaynağında program_id'yi ara
        program_id_match = re.search(r'"programId"\s*:\s*(\d+)', response.text)
        if program_id_match:
            return program_id_match.group(1)
        
        # 3. Yöntem: URL'den slug'ı kullan
        slug_match = re.search(r'nowtv\.com\.tr/([^/]+)/bolumler', bolumler_url)
        if slug_match:
            slug = slug_match.group(1)
            # Slug'ı program_id ile eşleştirebileceğiniz bir mapping yapabilirsiniz
            # Şimdilik None döndürüyoruz
            
        return None
    except Exception as e:
        print(f"   ⚠️ program_id alınamadı: {e}")
        return None

def run_scraper():
    print("🚀 Bot Başlatıldı. Kaynak JSON okunuyor...")
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
    
    try:
        source_resp = scraper.get(JSON_SOURCE_URL)
        target_series = json.loads(source_resp.text)
    except Exception as e:
        print(f"❌ JSON okuma hatası: {e}")
        return

    memory_data = {}

    for dizi_key, info in target_series.items():
        title = info['isim']
        dizi_url = info['link']
        poster = info['resim']
        
        # URL'yi /bolumler formatına çevir
        bolumler_url = dizi_url.replace('/izle', '/bolumler')
        
        print(f"\n📺 {title} taranıyor -> {bolumler_url}")
        
        try:
            # Önce program_id'yi al
            program_id = get_program_id_from_page(scraper, bolumler_url)
            
            if not program_id:
                print(f"   ⚠️ program_id bulunamadı, alternatif yöntem deneniyor...")
                # Alternatif yöntem: Manuel mapping yapabilirsiniz
                # Örnek: "sakincali" -> "1823" gibi
                # program_id = get_program_id_from_slug(dizi_key)
                continue
            
            print(f"   🔍 Program ID: {program_id}")
            
            # API'den tüm bölümleri al
            all_episodes_data = get_all_episodes_from_api(scraper, program_id)
            
            eps = []
            for ep_data in all_episodes_data:
                # M3U8 linkini çek
                m3u8 = get_now_m3u8(scraper, ep_data['url'])
                
                # Bölüm başlığını temizle
                clean_title = re.sub(r'\s*\.\s*Bölüm\s*$', '', ep_data['title'], flags=re.IGNORECASE)
                
                if not any(e['link'] == m3u8 for e in eps):
                    eps.append({
                        "ad": clean_title,
                        "link": m3u8,
                        "aciklama": ep_data['desc'][:200] if ep_data['desc'] else "",  # Kısa açıklama
                        "resim": ep_data['img'] if ep_data['img'] else poster
                    })
                    print(f"   ✅ {clean_title}")
            
            if eps:
                memory_data[dizi_key] = {
                    "isim": title,
                    "resim": poster,
                    "program_id": program_id,  # Gelecekte kullanmak için sakla
                    "bolumler": eps
                }
                print(f"   📊 Toplam {len(eps)} bölüm eklendi")
            else:
                print(f"   ⚠️ Hiç bölüm bulunamadı")
                
        except Exception as e:
            print(f"   ❌ {title} işlenirken hata: {e}")
            import traceback
            traceback.print_exc()

    create_html(memory_data)

def create_html(series_data):
    file_name = "nowtv_vod.html"
    json_embedded = json.dumps(series_data, ensure_ascii=False)
    
    html_template = f'''<!DOCTYPE html>
<html lang="tr">
<head>
    <title>NOW VOD PLAYER</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{ margin: 0; background: #080808; color: #fff; font-family: 'Segoe UI', Tahoma, sans-serif; }}
        .navbar {{ background: #000; padding: 15px 30px; border-bottom: 2px solid #f50057; display: flex; justify-content: space-between; align-items: center; position: sticky; top: 0; z-index: 100; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 20px; padding: 30px; }}
        .card {{ background: #121212; border-radius: 10px; overflow: hidden; cursor: pointer; transition: 0.3s; border: 1px solid #222; }}
        .card:hover {{ transform: scale(1.05); border-color: #f50057; box-shadow: 0 0 15px rgba(245, 0, 87, 0.3); }}
        .card img {{ width: 100%; aspect-ratio: 2/3; object-fit: cover; }}
        .card-name {{ padding: 10px; text-align: center; font-size: 14px; font-weight: bold; }}
        .player-view {{ position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: #000; z-index: 1000; display: none; }}
        .btn {{ background: #f50057; color: #fff; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; font-weight: bold; margin: 10px; }}
        .hidden {{ display: none !important; }}
        .episode-desc {{ font-size: 12px; color: #aaa; padding: 5px 10px; overflow: hidden; text-overflow: ellipsis; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; }}
    </style>
</head>
<body>
    <div class="navbar">
        <div style="font-size: 24px; font-weight: bold; color: #f50057;">METV NOW VOD</div>
        <input type="text" id="searchInput" placeholder="Dizi ara..." oninput="search()" style="padding: 8px; border-radius: 20px; border: none; width: 200px;">
    </div>
    
    <div id="mainGrid" class="grid"></div>
    <div id="episodeGrid" class="grid hidden"></div>
    
    <div id="playerView" class="player-view">
        <button class="btn" onclick="closePlayer()">✕ KAPAT</button>
        <div id="videoContainer" style="height: calc(100% - 70px);"></div>
    </div>

    <script>
        const seriesData = {json_embedded};
        const BRADMAX = "{BRADMAX_PLAYER}";

        function init() {{
            const grid = document.getElementById("mainGrid");
            Object.keys(seriesData).forEach(id => {{
                const d = seriesData[id];
                const card = document.createElement("div");
                card.className = "card";
                card.innerHTML = `<img src="${{d.resim}}" onerror="this.src='https://via.placeholder.com/160x240?text=NO+IMAGE'"><div class="card-name">${{d.isim}}</div>`;
                card.onclick = () => showEpisodes(id);
                grid.appendChild(card);
            }});
        }}

        function showEpisodes(id) {{
            window.scrollTo(0,0);
            document.getElementById("mainGrid").classList.add("hidden");
            const eg = document.getElementById("episodeGrid");
            eg.classList.remove("hidden");
            eg.innerHTML = `<div style="grid-column: 1/-1;"><button class="btn" onclick="goBack()">← DİZİLER</button><h2 style="display:inline; margin-left:20px;">${{seriesData[id].isim}}</h2><span style="margin-left:20px; color:#888;">(${{seriesData[id].bolumler.length}} bölüm)</span></div>`;
            
            seriesData[id].bolumler.forEach(ep => {{
                const card = document.createElement("div");
                card.className = "card";
                const epImg = ep.resim || seriesData[id].resim;
                card.innerHTML = `
                    <img src="${{epImg}}" onerror="this.src='${{seriesData[id].resim}}'">
                    <div class="card-name">${{ep.ad}}</div>
                    ${{ep.aciklama ? `<div class="episode-desc">${{ep.aciklama}}</div>` : ''}}
                `;
                card.onclick = () => playVideo(ep.link);
                eg.appendChild(card);
            }});
        }}

        function playVideo(link) {{
            document.getElementById("playerView").style.display = "block";
            let u = link.includes(".m3u8") ? BRADMAX + encodeURIComponent(link) : link;
            document.getElementById("videoContainer").innerHTML = `<iframe src="${{u}}&autoplay=true" width="100%" height="100%" frameborder="0" allowfullscreen></iframe>`;
        }}

        function closePlayer() {{
            document.getElementById("playerView").style.display = "none";
            document.getElementById("videoContainer").innerHTML = "";
        }}

        function goBack() {{
            document.getElementById("episodeGrid").classList.add("hidden");
            document.getElementById("mainGrid").classList.remove("hidden");
        }}

        function search() {{
            let q = document.getElementById("searchInput").value.toLowerCase();
            document.querySelectorAll("#mainGrid .card").forEach(c => {{
                const cardText = c.querySelector('.card-name').textContent.toLowerCase();
                c.style.display = cardText.includes(q) ? "" : "none";
            }});
        }}
        init();
    </script>
</body>
</html>'''

    with open(file_name, "w", encoding="utf-8") as f:
        f.write(html_template)
    
    print(f"\n✅ HTML oluşturuldu: {file_name}")
    commit_and_push(file_name)

if __name__ == "__main__":
    run_scraper()

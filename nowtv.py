import cloudscraper
from bs4 import BeautifulSoup
import json
import time
import re
import logging
from urllib.parse import urljoin, urlparse

# Loglama ayarları
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BASE_URL = "https://www.nowtv.com.tr"
MAIN_URL = "https://www.nowtv.com.tr/dizi-arsivi"

def slugify(text):
    mapping = {'ç': 'c', 'ğ': 'g', 'ı': 'i', 'ö': 'o', 'ş': 's', 'ü': 'u', 'Ç': 'c', 'Ğ': 'g', 'İ': 'i', 'Ö': 'o', 'Ş': 's', 'Ü': 'u'}
    text = str(text).lower().strip()
    for tr, en in mapping.items(): 
        text = text.replace(tr, en)
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    return re.sub(r'[\s-]+', '-', text).strip('-')

def clean_url(url, base_url=BASE_URL):
    if not url: 
        return ""
    if url.startswith('//'):
        return 'https:' + url
    if url.startswith('/'):
        return base_url + url
    if not url.startswith(('http://', 'https://')):
        return base_url + '/' + url.lstrip('/')
    return url

def extract_m3u8_url(scraper, episode_url):
    """Bölüm sayfasından m3u8 URL'sini çıkarır"""
    try:
        logger.debug(f"m3u8 aranıyor: {episode_url}")
        resp = scraper.get(episode_url, timeout=15)
        
        if "Teknik bir sorun" in resp.text:
            logger.warning(f"Sayfa engellendi: {episode_url}")
            return ""
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # 1. Video player script'inde m3u8 ara
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string:
                # m3u8 pattern'leri ara
                patterns = [
                    r'["\'](https?://[^"\']+\.m3u8[^"\']*)["\']',
                    r'["\'](https?://[^"\']+\.smil/[^"\']*\.m3u8)["\']',
                    r'source:\s*["\'](https?://[^"\']+\.m3u8)["\']',
                    r'file:\s*["\'](https?://[^"\']+\.m3u8)["\']'
                ]
                
                for pattern in patterns:
                    matches = re.findall(pattern, script.string)
                    for match in matches:
                        if 'm3u8' in match:
                            logger.info(f"m3u8 bulundu: {match[:100]}...")
                            return clean_url(match)
        
        # 2. Video tag'inde ara
        video_tags = soup.find_all('video')
        for video in video_tags:
            source = video.get('src')
            if source and 'm3u8' in source:
                return clean_url(source)
            
            # source tag'leri kontrol et
            source_tags = video.find_all('source')
            for source_tag in source_tags:
                src = source_tag.get('src')
                if src and 'm3u8' in src:
                    return clean_url(src)
        
        # 3. Iframe içinde ara
        iframes = soup.find_all('iframe')
        for iframe in iframes:
            src = iframe.get('src')
            if src and ('bradmax' in src or 'm3u8' in src):
                # Iframe'i aç ve içindeki m3u8'i bul
                try:
                    iframe_resp = scraper.get(clean_url(src), timeout=10)
                    iframe_soup = BeautifulSoup(iframe_resp.text, 'html.parser')
                    
                    # Iframe içinde m3u8 ara
                    iframe_patterns = [
                        r'["\'](https?://[^"\']+\.m3u8)["\']',
                        r'mediaUrl[=:]\s*["\']([^"\']+)["\']'
                    ]
                    
                    for pattern in iframe_patterns:
                        matches = re.findall(pattern, iframe_resp.text)
                        for match in matches:
                            if 'm3u8' in match:
                                return clean_url(match)
                except:
                    continue
        
        logger.warning(f"m3u8 bulunamadı: {episode_url}")
        return ""
        
    except Exception as e:
        logger.error(f"m3u8 çekme hatası: {e}")
        return ""

def extract_season_episodes(scraper, series_url):
    """Dizi için tüm sezon ve bölümleri bulur"""
    episodes = []
    
    try:
        # Dizi ana sayfasını al
        resp = scraper.get(series_url, timeout=15)
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Sezon linklerini bul (varsa)
        season_links = []
        
        # Sezon selector'ları
        season_selectors = [
            'a[href*="/sezon"]',
            'a[href*="/season"]',
            '.season-list a',
            '.seasons a'
        ]
        
        for selector in season_selectors:
            found = soup.select(selector)
            if found:
                season_links = [clean_url(a['href']) for a in found]
                break
        
        # Eğer sezon linki yoksa, doğrudan bölüm sayfasını dene
        if not season_links:
            # Bölümler genellikle /bolumler sayfasında
            bolumler_url = series_url.replace('/izle', '/bolumler')
            season_links = [bolumler_url]
        
        # Her sezon için bölümleri topla
        for season_url in season_links[:3]:  # İlk 3 sezon ile sınırla
            try:
                season_resp = scraper.get(season_url, timeout=15)
                season_soup = BeautifulSoup(season_resp.text, 'html.parser')
                
                # Bölüm linklerini bul
                episode_selectors = [
                    'a[href*="/bolum/"]',
                    '.episode-list a',
                    '.list-item a',
                    'a.episode-item'
                ]
                
                for selector in episode_selectors:
                    episode_links = season_soup.select(selector)
                    if episode_links:
                        for link in episode_links:
                            episode_url = clean_url(link['href'])
                            
                            # Bölüm numarasını çıkar
                            ep_match = re.search(r'/bolum/(\d+)', episode_url)
                            ep_num = ep_match.group(1) if ep_match else str(len(episodes) + 1)
                            
                            # Bölüm adını bul
                            ep_name_elem = link.select_one('.title, h3, .episode-title, .program-name')
                            ep_name = ep_name_elem.get_text(strip=True) if ep_name_elem else f"Bölüm {ep_num}"
                            
                            # m3u8 URL'sini al
                            m3u8_url = extract_m3u8_url(scraper, episode_url)
                            
                            episodes.append({
                                "numara": ep_num,
                                "ad": ep_name,
                                "link": episode_url,
                                "m3u8": m3u8_url
                            })
                            
                            # Her bölüm arasında kısa bekleme
                            time.sleep(0.5)
                        
                        break  # İlk çalışan selector'da dur
                
            except Exception as e:
                logger.error(f"Sezon {season_url} hatası: {e}")
                continue
        
        # Eğer hala bölüm yoksa, direkt bölümleri ara
        if not episodes:
            logger.info(f"Doğrudan bölüm arama: {series_url}")
            
            # Sayfadaki tüm linkleri tara
            all_links = soup.find_all('a', href=True)
            for link in all_links:
                href = link['href']
                if '/bolum/' in href and href not in [ep['link'] for ep in episodes]:
                    episode_url = clean_url(href)
                    
                    # Bölüm numarası
                    ep_match = re.search(r'/bolum/(\d+)', episode_url)
                    if ep_match:
                        ep_num = ep_match.group(1)
                        ep_name = link.get_text(strip=True) or f"Bölüm {ep_num}"
                        
                        # m3u8 URL'sini al
                        m3u8_url = extract_m3u8_url(scraper, episode_url)
                        
                        episodes.append({
                            "numara": ep_num,
                            "ad": ep_name,
                            "link": episode_url,
                            "m3u8": m3u8_url
                        })
        
        # Bölümleri numaraya göre sırala
        episodes.sort(key=lambda x: int(x['numara']) if x['numara'].isdigit() else 999)
        
        logger.info(f"Toplam {len(episodes)} bölüm bulundu")
        return episodes
        
    except Exception as e:
        logger.error(f"Sezon/bölüm çekme hatası: {e}")
        return []

def extract_series_from_main(scraper):
    """Ana sayfadan dizi bilgilerini çıkarır"""
    try:
        response = scraper.get(MAIN_URL, timeout=30)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # "DAHA FAZLA" butonundan toplam dizi sayısını al
        load_more = soup.select_one('.ajax-load-more-archive')
        total_series = 106  # Varsayılan
        
        if load_more:
            data_rows = load_more.get('data-rows')
            if data_rows and data_rows.isdigit():
                total_series = int(data_rows)
                logger.info(f"Toplam {total_series} dizi var")
        
        # Dizi item'larını bul
        series_items = soup.select('.videos .list-item')
        series_data = {}
        
        for item in series_items:
            try:
                # Dizi adı
                name_tag = item.select_one('.program-name strong')
                if not name_tag:
                    continue
                    
                series_name = name_tag.get_text(strip=True)
                series_id = slugify(series_name)
                
                # Dizi linki
                link_tag = item.select_one('.list-item-image a, .list-item-meta a')
                if not link_tag:
                    continue
                    
                series_url = clean_url(link_tag['href'])
                
                # Görsel
                img_tag = item.find('img')
                series_img = ""
                if img_tag:
                    img_src = img_tag.get('src') or img_tag.get('data-src', '')
                    series_img = clean_url(img_src)
                
                # Açıklama
                desc_tag = item.select_one('.program-desc')
                series_desc = desc_tag.get_text(strip=True) if desc_tag else ""
                
                logger.info(f"🔍 Dizi işleniyor: {series_name}")
                
                # Bölümleri çek (isteğe bağlı, uzun sürebilir)
                episodes = []
                try:
                    episodes = extract_season_episodes(scraper, series_url)
                    logger.info(f"  ✅ {len(episodes)} bölüm bulundu")
                except Exception as e:
                    logger.warning(f"  ⚠️ Bölüm çekilemedi: {e}")
                
                # Veriyi kaydet
                series_data[series_id] = {
                    "isim": series_name,
                    "resim": series_img,
                    "link": series_url,
                    "aciklama": series_desc,
                    "bolumler": episodes,
                    "bolum_sayisi": len(episodes)
                }
                
                # Her dizi arasında bekle
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Dizi işleme hatası: {e}")
                continue
        
        return series_data
        
    except Exception as e:
        logger.error(f"Ana sayfa çekme hatası: {e}")
        return {}

def simulate_ajax_load(scraper):
    """AJAX ile ek diziler yükler"""
    logger.info("🔄 AJAX ile ek diziler yükleniyor...")
    
    series_data = {}
    page = 1
    max_pages = 10  # Maksimum sayfa sayısı
    
    while page <= max_pages:
        try:
            # AJAX endpoint tahmini
            ajax_url = f"https://www.nowtv.com.tr/ajax/dizi-arsivi?page={page}&count=10"
            
            logger.info(f"📄 Sayfa {page} deneniyor...")
            response = scraper.get(ajax_url, timeout=15)
            
            if response.status_code != 200:
                logger.info(f"Sayfa {page} sona erdi")
                break
            
            # JSON mu HTML mi kontrol et
            try:
                data = response.json()
                # JSON formatını parse et
                logger.info(f"JSON verisi alındı")
                break  # Çık, çünkü API bulundu
            except:
                # HTML ise parse et
                soup = BeautifulSoup(response.text, 'html.parser')
                items = soup.select('.list-item')
                
                if not items:
                    logger.info("Daha fazla dizi yok")
                    break
                
                # Buradaki item'ları işle
                logger.info(f"{len(items)} dizi bulundu")
                
            page += 1
            time.sleep(2)
            
        except Exception as e:
            logger.error(f"AJAX sayfa {page} hatası: {e}")
            break
    
    return series_data

def run_scraper():
    logger.info("🚀 NowTV Scraper Başlatılıyor...")
    
    # Cloudscraper yapılandırması
    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'desktop': True,
            'mobile': False
        },
        delay=10
    )
    
    # Headers
    scraper.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
        'Referer': 'https://www.nowtv.com.tr/'
    })
    
    # 1. Ana sayfadan dizileri çek
    series_data = extract_series_from_main(scraper)
    
    # 2. Eğer az dizi varsa, AJAX ile daha fazla yükle
    if len(series_data) < 10:
        logger.info("Az dizi bulundu, AJAX deneniyor...")
        more_data = simulate_ajax_load(scraper)
        # more_data'yı series_data'ya ekle (gerekirse)
    
    # 3. Verileri kaydet
    if series_data:
        # JSON dosyası
        with open('nowtv_complete.json', 'w', encoding='utf-8') as f:
            json.dump(series_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✅ Toplam {len(series_data)} dizi kaydedildi")
        
        # HTML arayüz oluştur
        create_html_interface(series_data)
    else:
        logger.error("❌ Hiç dizi bulunamadı!")
        
        # Debug için sayfayı kaydet
        try:
            resp = scraper.get(MAIN_URL)
            with open('debug_page.html', 'w', encoding='utf-8') as f:
                f.write(resp.text)
            logger.info("Debug sayfası kaydedildi: debug_page.html")
        except:
            pass

def create_html_interface(series_data):
    """Modern HTML arayüzü oluşturur"""
    html_template = f'''<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NOW TV Dizi Arşivi</title>
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root {{
            --primary: #e50914;
            --dark: #141414;
            --light: #f5f5f1;
            --gray: #808080;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ background: var(--dark); color: var(--light); font-family: Arial, sans-serif; }}
        .header {{ background: linear-gradient(to bottom, #000 0%, transparent 100%); padding: 20px 50px; }}
        .logo {{ color: var(--primary); font-size: 2.5rem; font-weight: bold; }}
        .container {{ padding: 30px; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 25px; }}
        .card {{ background: #1a1a1a; border-radius: 8px; overflow: hidden; transition: transform 0.3s; }}
        .card:hover {{ transform: scale(1.05); }}
        .card-img {{ width: 100%; height: 350px; object-fit: cover; }}
        .card-info {{ padding: 20px; }}
        .card-title {{ font-size: 1.2rem; margin-bottom: 10px; }}
        .card-episodes {{ color: var(--primary); font-size: 0.9rem; }}
        .player-overlay {{ position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.9); display: none; z-index: 1000; }}
        .player-container {{ width: 90%; max-width: 1200px; margin: 50px auto; background: #000; padding: 20px; border-radius: 10px; }}
        .search {{ margin: 20px 0; padding: 10px; width: 100%; background: #333; color: white; border: none; border-radius: 4px; }}
    </style>
</head>
<body>
    <div class="header">
        <div class="logo">NOW TV</div>
    </div>
    
    <div class="container">
        <input type="text" class="search" placeholder="Dizi ara..." id="searchInput">
        <div class="grid" id="seriesGrid"></div>
    </div>
    
    <div class="player-overlay" id="playerOverlay">
        <div class="player-container">
            <button onclick="closePlayer()" style="float:right; background:var(--primary); color:white; border:none; padding:10px 20px; border-radius:4px;">Kapat</button>
            <div id="playerContent" style="margin-top: 50px;"></div>
        </div>
    </div>

    <script>
        const seriesData = {json.dumps(series_data, ensure_ascii=False)};
        
        function renderSeries() {{
            const grid = document.getElementById('seriesGrid');
            grid.innerHTML = '';
            
            Object.values(seriesData).forEach(series => {{
                const card = document.createElement('div');
                card.className = 'card';
                card.innerHTML = `
                    <img src="${{series.resim || 'https://via.placeholder.com/250x350'}}" class="card-img">
                    <div class="card-info">
                        <div class="card-title">${{series.isim}}</div>
                        <div class="card-episodes">${{series.bolum_sayisi || 0}} bölüm</div>
                    </div>
                `;
                card.onclick = () => showEpisodes('${{series.isim}}');
                grid.appendChild(card);
            }});
        }}
        
        function showEpisodes(seriesName) {{
            const series = Object.values(seriesData).find(s => s.isim === seriesName);
            if (!series) return;
            
            let episodesHTML = `<h2>${{series.isim}} - Bölümler</h2>`;
            if (series.bolumler && series.bolumler.length > 0) {{
                series.bolumler.forEach(ep => {{
                    episodesHTML += `
                        <div style="margin: 10px 0; padding: 10px; background: #222;">
                            <strong>Bölüm ${{ep.numara}}:</strong> ${{ep.ad}}
                            ${ep.m3u8 ? `<button onclick="playM3U8('${ep.m3u8}')" style="margin-left:10px; background:var(--primary); color:white; border:none; padding:5px 10px;">Oynat</button>` : ''}
                        </div>
                    `;
                }});
            }} else {{
                episodesHTML += `<p>Bölüm bilgisi bulunamadı.</p>`;
            }}
            
            document.getElementById('playerContent').innerHTML = episodesHTML;
            document.getElementById('playerOverlay').style.display = 'block';
        }}
        
        function playM3U8(url) {{
            if (!url) {{
                alert('Video URL bulunamadı!');
                return;
            }}
            document.getElementById('playerContent').innerHTML = `
                <video controls autoplay style="width:100%; height:70vh;">
                    <source src="${{url}}" type="application/x-mpegURL">
                </video>
            `;
        }}
        
        function closePlayer() {{
            document.getElementById('playerOverlay').style.display = 'none';
            document.getElementById('playerContent').innerHTML = '';
        }}
        
        // Arama fonksiyonu
        document.getElementById('searchInput').addEventListener('input', function(e) {{
            const searchTerm = e.target.value.toLowerCase();
            const cards = document.querySelectorAll('.card');
            cards.forEach(card => {{
                const title = card.querySelector('.card-title').textContent.toLowerCase();
                card.style.display = title.includes(searchTerm) ? 'block' : 'none';
            }});
        }});
        
        window.onload = renderSeries;
    </script>
</body>
</html>'''
    
    with open('nowtv_interface.html', 'w', encoding='utf-8') as f:
        f.write(html_template)
    
    logger.info("✅ HTML arayüzü oluşturuldu: nowtv_interface.html")

if __name__ == "__main__":
    run_scraper()

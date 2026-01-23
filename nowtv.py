import cloudscraper
from bs4 import BeautifulSoup
import json
import time
import re
import os
import subprocess
import logging
from urllib.parse import urljoin, urlparse

# Log ayarları
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# NowTV ayarları
BASE_URL = "https://www.nowtv.com.tr"
MAIN_URL = "https://www.nowtv.com.tr/dizi-arsivi"

def slugify(text):
    """Türkçe karakterleri dönüştür ve URL uyumlu hale getir"""
    if not text:
        return ""
    
    mapping = {
        'ç': 'c', 'ğ': 'g', 'ı': 'i', 'ö': 'o',
        'ş': 's', 'ü': 'u',
        'Ç': 'c', 'Ğ': 'g', 'İ': 'i', 'Ö': 'o',
        'Ş': 's', 'Ü': 'u'
    }
    
    text = str(text).lower().strip()
    
    for tr, en in mapping.items():
        text = text.replace(tr, en)
    
    # Özel karakterleri kaldır
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'[\s-]+', '-', text)
    text = text.strip('-')
    
    return text

def commit_and_push(file_name):
    """GitHub Actions ortamında dosyayı repoya push eder."""
    if not (os.getenv('GITHUB_ACTIONS') == 'true' or os.path.exists('.git')):
        logger.info("Git ortamı değil, push atlanıyor")
        return
    
    logger.info(f"📤 {file_name} GitHub'a gönderiliyor...")
    try:
        subprocess.run(["git", "config", "--global", "user.name", "github-actions[bot]"], 
                      check=True, capture_output=True)
        subprocess.run(["git", "config", "--global", "user.email", "github-actions[bot]@users.noreply.github.com"], 
                      check=True, capture_output=True)
        
        subprocess.run(["git", "add", file_name], check=True, capture_output=True)
        
        status = subprocess.run(["git", "status", "--porcelain"], 
                               capture_output=True, text=True).stdout
        
        if status:
            commit_msg = f"🔄 NowTV Arşiv Güncellendi - {time.strftime('%Y-%m-%d %H:%M')}"
            subprocess.run(["git", "commit", "-m", commit_msg], 
                          check=True, capture_output=True)
            subprocess.run(["git", "push"], check=True, capture_output=True)
            logger.info("🚀 GitHub Reponuza başarıyla yüklendi!")
        else:
            logger.info("ℹ️ Değişiklik yok, commit atlanıyor.")
            
    except Exception as e:
        logger.error(f"❌ Git Hatası: {e}")

def clean_url(url):
    """URL'yi temizle ve tam URL haline getir"""
    if not url:
        return ""
    
    url = url.strip()
    
    if url.startswith('//'):
        url = 'https:' + url
    elif url.startswith('/'):
        url = BASE_URL + url
    elif not url.startswith(('http://', 'https://')):
        url = BASE_URL + '/' + url.lstrip('/')
    
    return url

def extract_series_info(scraper, series_url):
    """Dizi sayfasından detaylı bilgileri çek"""
    try:
        logger.debug(f"Dizi detayları çekiliyor: {series_url}")
        resp = scraper.get(series_url, timeout=20)
        
        if resp.status_code != 200:
            logger.warning(f"Dizi sayfası yüklenemedi: {resp.status_code}")
            return []
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Bölümleri bulmak için çeşitli selector'lar
        episode_selectors = [
            '.list-item', '.video-item', '.episode-card',
            '.season-episodes .item', '[class*="episode"]',
            'div[data-episode]', 'a[href*="/bolum"]'
        ]
        
        episodes = []
        
        for selector in episode_selectors:
            episode_elements = soup.select(selector)
            if episode_elements and len(episode_elements) > 0:
                logger.info(f"{selector} ile {len(episode_elements)} bölüm bulundu")
                
                for ep in episode_elements[:50]:  # İlk 50 bölüm
                    try:
                        # Link bul
                        link_elem = ep.find('a', href=True)
                        if not link_elem:
                            continue
                        
                        episode_url = clean_url(link_elem['href'])
                        
                        # Başlık bul
                        title_elem = ep.select_one('h3, h2, .title, .program-name, .episode-title')
                        title = title_elem.get_text(strip=True) if title_elem else "Bölüm"
                        
                        # Görsel bul
                        img_elem = ep.find('img')
                        thumbnail = ""
                        if img_elem:
                            img_src = img_elem.get('src') or img_elem.get('data-src', '')
                            thumbnail = clean_url(img_src)
                        
                        episodes.append({
                            "ad": title,
                            "link": episode_url,
                            "thumbnail": thumbnail
                        })
                        
                    except Exception as e:
                        logger.debug(f"Bölüm parse hatası: {e}")
                        continue
                
                if episodes:
                    break
        
        # Eğer bölüm bulunamazsa, tüm bölümler linkini dene
        if not episodes:
            logger.info("Bölüm bulunamadı, alternatif yöntem deneniyor...")
            
            # /bolumler veya /sezon sayfasını kontrol et
            bolumler_url = series_url.rstrip('/') + "/bolumler"
            resp2 = scraper.get(bolumler_url, timeout=15)
            
            if resp2.status_code == 200:
                soup2 = BeautifulSoup(resp2.text, 'html.parser')
                
                # Tüm linkleri kontrol et
                all_links = soup2.find_all('a', href=True)
                for link in all_links:
                    href = link['href']
                    if '/bolum' in href or 'sezon' in href:
                        episode_url = clean_url(href)
                        title = link.get_text(strip=True) or f"Bölüm {len(episodes)+1}"
                        episodes.append({
                            "ad": title,
                            "link": episode_url,
                            "thumbnail": ""
                        })
        
        logger.info(f"Toplam {len(episodes)} bölüm bulundu")
        return episodes[::-1]  # Eskiden yeniye sırala
        
    except Exception as e:
        logger.error(f"Dizi detay çekme hatası: {e}")
        return []

def get_main_page_series(scraper):
    """Ana sayfadaki dizileri çek"""
    logger.info("📺 Ana sayfa taranıyor...")
    
    try:
        response = scraper.get(MAIN_URL, timeout=30)
        
        if response.status_code != 200:
            logger.error(f"Ana sayfa yüklenemedi: {response.status_code}")
            return {}
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # HTML'deki yapıya göre selector'lar
        series_selectors = [
            '.list-item',  # Verdiğin HTML'deki class
            '.program-card',
            '.dizi-item',
            'div[class*="item"]:has(a[href*="/"])',
            'a[href*="/dizi"]'
        ]
        
        series_data = {}
        
        for selector in series_selectors:
            series_items = soup.select(selector)
            if series_items and len(series_items) > 3:  # En az 3 öğe
                logger.info(f"{selector} ile {len(series_items)} dizi bulundu")
                
                for item in series_items:
                    try:
                        # Link bul
                        link_elem = item.find('a', href=True)
                        if not link_elem:
                            continue
                        
                        series_url = clean_url(link_elem['href'])
                        
                        # Dizi adını bul
                        name_selectors = [
                            '.program-name', '.title', 'h2', 'h3',
                            '.caption', 'strong'
                        ]
                        
                        series_name = ""
                        for name_selector in name_selectors:
                            name_elem = item.select_one(name_selector)
                            if name_elem:
                                series_name = name_elem.get_text(strip=True)
                                if series_name and len(series_name) > 2:
                                    break
                        
                        if not series_name:
                            # URL'den dizi adını çıkar
                            parsed_url = urlparse(series_url)
                            path_parts = parsed_url.path.split('/')
                            if len(path_parts) > 1:
                                series_name = path_parts[1].replace('-', ' ').title()
                        
                        if not series_name:
                            continue
                        
                        # Slug oluştur
                        series_id = slugify(series_name)
                        
                        if series_id in series_data:
                            logger.debug(f"{series_name} zaten eklenmiş, atlanıyor")
                            continue
                        
                        # Görsel bul
                        img_elem = item.find('img')
                        thumbnail = ""
                        if img_elem:
                            img_src = img_elem.get('src') or img_elem.get('data-src', '')
                            thumbnail = clean_url(img_src)
                        
                        logger.info(f"  🔍 {series_name} işleniyor...")
                        
                        # Bölümleri al
                        episodes = extract_series_info(scraper, series_url)
                        
                        if episodes:
                            series_data[series_id] = {
                                "isim": series_name,
                                "resim": thumbnail,
                                "link": series_url,
                                "bolumler": episodes
                            }
                            logger.info(f"    ✅ {len(episodes)} bölüm eklendi")
                        else:
                            logger.warning(f"    ⚠️ {series_name} için bölüm bulunamadı")
                        
                        time.sleep(0.5)  # Rate limiting
                        
                    except Exception as e:
                        logger.error(f"    ❌ Dizi işleme hatası: {e}")
                        continue
                
                if series_data:
                    break
        
        return series_data
        
    except Exception as e:
        logger.error(f"Ana sayfa çekme hatası: {e}")
        return {}

def load_more_series(scraper):
    """Daha Fazla butonuna tıklayarak ek diziler yükle"""
    logger.info("🔄 Ek diziler yükleniyor...")
    
    # Bu fonksiyon JavaScript ile yüklenen içerik için kullanılabilir
    # NowTV'nin yapısına göre AJAX endpoint'ini bulmamız gerekebilir
    
    try:
        # AJAX endpoint'ini tahmin et
        ajax_urls = [
            f"{BASE_URL}/api/series",
            f"{BASE_URL}/diziler/load-more",
            f"{BASE_URL}/ajax/series"
        ]
        
        for ajax_url in ajax_urls:
            try:
                response = scraper.get(ajax_url, timeout=15)
                if response.status_code == 200:
                    data = response.json()
                    # JSON yapısını parse et
                    logger.info(f"AJAX endpoint bulundu: {ajax_url}")
                    return data
            except:
                continue
        
        logger.warning("AJAX endpoint bulunamadı")
        return {}
        
    except Exception as e:
        logger.error(f"Load more hatası: {e}")
        return {}

def run_scraper():
    """Ana scraping fonksiyonu"""
    logger.info("🚀 NowTV Web Scraper Başlatıldı")
    logger.info(f"Hedef URL: {MAIN_URL}")
    
    # Cloudscraper oluştur
    try:
        scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'desktop': True,
                'mobile': False
            },
            delay=10
        )
        
        # Headers güncelle
        scraper.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0'
        })
        
        # Ana sayfadan dizileri çek
        series_data = get_main_page_series(scraper)
        
        # Ek dizileri yükle
        if len(series_data) < 10:  # Eğer az dizi bulunduysa
            more_data = load_more_series(scraper)
            # more_data'yı parse et ve series_data'ya ekle
        
        if series_data:
            logger.info(f"✅ Toplam {len(series_data)} dizi başarıyla toplandı")
            
            # JSON olarak kaydet (debug için)
            json_file = "nowtv_data.json"
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(series_data, f, ensure_ascii=False, indent=2)
            logger.info(f"📁 Veriler {json_file} dosyasına kaydedildi")
            
            # HTML oluştur
            create_html(series_data)
        else:
            logger.error("❌ Hiç dizi bulunamadı!")
            # Debug için sayfayı kaydet
            try:
                resp = scraper.get(MAIN_URL)
                with open("debug_page.html", "w", encoding="utf-8") as f:
                    f.write(resp.text)
                logger.info("Debug sayfası kaydedildi: debug_page.html")
            except:
                pass
            
    except Exception as e:
        logger.error(f"❌ Scraper başlatma hatası: {e}")

def create_html(series_data):
    """HTML arayüzü oluştur"""
    file_name = "nowtv_vod.html"
    
    # JSON verisini hazırla
    json_data = json.dumps(series_data, ensure_ascii=False)
    
    # NowTV için özel tasarım
    html_template = f'''<!DOCTYPE html>
<html lang="tr">
<head>
    <title>NOW TV DİZİ ARŞİVİ</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="icon" href="https://www.nowtv.com.tr/favicon.ico" type="image/x-icon">
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root {{
            --primary-color: #e50914;
            --secondary-color: #221f1f;
            --accent-color: #f5f5f1;
            --card-bg: #181818;
            --hover-bg: #2a2a2a;
        }}
        
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            background-color: var(--secondary-color);
            color: var(--accent-color);
            font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
            line-height: 1.6;
            overflow-x: hidden;
            padding-bottom: 50px;
        }}
        
        .header {{
            background: linear-gradient(to bottom, rgba(0,0,0,0.9) 0%, rgba(0,0,0,0.7) 50%, transparent 100%);
            padding: 20px 40px;
            position: sticky;
            top: 0;
            z-index: 1000;
            backdrop-filter: blur(10px);
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }}
        
        .logo-area {{
            display: flex;
            align-items: center;
            gap: 15px;
            margin-bottom: 20px;
        }}
        
        .logo {{
            font-size: 32px;
            font-weight: bold;
            color: var(--primary-color);
            text-transform: uppercase;
            letter-spacing: 2px;
        }}
        
        .logo span {{
            color: var(--accent-color);
        }}
        
        .stats {{
            background: rgba(0,0,0,0.5);
            padding: 8px 15px;
            border-radius: 20px;
            font-size: 14px;
            border: 1px solid rgba(255,255,255,0.1);
        }}
        
        .search-container {{
            position: relative;
            max-width: 500px;
            margin: 0 auto;
        }}
        
        .search-input {{
            width: 100%;
            padding: 15px 20px 15px 50px;
            background: rgba(0,0,0,0.7);
            border: 2px solid rgba(255,255,255,0.2);
            border-radius: 30px;
            color: white;
            font-size: 16px;
            transition: all 0.3s ease;
        }}
        
        .search-input:focus {{
            outline: none;
            border-color: var(--primary-color);
            background: rgba(0,0,0,0.9);
        }}
        
        .search-icon {{
            position: absolute;
            left: 20px;
            top: 50%;
            transform: translateY(-50%);
            color: rgba(255,255,255,0.5);
        }}
        
        .container {{
            padding: 30px;
            max-width: 1400px;
            margin: 0 auto;
        }}
        
        .grid-title {{
            font-size: 24px;
            margin: 30px 0 20px;
            padding-left: 10px;
            border-left: 4px solid var(--primary-color);
        }}
        
        .series-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
            gap: 25px;
            margin-top: 20px;
        }}
        
        .series-card {{
            background: var(--card-bg);
            border-radius: 10px;
            overflow: hidden;
            transition: all 0.3s ease;
            cursor: pointer;
            position: relative;
        }}
        
        .series-card:hover {{
            transform: translateY(-10px) scale(1.03);
            box-shadow: 0 20px 30px rgba(0,0,0,0.5);
            background: var(--hover-bg);
        }}
        
        .series-poster {{
            width: 100%;
            height: 300px;
            object-fit: cover;
            border-bottom: 3px solid var(--primary-color);
        }}
        
        .series-info {{
            padding: 20px;
        }}
        
        .series-name {{
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 10px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        
        .episode-count {{
            color: var(--primary-color);
            font-size: 14px;
            display: flex;
            align-items: center;
            gap: 5px;
        }}
        
        .episodes-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }}
        
        .episode-card {{
            background: var(--card-bg);
            border-radius: 8px;
            overflow: hidden;
            transition: all 0.2s ease;
        }}
        
        .episode-card:hover {{
            transform: scale(1.05);
            background: var(--hover-bg);
        }}
        
        .episode-thumbnail {{
            width: 100%;
            height: 120px;
            object-fit: cover;
        }}
        
        .episode-info {{
            padding: 15px;
        }}
        
        .episode-title {{
            font-size: 14px;
            font-weight: bold;
            margin-bottom: 5px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        
        .back-button {{
            background: var(--primary-color);
            color: white;
            border: none;
            padding: 12px 25px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
            display: flex;
            align-items: center;
            gap: 10px;
            margin: 20px 0;
            transition: all 0.3s ease;
        }}
        
        .back-button:hover {{
            background: #ff0a16;
            transform: translateX(-5px);
        }}
        
        .player-overlay {{
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.95);
            z-index: 9999;
            display: none;
            align-items: center;
            justify-content: center;
        }}
        
        .player-container {{
            width: 90%;
            max-width: 1200px;
            background: black;
            border-radius: 10px;
            overflow: hidden;
            position: relative;
        }}
        
        .close-player {{
            position: absolute;
            top: 15px;
            right: 15px;
            background: var(--primary-color);
            color: white;
            border: none;
            width: 40px;
            height: 40px;
            border-radius: 50%;
            cursor: pointer;
            font-size: 20px;
            z-index: 100;
        }}
        
        .player-frame {{
            width: 100%;
            height: 70vh;
            border: none;
        }}
        
        .loading {{
            display: none;
            text-align: center;
            padding: 40px;
            font-size: 18px;
            color: var(--accent-color);
        }}
        
        .loading i {{
            font-size: 30px;
            margin-bottom: 10px;
            color: var(--primary-color);
        }}
        
        .no-results {{
            grid-column: 1 / -1;
            text-align: center;
            padding: 50px;
            color: rgba(255,255,255,0.5);
        }}
        
        @media (max-width: 768px) {{
            .series-grid {{
                grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
                gap: 15px;
            }}
            
            .container {{
                padding: 15px;
            }}
            
            .header {{
                padding: 15px;
            }}
            
            .player-frame {{
                height: 50vh;
            }}
        }}
        
        @media (max-width: 480px) {{
            .series-grid {{
                grid-template-columns: repeat(2, 1fr);
            }}
            
            .logo {{
                font-size: 24px;
            }}
        }}
    </style>
</head>
<body>
    <!-- Header -->
    <div class="header">
        <div class="logo-area">
            <div class="logo">NOW<span>TV</span></div>
            <div class="stats">
                <i class="fas fa-film"></i>
                <span id="seriesCount">0</span> Dizi
                <i class="fas fa-play-circle" style="margin-left: 15px;"></i>
                <span id="episodeCount">0</span> Bölüm
            </div>
        </div>
        
        <div class="search-container">
            <i class="fas fa-search search-icon"></i>
            <input type="text" 
                   id="searchInput" 
                   class="search-input" 
                   placeholder="Dizi ara..."
                   onkeyup="searchSeries()">
        </div>
    </div>

    <!-- Main Content -->
    <div class="container">
        <!-- Series Grid -->
        <div id="seriesContainer">
            <h2 class="grid-title">TÜM DİZİLER</h2>
            <div id="seriesGrid" class="series-grid"></div>
        </div>
        
        <!-- Episodes Grid (hidden by default) -->
        <div id="episodesContainer" style="display: none;">
            <button class="back-button" onclick="goBackToSeries()">
                <i class="fas fa-arrow-left"></i>
                Tüm Dizilere Dön
            </button>
            <h2 id="currentSeriesTitle" class="grid-title"></h2>
            <div id="episodesGrid" class="episodes-grid"></div>
        </div>
        
        <!-- Loading Indicator -->
        <div id="loading" class="loading">
            <i class="fas fa-spinner fa-spin"></i>
            <p>Yükleniyor...</p>
        </div>
        
        <!-- No Results -->
        <div id="noResults" class="no-results" style="display: none;">
            <i class="fas fa-search" style="font-size: 50px; margin-bottom: 20px;"></i>
            <h3>Sonuç bulunamadı</h3>
            <p>Aradığınız dizi bulunamadı, farklı bir anahtar kelime deneyin.</p>
        </div>
    </div>

    <!-- Video Player Overlay -->
    <div id="playerOverlay" class="player-overlay">
        <div class="player-container">
            <button class="close-player" onclick="closePlayer()">
                <i class="fas fa-times"></i>
            </button>
            <iframe id="videoFrame" class="player-frame" 
                    frameborder="0" 
                    allowfullscreen
                    allow="autoplay; encrypted-media">
            </iframe>
        </div>
    </div>

    <script>
        // Global variables
        const seriesData = {json_data};
        let currentSeriesId = null;
        
        // Initialize the page
        function init() {{
            showLoading(true);
            
            // Update stats
            const seriesCount = Object.keys(seriesData).length;
            let totalEpisodes = 0;
            
            Object.values(seriesData).forEach(series => {{
                totalEpisodes += series.bolumler ? series.bolumler.length : 0;
            }});
            
            document.getElementById('seriesCount').textContent = seriesCount;
            document.getElementById('episodeCount').textContent = totalEpisodes;
            
            // Render series
            renderSeries();
            
            showLoading(false);
        }}
        
        // Render all series
        function renderSeries(filterText = '') {{
            const grid = document.getElementById('seriesGrid');
            grid.innerHTML = '';
            
            let hasResults = false;
            const filteredSeries = {{}};
            
            // Filter series
            Object.keys(seriesData).forEach(key => {{
                const series = seriesData[key];
                const seriesName = series.isim || key.replace(/-/g, ' ');
                
                if (!filterText || seriesName.toLowerCase().includes(filterText.toLowerCase())) {{
                    filteredSeries[key] = series;
                    hasResults = true;
                }}
            }});
            
            // Show/hide no results message
            document.getElementById('noResults').style.display = hasResults ? 'none' : 'block';
            
            // Render filtered series
            Object.keys(filteredSeries).forEach(key => {{
                const series = filteredSeries[key];
                const episodeCount = series.bolumler ? series.bolumler.length : 0;
                const seriesName = series.isim || key.replace(/-/g, ' ');
                
                const card = document.createElement('div');
                card.className = 'series-card';
                card.onclick = () => showEpisodes(key);
                
                card.innerHTML = `
                    <img src="${{series.resim || 'https://via.placeholder.com/220x300/181818/FFFFFF?text=NO+IMAGE'}}" 
                         class="series-poster" 
                         alt="${{seriesName}}"
                         onerror="this.src='https://via.placeholder.com/220x300/181818/FFFFFF?text=NO+IMAGE'">
                    <div class="series-info">
                        <div class="series-name" title="${{seriesName}}">${{seriesName}}</div>
                        <div class="episode-count">
                            <i class="fas fa-play-circle"></i>
                            ${{episodeCount}} Bölüm
                        </div>
                    </div>
                `;
                
                grid.appendChild(card);
            }});
        }}
        
        // Show episodes for a specific series
        function showEpisodes(seriesId) {{
            currentSeriesId = seriesId;
            const series = seriesData[seriesId];
            const seriesName = series.isim || seriesId.replace(/-/g, ' ');
            
            // Update UI
            document.getElementById('seriesContainer').style.display = 'none';
            document.getElementById('episodesContainer').style.display = 'block';
            document.getElementById('currentSeriesTitle').textContent = seriesName;
            
            // Render episodes
            const grid = document.getElementById('episodesGrid');
            grid.innerHTML = '';
            
            if (series.bolumler && series.bolumler.length > 0) {{
                series.bolumler.forEach((episode, index) => {{
                    const card = document.createElement('div');
                    card.className = 'episode-card';
                    card.onclick = () => playEpisode(episode.link);
                    
                    const epNumber = series.bolumler.length - index;
                    const epTitle = episode.ad || `Bölüm ${{epNumber}}`;
                    
                    card.innerHTML = `
                        <img src="${{episode.thumbnail || series.resim || 'https://via.placeholder.com/200x120/181818/FFFFFF?text=EPISODE'}}" 
                             class="episode-thumbnail" 
                             alt="${{epTitle}}"
                             onerror="this.src='https://via.placeholder.com/200x120/181818/FFFFFF?text=EPISODE'">
                        <div class="episode-info">
                            <div class="episode-title" title="${{epTitle}}">${{epTitle}}</div>
                            <div style="font-size: 12px; color: #999; margin-top: 5px;">
                                <i class="far fa-play-circle"></i> Oynat
                            </div>
                        </div>
                    `;
                    
                    grid.appendChild(card);
                }});
            }} else {{
                grid.innerHTML = `
                    <div class="no-results" style="grid-column: 1 / -1;">
                        <i class="fas fa-exclamation-circle" style="font-size: 50px; margin-bottom: 20px;"></i>
                        <h3>Bölüm bulunamadı</h3>
                        <p>Bu dizi için henüz bölüm eklenmemiş.</p>
                    </div>
                `;
            }}
            
            // Scroll to top
            window.scrollTo({{top: 0, behavior: 'smooth'}});
        }}
        
        // Go back to series list
        function goBackToSeries() {{
            document.getElementById('episodesContainer').style.display = 'none';
            document.getElementById('seriesContainer').style.display = 'block';
            currentSeriesId = null;
            
            // Clear search
            document.getElementById('searchInput').value = '';
            renderSeries();
            
            // Scroll to top
            window.scrollTo({{top: 0, behavior: 'smooth'}});
        }}
        
        // Play episode
        function playEpisode(episodeUrl) {{
            showLoading(true);
            
            // Try different player methods
            let playerUrl = '';
            
            // Method 1: Direct iframe (if supported)
            if (episodeUrl.includes('nowtv.com.tr')) {{
                playerUrl = episodeUrl;
            }}
            // Method 2: Use external player service
            else {{
                playerUrl = `https://bradmax.com/client/embed-player/d9decbf0d308f4bb91825c3f3a2beb7b0aaee2f6_8493?mediaUrl=${{encodeURIComponent(episodeUrl)}}&autoplay=true`;
            }}
            
            // Set iframe source
            document.getElementById('videoFrame').src = playerUrl;
            
            // Show player
            document.getElementById('playerOverlay').style.display = 'flex';
            
            showLoading(false);
        }}
        
        // Close player
        function closePlayer() {{
            document.getElementById('playerOverlay').style.display = 'none';
            document.getElementById('videoFrame').src = '';
        }}
        
        // Search series
        function searchSeries() {{
            const searchText = document.getElementById('searchInput').value;
            renderSeries(searchText);
        }}
        
        // Show/hide loading
        function showLoading(show) {{
            document.getElementById('loading').style.display = show ? 'block' : 'none';
        }}
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {{
            // ESC to close player
            if (e.key === 'Escape') {{
                closePlayer();
            }}
            // Backspace to go back
            if (e.key === 'Backspace' && currentSeriesId) {{
                goBackToSeries();
            }}
        }});
        
        // Initialize when page loads
        window.onload = init;
    </script>
</body>
</html>'''
    
    # HTML dosyasını oluştur
    with open(file_name, "w", encoding="utf-8") as f:
        f.write(html_template)
    
    logger.info(f"✅ HTML dosyası oluşturuldu: {file_name}")
    
    # GitHub'a push et
    commit_and_push(file_name)
    
    return file_name

def main():
    """Ana fonksiyon"""
    print("=" * 60)
    print("NOW TV WEB SCRAPER")
    print("=" * 60)
    
    try:
        run_scraper()
        
        print("\n" + "=" * 60)
        print("SCRAPING TAMAMLANDI!")
        print("=" * 60)
        
    except KeyboardInterrupt:
        logger.info("Kullanıcı tarafından durduruldu")
    except Exception as e:
        logger.error(f"Ana fonksiyon hatası: {e}")

if __name__ == "__main__":
    main()

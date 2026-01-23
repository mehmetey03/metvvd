import cloudscraper
from bs4 import BeautifulSoup
import json
import time
import re

BASE_URL = "https://www.kanald.com.tr"

def slugify(text):
    """Metni URL dostu formata çevirir"""
    text = text.lower()
    tr_map = {'ı': 'i', 'ğ': 'g', 'ü': 'u', 'ş': 's', 'ö': 'o', 'ç': 'c', 'İ': 'i'}
    for tr, en in tr_map.items():
        text = text.replace(tr, en)
    text = re.sub(r'[^a-z0-9]+', '-', text)
    return text.strip('-')

def extract_episode_number(name):
    """Bölüm numarasını çıkarır (sıralama için)"""
    match = re.search(r'(\d+)\.\s*Bölüm', name, re.IGNORECASE)
    if match:
        return int(match.group(1))
    
    match = re.search(r'Bölüm\s*(\d+)', name, re.IGNORECASE)
    if match:
        return int(match.group(1))
    
    return 9999  # Numarasız bölümler en sona

def get_kanald_series():
    """Kanal D dizilerini ve bölümlerini toplar"""
    print("🚀 Kanal D Dizileri Taranıyor...")
    
    scraper = cloudscraper.create_scraper(
        browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True}
    )
    
    series_data = {}
    
    # Ana dizi listesi
    try:
        print("📡 Dizi listesi alınıyor...")
        response = scraper.get(f"{BASE_URL}/diziler", timeout=30)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        cards = soup.find_all('a', class_='poster-card')
        print(f"✅ Toplam {len(cards)} dizi bulundu\n")
        
        for idx, card in enumerate(cards, 1):
            try:
                # Dizi bilgileri
                img_tag = card.find('img')
                title = img_tag.get('alt') or img_tag.get('title') if img_tag else ""
                
                if not title:
                    href = card.get('href', '')
                    title = href.replace('/', '').replace('-', ' ').title()
                
                series_url = card.get('href', '')
                full_url = BASE_URL + series_url if series_url.startswith('/') else series_url
                
                poster = ""
                if img_tag:
                    poster = img_tag.get('data-src') or img_tag.get('src') or ""
                    if poster.startswith("//"):
                        poster = "https:" + poster
                
                if not title or len(title) < 2:
                    continue
                
                series_id = slugify(title)
                print(f"[{idx}/{len(cards)}] 📺 {title}")
                
                # Bölümleri topla
                episodes = get_series_episodes(scraper, full_url, title)
                
                if episodes:
                    series_data[series_id] = {
                        "resim": poster,
                        "bolumler": episodes
                    }
                    print(f"    ✅ {len(episodes)} bölüm eklendi\n")
                else:
                    print(f"    ⚠️ Bölüm bulunamadı\n")
                
                time.sleep(0.5)  # Rate limiting
                
            except Exception as e:
                print(f"    ❌ Hata: {e}\n")
                continue
        
        print(f"\n{'='*60}")
        print(f"🎉 Toplam {len(series_data)} dizi başarıyla işlendi!")
        print(f"{'='*60}\n")
        
        return series_data
        
    except Exception as e:
        print(f"❌ Ana sayfa hatası: {e}")
        return {}

def get_series_episodes(scraper, series_url, series_name):
    """Dizi bölümlerini toplar"""
    episodes = []
    
    try:
        response = scraper.get(series_url, timeout=30)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Bölüm linklerini bul
        episode_links = soup.find_all('a', href=re.compile(r'/bolum/'))
        
        for link in episode_links:
            episode_name = link.get_text(strip=True)
            episode_url = BASE_URL + link.get('href') if link.get('href').startswith('/') else link.get('href')
            
            # Video URL'sini çek
            video_url = get_video_url(scraper, episode_url)
            
            if video_url:
                # Bölüm adını temizle
                clean_name = episode_name.replace(series_name, '').strip()
                if not clean_name or 'İzle' in clean_name:
                    clean_name = f"{extract_episode_number(episode_name)}. Bölüm"
                
                episodes.append({
                    "ad": clean_name,
                    "link": video_url,
                    "episode_num": extract_episode_number(episode_name)
                })
                print(f"    ✓ {clean_name}")
        
        # Bölümleri sırala (1. Bölüm -> Son Bölüm)
        episodes = sorted(episodes, key=lambda x: x['episode_num'])
        
        # Sıralama numarasını kaldır
        return [{"ad": ep["ad"], "link": ep["link"]} for ep in episodes]
        
    except Exception as e:
        print(f"    ❌ Bölüm çekme hatası: {e}")
        return []

def get_video_url(scraper, episode_url):
    """Bölüm video URL'sini çeker"""
    try:
        response = scraper.get(episode_url, timeout=30)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Video player div'ini bul
        video_div = soup.find('div', {'data-video-url': True})
        if video_div:
            return video_div.get('data-video-url')
        
        # Alternatif: Script içinde video URL ara
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string and ('m3u8' in script.string or 'mp4' in script.string):
                # M3U8 veya MP4 URL'sini bul
                m3u8_match = re.search(r'https?://[^\s"\']+\.m3u8', script.string)
                if m3u8_match:
                    return m3u8_match.group(0)
                
                mp4_match = re.search(r'https?://[^\s"\']+\.mp4', script.string)
                if mp4_match:
                    return mp4_match.group(0)
        
        return None
        
    except Exception as e:
        return None

def create_html(data):
    """HTML dosyasını oluşturur"""
    json_str = json.dumps(data, ensure_ascii=False, indent=2)
    
    html_template = '''<!DOCTYPE html>
<html lang="tr">
<head>
    <title>KANAL D ARŞİVİ</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, user-scalable=no, initial-scale=1.0">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
        body { background: #00040d; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #fff; overflow-x: hidden; }
        .header { background: linear-gradient(135deg, #1a0d2e 0%, #0d0221 100%); border-bottom: 2px solid #3d2963; padding: 15px 20px; display: flex; justify-content: space-between; align-items: center; position: sticky; top: 0; z-index: 1000; box-shadow: 0 4px 20px rgba(0,0,0,0.5); }
        .logo-section { display: flex; align-items: center; gap: 12px; }
        .logo-text { font-size: 22px; font-weight: 700; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; letter-spacing: 1px; }
        .search-section { display: flex; gap: 10px; }
        .search-input { background: rgba(255, 255, 255, 0.08); border: 2px solid rgba(255, 255, 255, 0.15); border-radius: 8px; padding: 10px 15px; color: #fff; font-size: 14px; width: 250px; transition: all 0.3s; }
        .search-input:focus { outline: none; border-color: #667eea; box-shadow: 0 0 15px rgba(102, 126, 234, 0.3); }
        .search-btn { background: #667eea; border: none; color: #fff; padding: 10px 20px; border-radius: 8px; cursor: pointer; font-weight: 600; transition: all 0.3s; }
        .search-btn:hover { background: #764ba2; transform: translateY(-2px); }
        .container { padding: 30px 20px; max-width: 1600px; margin: 0 auto; }
        .page-title { font-size: 28px; margin-bottom: 25px; padding-bottom: 15px; border-bottom: 2px solid #3d2963; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .series-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 20px; }
        .series-card { background: #15161a; border-radius: 12px; overflow: hidden; border: 2px solid #323442; cursor: pointer; transition: all 0.3s; position: relative; }
        .series-card:hover { border-color: #667eea; transform: translateY(-8px); box-shadow: 0 12px 30px rgba(102, 126, 234, 0.3); }
        .series-poster { width: 100%; padding-top: 145%; position: relative; overflow: hidden; background: #0a0e1a; }
        .series-poster img { position: absolute; top: 0; left: 0; width: 100%; height: 100%; object-fit: cover; transition: transform 0.4s; }
        .series-card:hover .series-poster img { transform: scale(1.15); }
        .series-overlay { position: absolute; bottom: 0; left: 0; right: 0; background: linear-gradient(to top, rgba(0,0,0,0.95) 0%, transparent 100%); padding: 15px 10px 10px; }
        .series-name { font-size: 14px; font-weight: 600; text-align: center; line-height: 1.3; color: #fff; }
        .episodes-container { display: none; }
        .episodes-container.active { display: block; }
        .back-btn { background: #667eea; color: #fff; padding: 12px 24px; border-radius: 8px; cursor: pointer; display: inline-block; margin-bottom: 20px; font-weight: 600; transition: all 0.3s; }
        .back-btn:hover { background: #764ba2; transform: translateX(-5px); }
        .player-container { position: fixed; top: 0; left: 0; width: 100%; height: 100vh; background: #000; z-index: 9999; display: none; flex-direction: column; }
        .player-container.active { display: flex; }
        .player-header { background: rgba(0,0,0,0.9); padding: 15px 20px; display: flex; justify-content: space-between; align-items: center; }
        .player-back-btn { background: #667eea; color: #fff; padding: 10px 20px; border-radius: 8px; cursor: pointer; font-weight: 600; border: none; transition: all 0.3s; }
        .player-back-btn:hover { background: #764ba2; }
        .player-frame { flex: 1; width: 100%; height: 100%; }
        .player-frame iframe { width: 100%; height: 100%; border: none; }
        .no-results { text-align: center; padding: 60px 20px; color: rgba(255,255,255,0.5); font-size: 18px; }
        .hidden { display: none !important; }
        @media (max-width: 768px) { .search-input { width: 150px; } .series-grid { grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 15px; } .logo-text { font-size: 18px; } }
    </style>
</head>
<body>
    <div class="header">
        <div class="logo-section"><div class="logo-text">📺 KANAL D ARŞİVİ</div></div>
        <div class="search-section">
            <input type="text" class="search-input" id="searchInput" placeholder="Dizi ara...">
            <button class="search-btn" onclick="searchSeries()">ARA</button>
        </div>
    </div>
    <div class="container" id="mainContainer">
        <div class="page-title">TÜM DİZİLER</div>
        <div class="series-grid" id="seriesGrid"></div>
        <div class="no-results hidden" id="noResults">Sonuç bulunamadı 😔</div>
    </div>
    <div class="container episodes-container" id="episodesContainer">
        <div class="back-btn" onclick="backToSeries()">← Dizilere Dön</div>
        <div class="page-title" id="episodesTitle"></div>
        <div class="series-grid" id="episodesGrid"></div>
    </div>
    <div class="player-container" id="playerContainer">
        <div class="player-header">
            <button class="player-back-btn" onclick="closePlayer()">← Geri</button>
            <div id="playerTitle"></div>
        </div>
        <div class="player-frame" id="playerFrame"></div>
    </div>
    <script>
        const seriesData = ''' + json_str + ''';
        const PLAYER_BASE_URL = "https://bradmax.com/client/embed-player/d9decbf0d308f4bb91825c3f3a2beb7b0aaee2f6_8493?mediaUrl=";
        const PLAYER_PARAMS = "&autoplay=true&fs=true";
        let currentSeries = null;
        
        function init() { renderSeriesGrid(); }
        
        function renderSeriesGrid() {
            const grid = document.getElementById('seriesGrid');
            grid.innerHTML = '';
            Object.keys(seriesData).forEach(key => {
                const series = seriesData[key];
                const card = document.createElement('div');
                card.className = 'series-card';
                card.onclick = () => showEpisodes(key);
                const seriesName = key.replace(/-/g, ' ').toUpperCase();
                card.innerHTML = `<div class="series-poster"><img src="${series.resim}" alt="${seriesName}" loading="lazy" onerror="this.src='https://via.placeholder.com/264x365?text=Resim+Yok'"><div class="series-overlay"><div class="series-name">${seriesName}</div></div></div>`;
                grid.appendChild(card);
            });
        }
        
        function showEpisodes(seriesId) {
            currentSeries = seriesId;
            const series = seriesData[seriesId];
            const seriesName = seriesId.replace(/-/g, ' ').toUpperCase();
            document.getElementById('mainContainer').classList.add('hidden');
            document.getElementById('episodesContainer').classList.add('active');
            document.getElementById('episodesTitle').textContent = seriesName + ' - BÖLÜMLER';
            const grid = document.getElementById('episodesGrid');
            grid.innerHTML = '';
            series.bolumler.forEach((episode, index) => {
                const card = document.createElement('div');
                card.className = 'series-card';
                card.onclick = () => playEpisode(episode.link, seriesName, episode.ad);
                card.innerHTML = `<div class="series-poster"><img src="${series.resim}" alt="${episode.ad}" loading="lazy"><div class="series-overlay"><div class="series-name">${episode.ad}</div></div></div>`;
                grid.appendChild(card);
            });
        }
        
        function backToSeries() {
            currentSeries = null;
            document.getElementById('mainContainer').classList.remove('hidden');
            document.getElementById('episodesContainer').classList.remove('active');
        }
        
        function playEpisode(streamUrl, seriesName, episodeName) {
            document.getElementById('playerContainer').classList.add('active');
            document.getElementById('playerTitle').textContent = `${seriesName} - ${episodeName}`;
            const fullUrl = PLAYER_BASE_URL + encodeURIComponent(streamUrl) + PLAYER_PARAMS;
            const iframe = `<iframe src="${fullUrl}" allowfullscreen></iframe>`;
            document.getElementById('playerFrame').innerHTML = iframe;
        }
        
        function closePlayer() {
            document.getElementById('playerContainer').classList.remove('active');
            document.getElementById('playerFrame').innerHTML = '';
        }
        
        function searchSeries() {
            const searchTerm = document.getElementById('searchInput').value.toLowerCase();
            const grid = document.getElementById('seriesGrid');
            const cards = grid.querySelectorAll('.series-card');
            const noResults = document.getElementById('noResults');
            let found = false;
            cards.forEach(card => {
                const name = card.querySelector('.series-name').textContent.toLowerCase();
                if (name.includes(searchTerm)) { card.style.display = 'block'; found = true; } else { card.style.display = 'none'; }
            });
            if (found) { noResults.classList.add('hidden'); } else { noResults.classList.remove('hidden'); }
        }
        
        document.getElementById('searchInput').addEventListener('input', function() {
            if (this.value === '') {
                document.querySelectorAll('.series-card').forEach(card => { card.style.display = 'block'; });
                document.getElementById('noResults').classList.add('hidden');
            }
        });
        
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                if (document.getElementById('playerContainer').classList.contains('active')) { closePlayer(); }
                else if (document.getElementById('episodesContainer').classList.contains('active')) { backToSeries(); }
            }
        });
        
        init();
    </script>
</body>
</html>'''
    
    filename = "kanald_archive.html"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html_template)
    
    print(f"✨ HTML dosyası '{filename}' oluşturuldu!")

if __name__ == "__main__":
    series_data = get_kanald_series()
    if series_data:
        create_html(series_data)
        print("\n🎉 İşlem tamamlandı! 'kanald_archive.html' dosyasını açabilirsiniz.")
    else:
        print("\n❌ Hiç veri çekilemedi.")

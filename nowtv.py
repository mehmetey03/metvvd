import cloudscraper
from bs4 import BeautifulSoup
import json
import time
import re
import logging
from urllib.parse import urljoin

# Loglama ayarları - Daha temiz çıktı için WARNING seviyesine aldım
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BASE_URL = "https://www.nowtv.com.tr"
MAIN_URL = "https://www.nowtv.com.tr/dizi-arsivi"

def slugify(text):
    mapping = {'ç': 'c', 'ğ': 'g', 'ı': 'i', 'ö': 'o', 'ş': 's', 'ü': 'u', 'Ç': 'c', 'Ğ': 'g', 'İ': 'i', 'Ö': 'o', 'Ş': 's', 'Ü': 'u'}
    text = str(text).lower().strip()
    for tr, en in mapping.items(): text = text.replace(tr, en)
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    return re.sub(r'[\s-]+', '-', text).strip('-')

def clean_url(url):
    if not url or any(x in url for x in ['facebook', 'twitter', 'whatsapp']): return ""
    url = url.strip()
    if url.startswith('/'): return BASE_URL + url
    return url

def extract_m3u8_url(scraper, episode_url):
    """Bölüm sayfasından m3u8 URL'sini daha derinlemesine arar"""
    try:
        # Engellenmemek için kısa bir bekleme
        time.sleep(1.5)
        resp = scraper.get(episode_url, timeout=15)
        
        if "Teknik bir sorun" in resp.text or resp.status_code != 200:
            return ""
        
        # 1. Yöntem: Script içindeki 'source' veya 'hls' tanımlarını ara
        # NowTV bazen base64 veya parçalı link kullanabilir, en yaygın olanları tara
        m3u8_matches = re.findall(r'https?://[^\s"\']+\.m3u8[^\s"\']*', resp.text)
        for link in m3u8_matches:
            if "master" in link or "index" in link:
                return link

        # 2. Yöntem: Video objelerini tara
        soup = BeautifulSoup(resp.text, 'html.parser')
        video_div = soup.find('div', {'data-video-source': True})
        if video_div:
            return video_div['data-video-source']
            
        return ""
    except:
        return ""

def extract_season_episodes(scraper, series_url):
    """Dizi için tüm bölümleri bulur"""
    episodes = []
    # Bölümlerin toplu listelendiği sayfa genellikle /bolumler'dir
    target_url = series_url.replace('/izle', '/bolumler')
    
    try:
        resp = scraper.get(target_url, timeout=15)
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Paylaştığın yapıya göre .list-item içindeki bölüm linklerini topla
        items = soup.select('.list-item')
        
        # Sadece gerçek bölüm linklerini al (Sosyal medya paylaşım linklerini ele)
        for item in items:
            link_tag = item.find('a', href=True)
            if link_tag and "/bolum/" in link_tag['href']:
                ep_url = clean_url(link_tag['href'])
                if not ep_url: continue
                
                # Başlık ve Resim
                title_tag = item.select_one('.program-name strong') or item.select_one('.program-name')
                img_tag = item.find('img')
                
                ep_num_match = re.search(r'/bolum/(\d+)', ep_url)
                ep_num = ep_num_match.group(1) if ep_num_match else "1"
                
                episodes.append({
                    "numara": ep_num,
                    "ad": title_tag.get_text(strip=True) if title_tag else f"Bölüm {ep_num}",
                    "link": ep_url,
                    "thumbnail": clean_url(img_tag.get('src') or img_tag.get('data-src')) if img_tag else "",
                    "m3u8": "" # Performans için m3u8'i sonra dolduracağız veya opsiyonel bırakacağız
                })
        
        # Tekilleştir ve sırala
        unique_eps = {v['link']: v for v in episodes}.values()
        return sorted(list(unique_eps), key=lambda x: int(x['numara']) if x['numara'].isdigit() else 0)
        
    except Exception as e:
        logger.error(f"Hata: {e}")
        return []

def run_scraper():
    logger.info("🚀 NowTV Arşiv Tarayıcı Başlatıldı...")
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome','platform': 'windows','desktop': True})
    
    try:
        response = scraper.get(MAIN_URL, timeout=30)
        soup = BeautifulSoup(response.text, 'html.parser')
        series_items = soup.select('.videos .list-item')
        series_data = {}

        # Test amaçlı ilk 5 diziyi çekelim (Hız için)
        for item in series_items[:10]:
            name_tag = item.select_one('.program-name strong')
            link_tag = item.select_one('.list-item-image a')
            
            if not name_tag or not link_tag: continue
            
            s_name = name_tag.get_text(strip=True)
            s_url = clean_url(link_tag['href'])
            s_id = slugify(s_name)
            
            logger.info(f"🔍 Dizi: {s_name}")
            
            episodes = extract_season_episodes(scraper, s_url)
            
            # Bölüm m3u8'lerini çekmek çok vakit alır ve engel riski yaratır.
            # İlk etapta sadece son bölümün m3u8'ini çekmeyi deneyelim (Örnek olarak)
            if episodes:
                logger.info(f"   ✅ {len(episodes)} bölüm listelendi. m3u8 aranıyor...")
                # Sadece son bölümün m3u8'ini çek (Test için)
                episodes[-1]['m3u8'] = extract_m3u8_url(scraper, episodes[-1]['link'])
                
                series_data[s_id] = {
                    "isim": s_name,
                    "resim": clean_url(item.find('img').get('src')) if item.find('img') else "",
                    "link": s_url,
                    "bolumler": episodes,
                    "bolum_sayisi": len(episodes)
                }
            
            time.sleep(2) # Banlanmamak için diziler arası bekleme

        if series_data:
            with open('nowtv_data.json', 'w', encoding='utf-8') as f:
                json.dump(series_data, f, ensure_ascii=False, indent=2)
            logger.info("✅ Veriler 'nowtv_data.json' dosyasına kaydedildi.")
        
    except Exception as e:
        logger.error(f"Kritik hata: {e}")

if __name__ == "__main__":
    run_scraper()

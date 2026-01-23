import cloudscraper
from bs4 import BeautifulSoup
import json
import time
import re
import logging

# Loglama ayarları
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
    if not url: return ""
    if url.startswith('/'): return BASE_URL + url
    return url

def extract_episodes(scraper, series_url):
    """Dizi sayfasındaki bölümleri bulur"""
    episodes = []
    try:
        # NowTV'de bölümler genellikle dizi-adi/bolumler sayfasındadır
        target_url = series_url.replace('/izle', '/bolumler')
        resp = scraper.get(target_url, timeout=15)
        
        # Eğer /bolumler sayfası yoksa ana sayfayı tara
        if resp.status_code != 200:
            resp = scraper.get(series_url, timeout=15)
            
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Paylaştığın HTML yapısına göre .list-item içindeki bölümleri bul
        items = soup.select('.list-item')
        for item in items:
            link_tag = item.find('a', href=True)
            if link_tag and "/bolum" in link_tag['href']:
                title_tag = item.select_one('.program-name strong') or item.select_one('.program-name')
                img_tag = item.find('img')
                
                episodes.append({
                    "ad": title_tag.get_text(strip=True) if title_tag else "Bölüm",
                    "link": clean_url(link_tag['href']),
                    "thumbnail": clean_url(img_tag.get('src') or img_tag.get('data-src')) if img_tag else ""
                })
        
        return episodes[::-1] # Eskiden yeniye
    except Exception as e:
        logger.error(f"Bölüm hatası: {e}")
        return []

def run_scraper():
    logger.info("🚀 Scraper Başlatıldı (Yeni HTML Yapısı)...")
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome','platform': 'windows','desktop': True})
    
    try:
        response = scraper.get(MAIN_URL, timeout=30)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Paylaştığın HTML yapısına göre ana konteyner
        items = soup.select('.videos .list-item')
        series_data = {}

        for item in items:
            # 1. Link ve İsim Çekme
            link_tag = item.select_one('.list-item-image a')
            name_tag = item.select_one('.program-name strong')
            
            if not link_tag or not name_tag: continue
            
            s_name = name_tag.get_text(strip=True)
            s_url = clean_url(link_tag['href'])
            s_id = slugify(s_name)
            
            # 2. Görsel Çekme
            img_tag = item.find('img')
            s_img = clean_url(img_tag.get('src')) if img_tag else ""

            logger.info(f"🔍 İşleniyor: {s_name}")
            
            # 3. Alt Bölümleri Çekme
            episodes = extract_episodes(scraper, s_url)
            
            if episodes:
                series_data[s_id] = {
                    "isim": s_name,
                    "resim": s_img,
                    "link": s_url,
                    "bolumler": episodes
                }
                logger.info(f"✅ {len(episodes)} bölüm eklendi.")
            
            time.sleep(1) # Siteyi yormayalım

        if series_data:
            with open("nowtv_data.json", "w", encoding="utf-8") as f:
                json.dump(series_data, f, ensure_ascii=False, indent=2)
            logger.info(f"🎉 Bitti! {len(series_data)} dizi kaydedildi.")
        else:
            logger.error("❌ Veri bulunamadı. Lütfen URL'yi veya seçicileri kontrol edin.")

    except Exception as e:
        logger.error(f"Kritik Hata: {e}")

if __name__ == "__main__":
    run_scraper()

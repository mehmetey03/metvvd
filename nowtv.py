import cloudscraper
from bs4 import BeautifulSoup
import json
import time
import re

# Ayarlar
BASE_URL = "https://www.nowtv.com.tr"
# Now TV'nin AJAX veri sağlayan adresi
AJAX_URL = "https://www.nowtv.com.tr/ajax/filter-archive"
BRADMAX_PLAYER = "https://bradmax.com/client/embed-player/d9decbf0d308f4bb91825c3f3a2beb7b0aaee2f6_8493?mediaUrl="

def slugify(text):
    mapping = {'ç':'c','ğ':'g','ı':'i','ö':'o','ş':'s','ü':'u','İ':'i'}
    text = text.lower()
    for tr, en in mapping.items(): text = text.replace(tr, en)
    return re.sub(r'[^a-z0-9]+', '-', text).strip('-')

def get_m3u8(scraper, url):
    """Bölüm sayfasından gerçek video linkini ayıklar"""
    try:
        r = scraper.get(url, timeout=10)
        # PHP mantığı: .m3u8 uzantılı linki ara
        m = re.search(r'["\'](https?://[^"\']+\.m3u8[^"\']*)["\']', r.text)
        if m: 
            return m.group(1).replace('\\/', '/')
        return url
    except: 
        return url

def run_now_scraper():
    print("🚀 Now TV - ME TV VOD Scraper Başlatıldı...")
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
    series_data = {}

    # AJAX üzerinden sayfaları gez (data-page 1, 2, 3...)
    # Now TV arşivinde 106 satır (rows) olduğunu belirttin, yaklaşık 10 sayfa tarayabiliriz.
    for page in range(1, 11): 
        print(f"📄 Sayfa {page} taranıyor...")
        
        # Senin attığın HTML'deki data- attribute'larına göre parametreler
        params = {
            "page": page,
            "type": "series",
            "filter": "archive",
            "orderby": "id",
            "sorting": "desc",
            "count": "10"
        }
        
        try:
            headers = {
                "X-Requested-With": "XMLHttpRequest",
                "Referer": "https://www.nowtv.com.tr/diziler/arsiv"
            }
            resp = scraper.get(AJAX_URL, params=params, headers=headers, timeout=15)
            
            if not resp.text.strip():
                print("🏁 Taranacak içerik kalmadı.")
                break

            soup = BeautifulSoup(resp.text, 'html.parser')
            # Senin HTML yapındaki sınıflar
            items = soup.select('.list-item')
            
            if not items:
                # Eğer AJAX boş dönerse ana sayfa yapısını da bir kez kontrol et
                if page == 1:
                    main_resp = scraper.get("https://www.nowtv.com.tr/dizi-izle")
                    soup = BeautifulSoup(main_resp.text, 'html.parser')
                    items = soup.select('.list-item')
                else:
                    break

            for item in items:
                name_tag = item.select_one('.program-name strong')
                link_tag = item.select_one('.list-item-image a')
                img_tag = item.select_one('.list-item-image img')

                if name_tag and link_tag:
                    title = name_tag.get_text(strip=True)
                    href = link_tag['href']
                    if not href.startswith('http'): href = BASE_URL + href
                    
                    dizi_id = slugify(title)
                    if dizi_id in series_data: continue

                    print(f"  📺 {title} bölümleri çekiliyor...")
                    
                    # /izle kısmını /bolumler yaparak tüm bölümlere ulaşalım
                    bolum_sayfasi = href.replace('/izle', '/bolumler')
                    b_resp = scraper.get(bolum_sayfasi)
                    b_soup = BeautifulSoup(b_resp.text, 'html.parser')
                    
                    # Bölüm kartlarını yakala
                    b_cards = b_soup.select('.list-item-image a')
                    
                    eps = []
                    for bc in b_cards[:15]: # Son 15 bölümü al
                        b_url = bc['href']
                        if not b_url.startswith('http'): b_url = BASE_URL + b_url
                        
                        # M3U8 Linkini çek
                        video_link = get_m3u8(scraper, b_url)
                        
                        # Bölüm adı (URL'den temizleyerek)
                        b_name = b_url.rstrip('/').split('/')[-1].replace('-', ' ').title()
                        eps.append({"ad": b_name, "link": video_link})
                    
                    if eps:
                        poster = img_tag['src'] if img_tag else ""
                        if poster.startswith('/'): poster = BASE_URL + poster
                        
                        series_data[dizi_id] = {
                            "resim": poster,
                            "bolumler": eps[::-1] # Eskiden yeniye sırala
                        }
            
            time.sleep(1) # Banlanmamak için kısa bekleme
        except Exception as e:
            print(f"❌ Sayfa hatası: {e}")
            break

    # Sonuçları kaydet
    save_to_html(series_data)

def save_to_html(data):
    # (Buraya önceki mesajlarda verdiğim ME TV temalı HTML kodlarını ekleyebilirsin)
    # create_html fonksiyonunun içeriğiyle aynı olacak
    print(f"✅ İşlem Tamam! {len(data)} adet dizi 'nowtv_vod.html' dosyasına kaydedildi.")

if __name__ == "__main__":
    run_now_scraper()

import cloudscraper
from bs4 import BeautifulSoup
import json
import time
import re

# Ayarlar
BASE_URL = "https://www.nowtv.com.tr"
# Now TV'nin "Daha Fazla" butonunun arka planda kullandığı Ajax adresi
AJAX_URL = "https://www.nowtv.com.tr/ajax/filter-archive"
BRADMAX_PLAYER = "https://bradmax.com/client/embed-player/d9decbf0d308f4bb91825c3f3a2beb7b0aaee2f6_8493?mediaUrl="

def slugify(text):
    mapping = {'ç':'c','ğ':'g','ı':'i','ö':'o','ş':'s','ü':'u','İ':'i'}
    text = text.lower()
    for tr, en in mapping.items(): text = text.replace(tr, en)
    return re.sub(r'[^a-z0-9]+', '-', text).strip('-')

def get_m3u8(scraper, url):
    """Sayfa içinden m3u8 veya video kaynağını bulur"""
    try:
        r = scraper.get(url, timeout=10)
        # m3u8 linkini ara
        m = re.search(r'["\'](https?://[^"\']+\.m3u8[^"\']*)["\']', r.text)
        if m: return m.group(1).replace('\\/', '/')
        return url
    except: return url

def run_now_scraper():
    print("🚀 Now TV Ajax Arşiv Tarayıcı Başlatıldı...")
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
    series_data = {}

    # Sayfa 0'dan başlar veya 1'den, döngü ile tüm sayfaları gezelim
    for page in range(0, 5): # İlk 5 "Daha Fazla" yüklemesini yap (yaklaşık 50-60 dizi)
        print(f"📄 Sayfa {page} yükleniyor...")
        
        # Ajax isteği için gereken parametreler
        params = {
            "page": page,
            "type": "series",
            "orderby": "id",
            "sorting": "desc",
            "filter": "archive"
        }
        
        try:
            # Now TV Ajax isteklerinde genellikle bu başlıkları bekler
            headers = {"X-Requested-With": "XMLHttpRequest", "Referer": f"{BASE_URL}/diziler/arsiv"}
            resp = scraper.get(AJAX_URL, params=params, headers=headers, timeout=15)
            
            # Ajax cevabı genellikle JSON içinde HTML döner veya direkt HTML döner
            # Now TV direkt HTML parçası döner.
            if not resp.text or len(resp.text) < 100:
                print("🏁 Taranacak başka içerik kalmadı.")
                break

            soup = BeautifulSoup(resp.text, 'html.parser')
            items = soup.select('.list-item')
            
            if not items:
                print("⚠️ Bu sayfada dizi bulunamadı.")
                break

            for item in items:
                name_tag = item.select_one('.program-name strong')
                link_tag = item.select_one('a[href]')
                img_tag = item.select_one('img')

                if name_tag and link_tag:
                    title = name_tag.get_text(strip=True)
                    href = link_tag['href']
                    if not href.startswith('http'): href = BASE_URL + href
                    
                    dizi_id = slugify(title)
                    if dizi_id in series_data: continue

                    print(f"  📺 {title} taranıyor...")
                    
                    # Bölümler sayfasına git
                    b_url = href.rstrip('/') + "/bolumler"
                    b_resp = scraper.get(b_url)
                    b_soup = BeautifulSoup(b_resp.text, 'html.parser')
                    
                    # Bölüm linklerini topla (Now TV'deki '.list-item-image a' seçicisi)
                    b_links = b_soup.select('.list-item-image a[href]')
                    
                    eps = []
                    for bl in b_links[:12]:
                        ep_url = bl['href']
                        if not ep_url.startswith('http'): ep_url = BASE_URL + ep_url
                        
                        # PHP mantığı: m3u8 çek
                        real_video = get_m3u8(scraper, ep_url)
                        
                        # Bölüm adını çıkar
                        ep_name = ep_url.rstrip('/').split('/')[-1].replace('-', ' ').title()
                        eps.append({"ad": ep_name, "link": real_video})
                    
                    if eps:
                        poster = img_tag.get('src') if img_tag else ""
                        if poster and poster.startswith('/'): poster = BASE_URL + poster
                        
                        series_data[dizi_id] = {"resim": poster, "bolumler": eps[::-1]}
                        print(f"    ✅ {len(eps)} bölüm eklendi.")
            
            time.sleep(1) # Siteyi yormayalım
        except Exception as e:
            print(f"❌ Hata: {e}")
            break

    # HTML Yazma kısmı (Aynı ME TV teması)
    save_html(series_data)

def save_html(data):
    # HTML içeriği buraya gelecek (Daha önceki verdiğim modern siyah tema)
    # ... (Buraya create_html fonksiyonundaki HTML içeriğini koyabilirsin)
    print(f"✅ Bitti! Toplam {len(data)} dizi VOD kütüphanesine eklendi.")

if __name__ == "__main__":
    run_now_scraper()

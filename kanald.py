import cloudscraper
from bs4 import BeautifulSoup
import json
import time
import re

# Web sitesi kök adresi
BASE_URL = "https://www.kanald.com.tr"

# cloudscraper, cloudflare ve bot korumalarını aşmak için requests yerine geçer
scraper = cloudscraper.create_scraper(
    browser={
        'browser': 'chrome',
        'platform': 'windows',
        'desktop': True
    }
)

MAX_RETRIES = 3
RETRY_DELAY = 2

def get_soup(url, retry_count=0):
    try:
        response = scraper.get(url, timeout=20)
        response.raise_for_status()
        return BeautifulSoup(response.text, "html.parser")
    except Exception as e:
        if retry_count < MAX_RETRIES:
            print(f"      ⚠ Bağlantı Hatası: {e}. Yeniden deneniyor... ({retry_count + 1}/{MAX_RETRIES})")
            time.sleep(RETRY_DELAY)
            return get_soup(url, retry_count + 1)
        return None

def slugify(text):
    tr_map = str.maketrans("ığüşöçİĞÜŞÖÇ", "igusoicigusoic")
    text = text.translate(tr_map).lower()
    text = re.sub(r'[^a-z0-9]', '', text)
    return text

def main():
    print("🚀 Kanal D İçerikleri Çekiliyor (Bot Koruması Aşılıyor)...")
    
    sources = ["/diziler", "/programlar"]
    diziler_data = {}

    for source in sources:
        soup = get_soup(BASE_URL + source)
        if not soup:
            continue

        # Kanal D'nin ana liste yapısı 'poster-card'
        cards = soup.find_all("div", class_="poster-card")
        print(f"📍 {source} sayfasında {len(cards)} potansiyel içerik bulundu.")

        for card in cards:
            try:
                title_tag = card.find("span", class_="title")
                link_tag = card.find("a")
                img_tag = card.find("img")

                if title_tag and link_tag:
                    dizi_adi = title_tag.get_text(strip=True)
                    dizi_link = BASE_URL + link_tag.get("href")
                    dizi_id = slugify(dizi_adi)
                    
                    # Resim çekme (Lazy load koruması)
                    poster_url = img_tag.get("data-src") or img_tag.get("src") or ""
                    if poster_url.startswith("//"):
                        poster_url = "https:" + poster_url

                    print(f"  --> {dizi_adi} taranıyor...")

                    # Bölümler sayfasına git
                    bolum_soup = get_soup(dizi_link + "/bolumler")
                    final_bolumler = []

                    if bolum_soup:
                        # Bölüm kartlarını bul
                        b_cards = bolum_soup.select(".sub-content-list .card")
                        for b_card in b_cards:
                            b_link_tag = b_card.find("a")
                            b_title_tag = b_card.find("div", class_="title")
                            
                            if b_link_tag and b_title_tag:
                                b_adi = b_title_tag.get_text(strip=True)
                                b_href = b_link_tag.get("href")
                                b_full_link = BASE_URL + b_href if b_href.startswith("/") else b_href
                                
                                final_bolumler.append({
                                    "ad": b_adi,
                                    "link": b_full_link
                                })

                    if final_bolumler:
                        # Kanal D bölümleri genelde yeniden eskiye gelir, ters çeviriyoruz
                        final_bolumler.reverse()
                        
                        diziler_data[dizi_id] = {
                            "resim": poster_url,
                            "ad": dizi_adi,
                            "bolumler": final_bolumler
                        }
                        print(f"    [✓] {len(final_bolumler)} bölüm eklendi.")
                    
                    time.sleep(0.2) # Sunucuyu yormamak için

            except Exception as e:
                print(f"  [!] Hata: {e}")

    # JSON verisini HTML şablonuna bas
    create_html(diziler_data)

def create_html(data):
    # Senin Show TV şablonunla uyumlu hale getirilmiş çıktı
    json_output = json.dumps(data, ensure_ascii=False)
    
    # HTML oluşturma (Önceki şablonunun aynısı kullanılabilir)
    with open("index.html", "w", encoding="utf-8") as f:
        # Buraya senin paylaştığın uzun HTML kodunu f-string içinde koyabilirsin.
        # Basitlik olması için kısa versiyonu bırakıyorum:
        f.write(f"<html><script>var diziler = {json_output}; console.log(diziler);</script><body><h1>Veriler Yuklendi. Konsolu kontrol et veya arayüzü ekle.</h1></body></html>")
    
    print(f"\n✨ Başarılı! {len(data)} dizi index.html dosyasına kaydedildi.")

if __name__ == "__main__":
    main()

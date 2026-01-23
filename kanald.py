import cloudscraper
from bs4 import BeautifulSoup
import json
import re

BASE_URL = "https://www.kanald.com.tr"

# Bot korumasını aşan scraper
scraper = cloudscraper.create_scraper(
    browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True}
)

def slugify(text):
    # Karakter listesi eşitlendi (ı-i, ş-s, vb.)
    tr_map = str.maketrans("ığüşöçİĞÜŞÖÇ", "igusoicigusoic")
    text = text.translate(tr_map).lower()
    text = re.sub(r'[^a-z0-9]', '', text)
    return text

def main():
    print("🚀 Kanal D İçerikleri Taranıyor (Karakter Hatası Giderildi)...")
    
    targets = [
        {"url": "/diziler", "label": "Diziler"},
        {"url": "/programlar", "label": "Programlar"}
    ]
    
    diziler_data = {}

    for target in targets:
        print(f"📍 {target['label']} sayfası taranıyor...")
        try:
            response = scraper.get(BASE_URL + target['url'], timeout=20)
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Paylaştığın HTML'deki poster-card yapısını yakalıyoruz
            cards = soup.find_all("a", class_="poster-card")
            
            if not cards:
                print(f"  ⚠️ Sayfa boş döndü. (Bot koruması hala aktif olabilir)")
                continue

            for card in cards:
                img_tag = card.find("img")
                if not img_tag: continue
                
                # Paylaştığın yapıdaki alt ve data-src verilerini çekiyoruz
                dizi_adi = img_tag.get("alt", "").strip()
                if not dizi_adi: 
                    # Alt boşsa başlığı card içindeki span'dan ara
                    title_span = card.find("span", class_="title")
                    dizi_adi = title_span.get_text(strip=True) if title_span else "Bilinmeyen İçerik"

                dizi_href = card.get("href", "")
                dizi_link = BASE_URL + dizi_href if dizi_href.startswith("/") else dizi_href
                dizi_id = slugify(dizi_adi)
                
                # Resim için paylaştığın 'data-src' en güveniliri
                poster_url = img_tag.get("data-src") or img_tag.get("src") or ""
                if poster_url.startswith("//"):
                    poster_url = "https:" + poster_url

                diziler_data[dizi_id] = {
                    "ad": dizi_adi,
                    "resim": poster_url,
                    "link": dizi_link,
                    "bolumler": [
                        {"ad": "Tüm Bölümler", "link": dizi_link + "/bolumler"}
                    ]
                }
                print(f"  [+] {dizi_adi} eklendi.")

        except Exception as e:
            print(f"  ❌ Beklenmedik Hata: {e}")

    if diziler_data:
        # JSON verisini dosyaya kaydet
        with open("kanald_data.json", "w", encoding="utf-8") as f:
            json.dump(diziler_data, f, ensure_ascii=False, indent=4)
        print(f"\n✨ Başarılı! {len(diziler_data)} içerik bulundu ve kanald_data.json dosyasına kaydedildi.")
    else:
        print("❌ Veri çekilemedi. Lütfen internet bağlantını veya siteye erişimi kontrol et.")

if __name__ == "__main__":
    main()

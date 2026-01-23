import cloudscraper
from bs4 import BeautifulSoup
import json
import re

def scrape_kanald():
    # Tarayıcı gibi davranması için daha güçlü bir scraper
    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'desktop': True
        }
    )
    
    base_url = "https://www.kanald.com.tr"
    sources = [
        f"{base_url}/diziler",
        f"{base_url}/programlar"
    ]
    
    all_data = {}
    print("🚀 Kanal D İçerik Kartları Taranıyor (Gelişmiş Tarama)...")
    
    for url in sources:
        try:
            response = scraper.get(url, timeout=20)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Alternatif seçiciler: Hem 'poster-card' hem de 'card' yapılarını dene
            cards = soup.select('.poster-card, [class*="card-container"]')
            
            for card in cards:
                # Başlık ve Link bulma (Kanal D'nin farklı HTML varyasyonlarına göre)
                title_tag = card.find(['span', 'h2', 'h3'], class_='title')
                link_tag = card.find('a')
                img_tag = card.find('img')
                
                if title_tag and link_tag:
                    title = title_tag.get_text(strip=True)
                    href = link_tag.get('href', '')
                    link = base_url + href if href.startswith('/') else href
                    
                    # Resim bulma (data-src, data-original veya src)
                    img = img_tag.get('data-src') or img_tag.get('data-original') or img_tag.get('src', '')
                    
                    if not img.startswith('http'):
                        img = "https:" + img if img.startswith('//') else img

                    # ID oluşturma
                    safe_id = re.sub(r'\W+', '', title.lower())
                    
                    if safe_id:
                        all_data[safe_id] = {
                            "resim": img,
                            "ad": title,
                            "bolumler": [
                                {"ad": "Tüm Bölümler", "link": link},
                                {"ad": "Bölümler Sayfası", "link": link + "/bolumler"}
                            ]
                        }
            print(f"📍 {url} tarandı...")
        except Exception as e:
            print(f"❌ Hata ({url}): {e}")

    return all_data

# Verileri çek ve dosyaya yaz
diziler_data = scrape_kanald()

if not diziler_data:
    print("⚠️ Veri çekilemedi! Lütfen site yapısını veya internet bağlantısını kontrol et.")
else:
    # Buraya bir önceki mesajdaki html_content kısmını ekle (Aynı şablon)
    # ... (HTML Yazma Bölümü) ...
    print(f"✅ Başarılı! {len(diziler_data)} içerik index.html dosyasına işlendi.")

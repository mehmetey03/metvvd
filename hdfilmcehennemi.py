import requests
from bs4 import BeautifulSoup
import json
import time
import urllib.parse
import random

def scrape_v3(max_pages=5):
    all_films = []
    base_url = "https://www.hdfilmcehennemi.nl"
    
    # ALTERNATİF PROXY LİSTESİ (Biri çalışmazsa diğeri devreye girer)
    proxies = [
        "https://api.allorigins.win/get?url=",
        "https://corsproxy.io/?",
        "https://api.codetabs.com/v1/proxy/?quest="
    ]
    
    for page in range(1, max_pages + 1):
        target_url = base_url + ("/" if page == 1 else f"/sayfa/{page}/")
        
        # Her sayfa için farklı bir proxy seçerek "rate limit"e takılmayı önleyelim
        current_proxy = proxies[page % len(proxies)]
        
        # AllOrigins proxy'si veriyi JSON içinde 'contents' olarak döndürür
        is_allorigins = "allorigins" in current_proxy
        encoded_url = urllib.parse.quote(target_url) if is_allorigins else target_url
        full_request_url = current_proxy + (encoded_url if is_allorigins else urllib.parse.quote(target_url))

        print(f"📡 Sayfa {page} deneniyor ({current_proxy.split('/')[2]})...")

        try:
            response = requests.get(full_request_url, timeout=20)
            
            if is_allorigins:
                html_content = response.json().get('contents', '')
            else:
                html_content = response.text

            soup = BeautifulSoup(html_content, 'html.parser')
            
            # HTML yapısını analiz ettiğimizde en sağlam yakalama yolu:
            # İçinde 'hdfc' veya film uzantısı geçen linkleri bulmak
            posters = soup.select('a.poster') or soup.select('.posters-4-col a') or soup.find_all('a', href=True)
            
            page_films = []
            for a in posters:
                href = a.get('href', '')
                # Sadece film detay sayfasına giden linkleri filtrele (Önemli!)
                if "/sayfa/" in href or href == base_url or len(href) < 10:
                    continue
                
                title_node = a.find('strong', class_='poster-title')
                if not title_node: continue
                
                title = title_node.get_text(strip=True)
                img = a.find('img')
                img_url = img.get('data-src') or img.get('src') if img else ""
                imdb = a.find('span', class_='imdb').get_text(strip=True) if a.find('span', class_='imdb') else "6.0"
                
                page_films.append({
                    "title": title,
                    "link": href if href.startswith('http') else base_url + href,
                    "image": img_url,
                    "imdb": imdb
                })

            if page_films:
                # Aynı filmleri tekrar eklememek için (set kontrolü gibi)
                current_titles = [f['title'] for f in page_films]
                print(f"✅ Sayfa {page} başarılı: {len(page_films)} film bulundu.")
                all_films.extend(page_films)
            else:
                print(f"⚠️ Sayfa {page} içeriği boş geldi. Proxy veya Bot koruması aktif.")
                # Hata tespiti için içeriğin bir kısmını yazdıralım
                if len(html_content) < 500:
                    print(f"   Gelen kısa mesaj: {html_content.strip()}")

            time.sleep(random.uniform(2, 4)) # Daha doğal bekleme süresi

        except Exception as e:
            print(f"❌ Sayfa {page} hatası: {str(e)}")

    return all_films

# Çalıştır
results = scrape_v3(5)
# ... (Kayıt işlemleri aynı)

import requests
from bs4 import BeautifulSoup
import time
import re

class KanalDScraper:
    def __init__(self):
        self.base_url = "https://www.kanald.com.tr"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7"
        }

    def safe_slug(self, text):
        if not text: return ""
        mapping = {'ç':'c','ğ':'g','ı':'i','i':'i','ö':'o','ş':'s','ü':'u','Ç':'C','Ğ':'G','İ':'I','Ö':'O','Ş':'S','Ü':'U'}
        for tr, en in mapping.items():
            text = text.replace(tr, en)
        return re.sub(r'[^a-zA-Z0-9\s-]', '', text).strip().lower().replace(" ", "-")

    def get_content_list(self, category_path):
        """Dizi veya Program listesini daha geniş seçicilerle çeker"""
        url = f"{self.base_url}{category_path}"
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(response.content, "html.parser")
            
            items = []
            # Kanal D'nin hem arşiv hem güncel sayfa yapısındaki tüm olası linkleri tara
            # Genelde 'card', 'item' veya 'story-card' içeren sınıflar kullanılır
            cards = soup.find_all("a", href=True)
            
            seen_urls = set()
            for a in cards:
                href = a['href']
                # Sadece ilgili kategoriye giden ve ana sayfaya gitmeyen linkleri al
                if category_path in href and href != category_path:
                    # Başlığı bul (span, h3 veya figcaption içinde olabilir)
                    title_elem = a.find(["h3", "span", "h2", "figcaption"])
                    title = title_elem.text.strip() if title_elem else ""
                    
                    full_url = self.base_url + href if href.startswith("/") else href
                    
                    if full_url not in seen_urls and len(title) > 2:
                        items.append({"title": title, "url": full_url})
                        seen_urls.add(full_url)
            
            return items
        except Exception as e:
            print(f"  ❌ Bağlantı hatası: {e}")
            return []

    def get_episodes(self, content_url):
        """Bölüm detaylarını HTML örneğindeki sınıflara göre çeker"""
        try:
            target_url = content_url.rstrip('/') + "/bolumler"
            response = requests.get(target_url, headers=self.headers, timeout=10)
            if response.status_code != 200: # Eğer /bolumler yoksa ana sayfasına bak
                response = requests.get(content_url, headers=self.headers, timeout=10)
            
            soup = BeautifulSoup(response.content, "html.parser")
            episodes = []
            
            # Paylaştığın örnekteki .story-card yapısını hedefler
            cards = soup.select(".story-card") or soup.select(".swiper-slide a")
            
            for card in cards:
                title_tag = card.find(["h3", "span"], class_="title")
                time_tag = card.find("time")
                
                if title_tag:
                    episodes.append({
                        "title": title_tag.text.strip(),
                        "duration": time_tag.text.strip() if time_tag else "Süre Belirtilmemiş",
                        "link": self.base_url + card['href'] if card['href'].startswith("/") else card['href']
                    })
            return episodes[:10] # Son 10 bölüm yeterli
        except:
            return []

    def run(self):
        print("🚀 Kanal D Profesyonel Arşiv Tarayıcı Başlatıldı...")
        results = {"diziler": [], "programlar": []}
        categories = [("/diziler", "diziler"), ("/programlar", "programlar")]

        for path, key in categories:
            print(f"\n📍 {key.upper()} listesi çekiliyor...")
            items = self.get_content_list(path)
            
            if not items:
                # Eğer hala 0 bulunuyorsa alternatif yöntem: /arsiv sayfasına bak
                print(f"  ⚠️ {path} boş döndü, arşiv taranıyor...")
                items = self.get_content_list(path + "/arsiv")

            print(f"🔎 {len(items)} içerik bulundu. Bölümler taranıyor...")

            for item in items:
                print(f"  🔄 {item['title']} taranıyor...")
                item['episodes'] = self.get_episodes(item['url'])
                results[key].append(item)
                time.sleep(0.3)

        self.save_to_html(results)

    def save_to_html(self, data):
        html_content = f"""
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: sans-serif; background: #1a1a1a; color: white; padding: 40px; }}
                .container {{ max-width: 1000px; margin: auto; }}
                .item-card {{ background: #2a2a2a; padding: 15px; margin: 10px 0; border-radius: 8px; border-left: 5px solid #f29400; }}
                h2 {{ color: #f29400; border-bottom: 2px solid #333; }}
                ul {{ font-size: 0.9em; color: #ccc; }}
                a {{ color: #00a8ff; text-decoration: none; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Kanal D Arşiv Taraması</h1>
                <h2>DİZİLER</h2>
                {"".join([f"<div class='item-card'><b>{x['title']}</b> - <a href='{x['url']}'>Git</a><ul>" + "".join([f"<li>{e['title']}</li>" for e in x['episodes']]) + "</ul></div>" for x in data['diziler']])}
                <h2>PROGRAMLAR</h2>
                {"".join([f"<div class='item-card'><b>{x['title']}</b> - <a href='{x['url']}'>Git</a><ul>" + "".join([f"<li>{e['title']}</li>" for e in x['episodes']]) + "</ul></div>" for x in data['programlar']])}
            </div>
        </body>
        </html>
        """
        with open("kanald_pro.html", "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"\n✨ İşlem Başarılı! {len(data['diziler']) + len(data['programlar'])} toplam içerik 'kanald_pro.html' dosyasına kaydedildi.")

if __name__ == "__main__":
    KanalDScraper().run()

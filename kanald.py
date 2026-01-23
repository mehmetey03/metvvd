import requests
from bs4 import BeautifulSoup
import json
import time
import re

class KanalDScraper:
    def __init__(self):
        self.base_url = "https://www.kanald.com.tr"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    def safe_slug(self, text):
        """Hata veren maketrans yerine güvenli karakter dönüşümü"""
        if not text: return ""
        mapping = {
            'ç': 'c', 'ğ': 'g', 'ı': 'i', 'i': 'i', 'ö': 'o', 'ş': 's', 'ü': 'u',
            'Ç': 'C', 'Ğ': 'G', 'İ': 'I', 'I': 'i', 'Ö': 'O', 'Ş': 'S', 'Ü': 'U'
        }
        for tr, en in mapping.items():
            text = text.replace(tr, en)
        text = re.sub(r'[^a-zA-Z0-9\s-]', '', text)
        return text.strip().lower().replace(" ", "-")

    def get_content_list(self, category_path):
        """Dizi veya Program listesini çeker"""
        url = f"{self.base_url}{category_path}"
        response = requests.get(url, headers=self.headers)
        soup = BeautifulSoup(response.content, "html.parser")
        
        items = []
        # Kanal D'nin kart yapısına göre seçici
        cards = soup.select(".content-card, .story-card, .series-card")
        
        for card in cards:
            link_tag = card.find("a") if card.name != "a" else card
            if link_tag and link_tag.get("href"):
                title = card.find("h3") or card.find("h2") or card.find(class_="title")
                items.append({
                    "title": title.text.strip() if title else "Adsız İçerik",
                    "url": self.base_url + link_tag.get("href") if not link_tag.get("href").startswith("http") else link_tag.get("href")
                })
        return items

    def get_episodes(self, content_url):
        """İçeriğin bölümlerini ve sezonlarını tarar"""
        try:
            # Bölümler sayfasına git
            if not content_url.endswith("/bolumler"):
                content_url = content_url.rstrip('/') + "/bolumler"
            
            response = requests.get(content_url, headers=self.headers)
            soup = BeautifulSoup(response.content, "html.parser")
            
            episodes = []
            # Paylaştığın HTML yapısındaki swiper-slide içindeki bölümleri bulur
            items = soup.select(".swiper-slide .story-card")
            
            for item in items:
                title_tag = item.select_one(".title")
                time_tag = item.select_one("time")
                img_tag = item.select_one("img")
                
                episodes.append({
                    "title": title_tag.text.strip() if title_tag else "Bölüm",
                    "duration": time_tag.text.strip() if time_tag else "N/A",
                    "image": img_tag.get("data-src") or img_tag.get("src") if img_tag else "",
                    "link": self.base_url + item.get("href") if item.get("href") else "#"
                })
            return episodes
        except Exception as e:
            print(f"  ⚠️ Hata: {str(e)}")
            return []

    def run(self):
        print("🚀 Kanal D Profesyonel Arşiv Tarayıcı Başlatıldı...")
        results = {"diziler": [], "programlar": []}

        categories = [("/diziler", "diziler"), ("/programlar", "programlar")]

        for path, key in categories:
            print(f"\n📍 {key.upper()} listesi çekiliyor...")
            items = self.get_content_list(path)
            print(f"🔎 {len(items)} içerik bulundu. Detaylar taranıyor...")

            for item in items:
                print(f"  🔄 İşleniyor: {item['title']}")
                item['episodes'] = self.get_episodes(item['url'])
                results[key].append(item)
                time.sleep(0.5) # Sunucuyu yormamak için

        self.save_to_html(results)

    def save_to_html(self, data):
        """Sonuçları şık bir HTML dosyasına kaydeder"""
        html_content = f"""
        <!DOCTYPE html>
        <html lang="tr">
        <head>
            <meta charset="UTF-8">
            <title>Kanal D Arşiv Listesi</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
            <style>
                body {{ background: #f4f4f4; }}
                .content-section {{ margin-bottom: 50px; background: white; padding: 20px; border-radius: 10px; }}
                .episode-card {{ font-size: 0.8rem; border: 1px solid #ddd; margin-bottom: 10px; }}
                .img-fluid {{ border-radius: 5px; }}
            </style>
        </head>
        <body class="container py-5">
            <h1 class="text-center mb-5">Kanal D İçerik Arşivi</h1>
            
            {"".join([self.generate_section(k.upper(), v) for k, v in data.items()])}
            
        </body>
        </html>
        """
        with open("kanald_pro.html", "w", encoding="utf-8") as f:
            f.write(html_content)
        print("\n✨ İşlem Başarılı! 'kanald_pro.html' oluşturuldu.")

    def generate_section(self, title, items):
        section_html = f"<div class='content-section'><h2>{title}</h2><div class='row'>"
        for item in items:
            episodes_html = "".join([f"<li>{ep['title']} ({ep['duration']})</li>" for ep in item['episodes'][:5]])
            section_html += f"""
            <div class='col-md-4 mb-4'>
                <div class='card h-100'>
                    <div class='card-body'>
                        <h5 class='card-title'>{item['title']}</h5>
                        <p class='text-muted'>Son Bölümler:</p>
                        <ul>{episodes_html}</ul>
                        <a href='{item['url']}' class='btn btn-sm btn-primary' target='_blank'>Sayfaya Git</a>
                    </div>
                </div>
            </div>"""
        section_html += "</div></div>"
        return section_html

if __name__ == "__main__":
    scraper = KanalDScraper()
    scraper.run()

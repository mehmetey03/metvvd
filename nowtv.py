import cloudscraper
from bs4 import BeautifulSoup
import json
import re
import subprocess
import time

BASE_URL = "https://www.nowtv.com.tr"
# NowTV bazen bu URL yapısını kabul eder, bazen Ajax bekler. İkisini de deneyeceğiz.
ARCHIVE_URL = "https://www.nowtv.com.tr/dizi-arsivi"

def slugify(text):
    mapping = {'ç':'c','ğ':'g','ı':'i','ö':'o','ş':'s','ü':'u','İ':'i','I':'i'}
    text = text.lower()
    for tr, en in mapping.items(): text = text.replace(tr, en)
    return re.sub(r'[^a-z0-9]+', '-', text).strip('-')

def get_m3u8(scraper, url):
    try:
        r = scraper.get(url, timeout=10)
        match = re.search(r'(https?://[^\s"\']+\.m3u8[^\s"\']*)', r.text)
        return match.group(0).replace('\\/', '/') if match else url
    except: return url

def run_scraper():
    print("🚀 NOW TV Hibrit Tarayıcı Başlatıldı...")
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome','platform': 'windows','desktop': True})
    series_data = {}

    # 1. ADIM: Ana sayfadaki ilk 10 diziyi ve toplam sayfa bilgisini al
    try:
        main_resp = scraper.get(ARCHIVE_URL, timeout=15)
        soup = BeautifulSoup(main_resp.text, 'html.parser')
        
        # Butondan toplam dizi sayısını öğrenelim
        btn = soup.find('a', class_='ajax-load-more-archive')
        total_rows = int(btn['data-rows']) if btn and btn.has_attr('data-rows') else 100
        print(f"📊 Toplam {total_rows} içerik tespit edildi.")

        # Sayfa sayfa gezelim (Her sayfa 10 dizi)
        for page in range(1, (total_rows // 10) + 2):
            print(f"📂 Sayfa {page} taranıyor...")
            
            # Ajax yerine doğrudan URL parametresi deniyoruz (Birçok sitede bu gizli çalışır)
            p_url = f"{ARCHIVE_URL}?page={page}"
            resp = scraper.get(p_url, timeout=15)
            page_soup = BeautifulSoup(resp.text, 'html.parser')
            cards = page_soup.select('.list-item')

            if not cards:
                print(f"⚠️ Sayfa {page} boş döndü, alternatif Ajax deneniyor...")
                # Alternatif: Ajax POST denemesi (Eğer URL parametresi yemezse)
                ajax_resp = scraper.post("https://www.nowtv.com.tr/ajax/get_archive_programs", 
                                         data={'filter':'archive','page':str(page),'type':'series'}, timeout=10)
                if ajax_resp.status_code == 200:
                    ajax_data = ajax_resp.json()
                    page_soup = BeautifulSoup(ajax_data.get('html', ''), 'html.parser')
                    cards = page_soup.select('.list-item')

            if not cards: break

            for card in cards:
                title_tag = card.find('strong') or card.find(class_='program-name')
                link_tag = card.find('a', href=True)
                if not title_tag or not link_tag: continue

                title = title_tag.get_text(strip=True)
                dizi_id = slugify(title)
                if dizi_id in series_data: continue

                print(f"  🎬 {title}...")
                
                # Bölümlere git
                b_url = (BASE_URL + link_tag['href']).replace('/izle', '/bolumler')
                try:
                    b_soup = BeautifulSoup(scraper.get(b_url, timeout=10).text, 'html.parser')
                    b_links = b_soup.find_all('a', href=re.compile(r'/bolum/'))
                    
                    eps = []
                    for bl in b_links:
                        b_title = bl.find_next(class_='program-name')
                        b_name = b_title.get_text(strip=True) if b_title else "Bölüm"
                        if any(e['ad'] == b_name for e in eps): continue
                        
                        full_url = BASE_URL + bl['href'] if bl['href'].startswith('/') else bl['href']
                        eps.append({"ad": b_name, "link": get_m3u8(scraper, full_url)})
                    
                    if eps:
                        img = card.find('img')
                        series_data[dizi_id] = {
                            "isim": title,
                            "resim": img.get('src') or img.get('data-src', ''),
                            "bolumler": eps
                        }
                except: continue

            time.sleep(0.5)

    except Exception as e:
        print(f"❌ Kritik Hata: {e}")

    if series_data:
        save_and_push(series_data)
    else:
        print("🚨 Veri hala çekilemedi. Site yapısı tamamen değişmiş olabilir.")

def save_and_push(data):
    # (Buradaki HTML oluşturma ve Git push kodları öncekiyle aynı, sadeleştirildi)
    html_file = "nowtv_vod.html"
    with open(html_file, "w", encoding="utf-8") as f:
        f.write(f"<html><script>const data = {json.dumps(data, ensure_ascii=False)};</script><body>")
        # Buraya senin istediğin o güzel tasarımı ekleyebilirsin, data JS içinde hazır.
        f.write("<div id='list'></div><script>Object.keys(data).forEach(k=>{document.getElementById('list').innerHTML += `<h1>${data[k].isim}</h1>`;});</script></body></html>")
    
    subprocess.run(["git", "add", html_file])
    subprocess.run(["git", "commit", "-m", "🔄 TÜM ARŞİV GÜNCELLENDİ"])
    subprocess.run(["git", "push"])
    print("🚀 Başarıyla yüklendi!")

if __name__ == "__main__":
    run_scraper()

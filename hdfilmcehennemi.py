import requests
from bs4 import BeautifulSoup
import json
import time
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from urllib.parse import urljoin

# =====================================================
# AYARLAR
# =====================================================
PAGES_TO_SCRAPE = int(sys.argv[1]) if len(sys.argv) > 1 else 10
BASE_URL = "https://www.hdfilmcehennemi.nl"
AJAX_URL = BASE_URL + "/ajax/load/page/{}/categories/film-izle-2/"
OUTPUT_JSON = "hdfilmcehennemi.json"
MAX_WORKERS = 10

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": BASE_URL + "/",
}

session = requests.Session()
session.headers.update(HEADERS)

lock = Lock()

# =====================================================
def slugify(text):
    text = text.lower()
    text = text.replace("ı","i").replace("ğ","g").replace("ü","u").replace("ş","s").replace("ö","o").replace("ç","c")
    text = re.sub(r"[^a-z0-9]", "-", text)
    return re.sub(r"-+", "-", text).strip("-")

# =====================================================
def get_embed_link(url):
    try:
        r = session.get(url, timeout=10)
        if r.status_code != 200:
            return ""

        soup = BeautifulSoup(r.text, "html.parser")
        iframe = soup.find("iframe", class_="close")

        if iframe:
            return iframe.get("data-src") or ""
    except:
        pass
    return ""

# =====================================================
def process_page(page, output):
    url = AJAX_URL.format(page)
    r = session.get(url, timeout=10)

    if r.status_code != 200 or not r.text.strip():
        return 0

    soup = BeautifulSoup(r.text, "html.parser")
    posters = soup.select("a.poster")
    count = 0

    for a in posters:
        name = a.get("title")
        link = a.get("href")

        img = a.find("img")
        poster = img.get("data-src") or img.get("src") if img else ""

        if not name or not link:
            continue

        film_url = urljoin(BASE_URL, link)
        embed = get_embed_link(film_url)

        fid = slugify(name)

        with lock:
            output[fid] = {
                "isim": name,
                "resim": poster,
                "link": embed
            }

        count += 1

    print(f"✅ Sayfa {page}: {count} film")
    return count

# =====================================================
def main():
    print("🚀 HDFilmCehennemi Scraper (GÜNCEL)")
    print(f"📊 Sayfa: {PAGES_TO_SCRAPE}\n")

    films = {}
    start = time.time()

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = [ex.submit(process_page, i, films) for i in range(1, PAGES_TO_SCRAPE + 1)]
        for _ in as_completed(futures):
            pass

    elapsed = time.time() - start

    print("\n" + "="*50)
    print(f"🎬 Toplam Film: {len(films)}")
    print(f"⏱ Süre: {elapsed:.2f} sn")
    print("="*50)

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(films, f, ensure_ascii=False, indent=2)

    print(f"✅ JSON oluşturuldu: {OUTPUT_JSON}")

# =====================================================
if __name__ == "__main__":
    main()

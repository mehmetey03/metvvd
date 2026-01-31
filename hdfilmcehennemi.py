import requests
from bs4 import BeautifulSoup
import json
import time
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from urllib.parse import urljoin

# ======================================================
# AYARLAR
# ======================================================
PAGES_TO_SCRAPE = int(sys.argv[1]) if len(sys.argv) > 1 else 5

BASE_URL = "https://www.hdfilmcehennemi.nl"
AJAX_URL = BASE_URL + "/ajax/load/page/{}/categories/film-izle-2/"
MAX_WORKERS = 6

OUTPUT_JSON = "hdfilmcehennemi.json"

data_lock = Lock()

# ======================================================
# HEADER (CF FREE)
# ======================================================
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept": "*/*",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": BASE_URL + "/",
}

session = requests.Session()
session.headers.update(HEADERS)

# ======================================================
# YARDIMCI FONKSİYONLAR
# ======================================================
def slugify(text):
    text = text.lower()
    text = text.replace("ı", "i").replace("ğ", "g").replace("ü", "u") \
               .replace("ş", "s").replace("ö", "o").replace("ç", "c")
    text = re.sub(r"[^a-z0-9]", "-", text)
    return re.sub(r"-+", "-", text).strip("-")


def extract_film(a):
    name = a.get("title") or a.text.strip()
    link = a.get("href")

    img = a.find("img")
    poster = ""
    if img:
        poster = img.get("data-src") or img.get("src") or ""
        poster = poster.split("?")[0]

    if not name or not link:
        return None

    return name, link, poster


def get_embed_link(film_url):
    try:
        r = session.get(film_url, timeout=10)
        if r.status_code != 200:
            return ""

        soup = BeautifulSoup(r.text, "html.parser")
        iframe = soup.find("iframe", class_="close")

        if iframe:
            return iframe.get("data-src") or iframe.get("src") or ""
    except:
        pass

    return ""


def process_page(page, out):
    url = AJAX_URL.format(page)
    r = session.get(url, timeout=10)

    if r.status_code != 200 or not r.text.strip():
        return 0

    soup = BeautifulSoup(r.text, "html.parser")
    posters = soup.select("a.poster")

    if not posters:
        return 0

    for a in posters:
        data = extract_film(a)
        if not data:
            continue

        name, link, poster = data
        film_url = urljoin(BASE_URL, link)
        embed = get_embed_link(film_url)

        fid = slugify(name)
        with data_lock:
            out[fid] = {
                "isim": name,
                "resim": poster or "https://via.placeholder.com/300x450?text=No+Image",
                "link": embed
            }

    print(f"✅ Sayfa {page}: {len(posters)} film")
    return len(posters)

# ======================================================
# ANA
# ======================================================
def main():
    print("🚀 HDFilmCehennemi Scraper (GÜNCEL YAPI)")
    print(f"📊 Sayfa: {PAGES_TO_SCRAPE}\n")

    films = {}
    start = time.time()

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = [
            ex.submit(process_page, i, films)
            for i in range(1, PAGES_TO_SCRAPE + 1)
        ]
        for _ in as_completed(futures):
            pass

    elapsed = time.time() - start

    print("\n" + "=" * 55)
    print(f"🎬 Toplam Film: {len(films)}")
    print(f"⏱ Süre: {elapsed:.2f} saniye")
    print("=" * 55)

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(films, f, ensure_ascii=False, indent=2)

    print(f"✅ JSON oluşturuldu: {OUTPUT_JSON}")


if __name__ == "__main__":
    main()

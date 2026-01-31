import requests
from bs4 import BeautifulSoup
import json
import time
import re
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from urllib.parse import urljoin

# ============================================================================
# AYARLAR
# ============================================================================
PAGES_TO_SCRAPE = int(sys.argv[1]) if len(sys.argv) > 1 else 5

BASE_URL = "https://www.hdfilmcehennemi.nl"
GITHUB_JSON_URL = "https://raw.githubusercontent.com/mehmetey03/metvvd/refs/heads/main/hdfilmcehennemi.json"

MAX_WORKERS = 6
MAX_RETRIES = 2
RETRY_DELAY = 0.5

data_lock = Lock()

# ============================================================================
# HEADERLAR
# ============================================================================
HEADERS_PAGE = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Referer": "https://www.hdfilmcehennemi.nl/",
    "Accept": "*/*",
    "X-Requested-With": "XMLHttpRequest",
    "Connection": "keep-alive",
}

HEADERS_FILM = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept": "text/html,*/*",
    "Connection": "keep-alive",
}

# ============================================================================
# SESSION
# ============================================================================
session = requests.Session()
adapter = requests.adapters.HTTPAdapter(
    pool_connections=MAX_WORKERS,
    pool_maxsize=MAX_WORKERS,
    max_retries=0
)
session.mount("http://", adapter)
session.mount("https://", adapter)

# ============================================================================
# YARDIMCI FONKSİYONLAR
# ============================================================================
def get_page_data(url, retry=0):
    try:
        r = session.get(url, headers=HEADERS_PAGE, timeout=10)
        r.raise_for_status()
        try:
            return r.json()
        except:
            return {"html": r.text}
    except:
        if retry < MAX_RETRIES:
            time.sleep(RETRY_DELAY)
            return get_page_data(url, retry + 1)
        return None


def get_soup(url, retry=0):
    try:
        r = session.get(url, headers=HEADERS_FILM, timeout=10)
        r.raise_for_status()
        return BeautifulSoup(r.text, "html.parser")
    except:
        if retry < MAX_RETRIES:
            time.sleep(RETRY_DELAY)
            return get_soup(url, retry + 1)
        return None


def slugify(text):
    text = text.lower()
    text = text.replace("ı", "i").replace("ğ", "g").replace("ü", "u").replace("ş", "s").replace("ö", "o").replace("ç", "c")
    text = re.sub(r"[^a-z0-9]", "-", text)
    return re.sub(r"-+", "-", text).strip("-")


def extract_film_data(a):
    film_link = a.get("href")
    film_adi = a.get("title") or a.text.strip()

    img = a.find("img")
    poster = ""
    if img:
        poster = img.get("data-src") or img.get("src") or ""
        poster = poster.split("?")[0]

    if not film_adi or not film_link:
        return None

    return {
        "isim": film_adi,
        "link": film_link,
        "poster": poster
    }


def process_film(info, output):
    film_url = urljoin(BASE_URL, info["link"])
    video_url = ""

    soup = get_soup(film_url)
    if soup:
        iframe = soup.find("iframe", class_="close")
        if iframe:
            src = iframe.get("data-src") or iframe.get("src")
            if src:
                if "rapidrame_id=" in src:
                    rid = src.split("rapidrame_id=")[-1]
                    video_url = f"{BASE_URL}/rplayer/{rid}"
                else:
                    video_url = src

    fid = slugify(info["isim"])
    with data_lock:
        output[fid] = {
            "isim": info["isim"],
            "resim": info["poster"] or "https://via.placeholder.com/300x450?text=No+Image",
            "link": video_url
        }


def process_page(page, output):
    url = f"{BASE_URL}/load/page/{page}/categories/film-izle-2/"
    data = get_page_data(url)

    if not data or "html" not in data:
        return 0

    html = data["html"]
    print(f"🔍 Sayfa {page} HTML uzunluğu: {len(html)}")

    soup = BeautifulSoup(html, "html.parser")
    films = soup.find_all("a", class_="poster")

    if not films:
        return 0

    with ThreadPoolExecutor(max_workers=4) as ex:
        tasks = []
        for a in films:
            info = extract_film_data(a)
            if info:
                tasks.append(
                    ex.submit(process_film, info, output)
                )

        for _ in as_completed(tasks):
            pass

    print(f"✅ Sayfa {page}: {len(films)} film")
    return len(films)

# ============================================================================
# ANA
# ============================================================================
def main():
    print("🚀 HDFilmCehennemi Scraper Başladı")
    print(f"📊 Sayfa: {PAGES_TO_SCRAPE}\n")

    films = {}
    start = time.time()

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = []
        for i in range(1, PAGES_TO_SCRAPE + 1):
            futures.append(ex.submit(process_page, i, films))

        for _ in as_completed(futures):
            pass

    elapsed = time.time() - start

    print("\n" + "=" * 50)
    print(f"🎬 Toplam Film: {len(films)}")
    print(f"⏱ Süre: {elapsed:.2f} saniye")
    print("=" * 50)

    with open("hdfilmcehennemi.json", "w", encoding="utf-8") as f:
        json.dump(films, f, ensure_ascii=False, indent=2)

    print("✅ JSON oluşturuldu: hdfilmcehennemi.json")


if __name__ == "__main__":
    main()

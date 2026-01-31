from bs4 import BeautifulSoup
import json

soup = BeautifulSoup(html_content, "html.parser")

film_elements = soup.select("a.poster")
films = []

for film in film_elements:
    film_data = {}

    # Başlık
    title = film.get("title")
    film_data["title"] = title.strip() if title else None

    # Link
    film_data["link"] = film.get("href")

    # Meta alanı (yıl / yorum)
    meta_div = film.find("div", class_="poster-meta")
    spans = meta_div.find_all("span") if meta_div else []

    film_data["year"] = spans[0].text.strip() if len(spans) > 0 else None
    film_data["comment_count"] = spans[1].text.strip() if len(spans) > 1 else None

    # IMDB
    imdb = film.find("span", class_="imdb")
    film_data["imdb_rating"] = imdb.text.strip() if imdb else None

    # Dil bilgisi
    lang = film.find("span", class_="poster-lang")
    if lang:
        if lang.find("i", class_="tr-flag"):
            film_data["language"] = "Türkçe Dublaj"
        else:
            span = lang.find("span")
            film_data["language"] = span.text.strip() if span else None
    else:
        film_data["language"] = None

    # Resim
    img = film.find("img")
    if img:
        film_data["image"] = img.get("data-src") or img.get("src")
        srcset = img.get("data-srcset")
        if srcset:
            parts = srcset.split()
            film_data["image_2x"] = parts[1] if len(parts) > 1 else None
        else:
            film_data["image_2x"] = None
    else:
        film_data["image"] = None
        film_data["image_2x"] = None

    # Popover (detaylar)
    popover = film.find_parent().find("div", class_="poster-popover")
    if popover:
        rating_block = popover.find("div", class_="popover-rating")
        if rating_block:
            p = rating_block.find("p")
            span = rating_block.find("span", class_="review-count")
            film_data["detailed_imdb"] = p.text.strip() if p else None
            film_data["review_count"] = span.text.strip() if span else None

        desc = popover.find("p", class_="popover-description")
        if desc:
            film_data["summary"] = desc.text.replace("Özet", "").strip()

        for meta in popover.find_all("span"):
            strong = meta.find("strong")
            if not strong:
                continue

            key = strong.text.lower()
            strong.extract()
            value = meta.text.strip()

            if "kanal" in key:
                film_data["channel"] = value
            elif "tür" in key:
                film_data["genres"] = [g.strip() for g in value.split(",")]
            elif "kategori" in key:
                film_data["category"] = value

    films.append(film_data)

# JSON kaydet
with open("films.json", "w", encoding="utf-8") as f:
    json.dump(films, f, ensure_ascii=False, indent=2)

print(f"✅ Toplam {len(films)} film bulundu")

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Kanal D Dizi Scraper - HTML Çıktılı
- Kanal D dizilerini ve bölümlerini tarar
- Doğrudan arşivden dizi listesi çeker
- ShowTV benzeri HTML arayüz oluşturur
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import re
import os
from urllib.parse import urljoin, urlparse

# Web sitesi kök adresi
BASE_URL = "https://www.kanald.com.tr"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Referer": BASE_URL,
}

# Yeniden deneme ayarları
MAX_RETRIES = 2
RETRY_DELAY = 1

def get_soup(url, retry_count=0):
    """URL'den BeautifulSoup nesnesi döndürür."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        response.encoding = 'utf-8'
        return BeautifulSoup(response.content, "html.parser")
    except Exception as e:
        if retry_count < MAX_RETRIES:
            time.sleep(RETRY_DELAY)
            return get_soup(url, retry_count + 1)
        else:
            print(f"      ✗ Hata: {str(e)[:80]}")
            return None

def slugify(text):
    """Metni ID olarak kullanılabilecek formata çevirir"""
    if not text:
        return "dizi"
    
    replacements = {
        'ı': 'i', 'İ': 'i', 'ğ': 'g', 'Ğ': 'g',
        'ü': 'u', 'Ü': 'u', 'ş': 's', 'Ş': 's',
        'ö': 'o', 'Ö': 'o', 'ç': 'c', 'Ç': 'c',
        'â': 'a', 'î': 'i', 'û': 'u'
    }
    
    for old, new in replacements.items():
        text = text.replace(old, new)
    
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '-', text)
    text = text.strip('-')
    
    return text

def extract_episode_number(name):
    """Bölüm adından numarayı çeker"""
    if not name:
        return 9999
    
    match = re.search(r'(\d+)\.\s*Bölüm', name)
    if match:
        return int(match.group(1))
    
    match = re.search(r'Bölüm\s*(\d+)', name, re.IGNORECASE)
    if match:
        return int(match.group(1))
    
    match = re.search(r'Sezon\s*\d+\s*Bölüm\s*(\d+)', name, re.IGNORECASE)
    if match:
        return int(match.group(1))
    
    return 9999

def extract_episode_number_only(name):
    """Bölüm adından sadece sayıyı çıkarır"""
    if not name:
        return "Bölüm"
    
    match = re.search(r'(\d+)\.\s*Bölüm', name)
    if match:
        return f"{match.group(1)}. Bölüm"
    
    match = re.search(r'Bölüm\s*(\d+)', name, re.IGNORECASE)
    if match:
        return f"{match.group(1)}. Bölüm"
    
    match = re.search(r'Sezon\s*\d+\s*Bölüm\s*(\d+)', name, re.IGNORECASE)
    if match:
        return f"{match.group(1)}. Bölüm"
    
    return name

def get_series_from_sitemap():
    """Site haritasından veya ana sayfadan dizileri çeker"""
    print("Kanal D dizileri aranıyor...")
    
    series_list = []
    
    # Önce ana diziler sayfasına bak
    urls_to_check = [
        f"{BASE_URL}/diziler",
        f"{BASE_URL}/diziler/arsiv",
        f"{BASE_URL}/programlar"
    ]
    
    for url in urls_to_check:
        print(f"  {url} kontrol ediliyor...")
        soup = get_soup(url)
        if not soup:
            continue
        
        # Dizi linklerini ara
        links = soup.find_all("a", href=True)
        
        for link in links:
            href = link.get("href", "")
            
            # Dizi linklerini filtrele
            if "/diziler/" in href and href != "/diziler/arsiv" and "/diziler/" != href:
                full_url = urljoin(BASE_URL, href)
                
                # Tekrar kontrolü
                if any(s["url"] == full_url for s in series_list):
                    continue
                
                # Dizi adını bul
                series_name = ""
                
                # İmg alt text
                img = link.find("img")
                if img and img.get("alt"):
                    series_name = img.get("alt").strip()
                elif link.get("title"):
                    series_name = link.get("title").strip()
                else:
                    # Yakınlardaki text
                    parent = link.parent
                    for elem in [link, parent]:
                        if elem:
                            h_tags = elem.find_all(["h2", "h3", "h4", "h5"])
                            for h in h_tags:
                                text = h.get_text(strip=True)
                                if text and len(text) > 2:
                                    series_name = text
                                    break
                        if series_name:
                            break
                
                if not series_name:
                    # URL'den isim çıkar
                    path = urlparse(full_url).path
                    name_from_url = path.split('/')[-1].replace('-', ' ').title()
                    series_name = name_from_url
                
                # Poster URL'si
                poster_url = ""
                if img:
                    poster_url = img.get("data-src") or img.get("src") or ""
                    if poster_url:
                        poster_url = urljoin(BASE_URL, poster_url)
                
                if series_name and full_url:
                    series_list.append({
                        "name": series_name,
                        "url": full_url,
                        "poster": poster_url
                    })
    
    # Benzersiz diziler
    unique_series = []
    seen_urls = set()
    
    for series in series_list:
        if series["url"] not in seen_urls:
            # URL'yi temizle (fragment kaldır)
            clean_url = series["url"].split('#')[0].split('?')[0]
            series["url"] = clean_url
            
            # İsmi temizle
            series["name"] = series["name"].replace('İzle', '').replace('Kanal D', '').strip()
            
            unique_series.append(series)
            seen_urls.add(clean_url)
    
    print(f"  Toplam {len(unique_series)} benzersiz dizi bulundu")
    
    # Eğer çok az dizi bulduysak, manuel ekle
    if len(unique_series) < 10:
        print("  Manuel olarak popüler diziler ekleniyor...")
        popular_series = [
            {"name": "Kardeşlerim", "url": f"{BASE_URL}/diziler/kardeslerim", "poster": ""},
            {"name": "Kuzey Yıldızı", "url": f"{BASE_URL}/diziler/kuzey-yildizi", "poster": ""},
            {"name": "Elbet Bir Gün", "url": f"{BASE_URL}/diziler/elbet-bir-gun", "poster": ""},
            {"name": "Ramo", "url": f"{BASE_URL}/diziler/ramo", "poster": ""},
            {"name": "Yargı", "url": f"{BASE_URL}/diziler/yargi", "poster": ""},
            {"name": "Çukur", "url": f"{BASE_URL}/diziler/cukur", "poster": ""},
            {"name": "Eşkıya Dünyaya Hükümdar Olmaz", "url": f"{BASE_URL}/diziler/eskıya-dunyaya-hukumdar-olamaz", "poster": ""},
            {"name": "Kuruluş Osman", "url": f"{BASE_URL}/diziler/kurulus-osman", "poster": ""},
            {"name": "Uyanış Büyük Selçuklu", "url": f"{BASE_URL}/diziler/uyanis-buyuk-selcuklu", "poster": ""},
        ]
        
        for series in popular_series:
            if series["url"] not in seen_urls:
                unique_series.append(series)
                seen_urls.add(series["url"])
    
    return unique_series[:50]  # İlk 50 dizi

def get_episodes_from_series_page(series_url, series_name):
    """Dizi sayfasından bölümleri çeker"""
    episodes = []
    
    print(f"    '{series_name}' bölümleri aranıyor...")
    
    soup = get_soup(series_url)
    if not soup:
        return episodes
    
    # Video listesini ara
    video_selectors = [
        "a[href*='/video/']",
        "a[href*='/izle/']",
        "div[data-media-id]",
        "div.episode",
        "div.video-item",
        "div.media-item"
    ]
    
    video_items = []
    
    for selector in video_selectors:
        items = soup.select(selector)
        if items:
            video_items.extend(items)
    
    # Eğer yukarıdakiler işe yaramazsa, tüm linkleri kontrol et
    if not video_items:
        all_links = soup.find_all("a", href=True)
        for link in all_links:
            href = link.get("href", "")
            if "/video/" in href or "/izle/" in href:
                video_items.append(link)
    
    print(f"      {len(video_items)} video öğesi bulundu")
    
    for item in video_items[:30]:  # İlk 30 bölüm
        try:
            # Media ID'yi bul
            media_id = None
            
            # data-media-id attribute'ü
            media_id = item.get("data-media-id")
            
            # data-id attribute'ü
            if not media_id:
                media_id = item.get("data-id")
            
            # Linkten çıkar
            if not media_id:
                href = item.get("href", "")
                match = re.search(r'/video/(\d+)', href)
                if match:
                    media_id = match.group(1)
            
            if not media_id:
                continue
            
            # Bölüm adını bul
            episode_name = ""
            
            # Title attribute
            title_attr = item.get("title") or item.get("data-title")
            if title_attr:
                episode_name = title_attr.strip()
            else:
                # Text içeriği
                text_elem = item.find(["h3", "h4", "div.title", "span.title"])
                if text_elem:
                    episode_name = text_elem.get_text(strip=True)
                else:
                    # Kendi text'i
                    episode_name = item.get_text(strip=True)
            
            # Poster
            poster_url = ""
            img_tag = item.find("img")
            if img_tag:
                poster_url = img_tag.get("data-src") or img_tag.get("src") or ""
                if poster_url:
                    poster_url = urljoin(BASE_URL, poster_url)
            
            episodes.append({
                "id": media_id,
                "name": episode_name or f"Bölüm {len(episodes) + 1}",
                "poster": poster_url
            })
            
        except Exception as e:
            continue
    
    return episodes

def get_video_stream_from_api(media_id):
    """Kanal D API'sinden video stream URL'sini alır"""
    try:
        api_url = "https://www.kanald.com.tr/actions/media"
        
        headers = {
            "User-Agent": HEADERS["User-Agent"],
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": BASE_URL
        }
        
        data = {"id": media_id}
        
        response = requests.post(api_url, headers=headers, data=data, timeout=10)
        response.raise_for_status()
        
        result = response.json()
        
        if result.get("status") == "success" and "media" in result:
            media = result["media"]
            
            # M3U8 ara
            if "files" in media:
                for file in media["files"]:
                    if file.get("type") == "application/x-mpegURL":
                        url = file.get("url")
                        if url:
                            if url.startswith("//"):
                                return "https:" + url
                            elif url.startswith("/"):
                                return BASE_URL + url
                            return url
            
            # MP4 ara
            if "mp4" in media:
                for mp4 in media["mp4"]:
                    url = mp4.get("src")
                    if url:
                        if url.startswith("//"):
                            return "https:" + url
                        elif url.startswith("/"):
                            return BASE_URL + url
                        return url
        
        return None
        
    except Exception as e:
        return None

def get_video_stream_from_page(page_url):
    """Video sayfasından stream URL'sini çeker"""
    try:
        soup = get_soup(page_url)
        if not soup:
            return None
        
        # Video etiketini ara
        video_tag = soup.find("video")
        if video_tag:
            source = video_tag.find("source")
            if source and source.get("src"):
                url = source.get("src")
                if url.startswith("//"):
                    return "https:" + url
                elif url.startswith("/"):
                    return BASE_URL + url
                return url
        
        # Script içinde video URL'sini ara
        scripts = soup.find_all("script")
        for script in scripts:
            if script.string:
                # M3U8 URL'sini ara
                match = re.search(r'(https?://[^\s"\']+\.m3u8[^\s"\']*)', script.string)
                if match:
                    return match.group(1)
                
                # MP4 URL'sini ara
                match = re.search(r'(https?://[^\s"\']+\.mp4[^\s"\']*)', script.string)
                if match:
                    return match.group(1)
        
        return None
        
    except Exception as e:
        return None

def main():
    print("=" * 60)
    print("KANAL D DİZİ SCRAPER - GÜNCELLENMİŞ")
    print("=" * 60)
    
    # Tüm dizileri al
    all_series = get_series_from_sitemap()
    
    if not all_series:
        print("Hiç dizi bulunamadı! Test moduna geçiliyor...")
        all_series = [
            {"name": "Kardeşlerim", "url": f"{BASE_URL}/diziler/kardeslerim", "poster": ""},
            {"name": "Kuzey Yıldızı", "url": f"{BASE_URL}/diziler/kuzey-yildizi", "poster": ""},
        ]
    
    diziler_data = {}
    
    # Test için sadece ilk 5 dizi
    test_series = all_series[:5]
    
    for idx, series in enumerate(test_series, 1):
        series_name = series["name"]
        series_url = series["url"]
        series_poster = series["poster"]
        series_id = slugify(series_name)
        
        print(f"\n[{idx}/{len(test_series)}] {series_name}")
        print(f"  URL: {series_url}")
        
        # Bölümleri al
        episodes = get_episodes_from_series_page(series_url, series_name)
        
        if not episodes:
            print(f"  ⚠ Hiç bölüm bulunamadı! Doğrudan dizi sayfası taranıyor...")
            
            # Dizi sayfasından video linklerini ara
            soup = get_soup(series_url)
            if soup:
                video_links = soup.find_all("a", href=lambda x: x and "/video/" in x)
                for link in video_links[:10]:  # İlk 10 video
                    href = link.get("href", "")
                    media_match = re.search(r'/video/(\d+)', href)
                    if media_match:
                        media_id = media_match.group(1)
                        episode_name = link.get_text(strip=True) or f"Video {media_id}"
                        episodes.append({
                            "id": media_id,
                            "name": episode_name,
                            "poster": ""
                        })
        
        if not episodes:
            print(f"  ⚠ Bölüm bulunamadı, atlanıyor")
            continue
        
        print(f"  📺 {len(episodes)} bölüm bulundu, stream URL'leri alınıyor...")
        
        final_episodes = []
        
        # Her bölüm için stream URL'sini al
        for ep_idx, episode in enumerate(episodes[:10], 1):  # İlk 10 bölüm
            print(f"    [{ep_idx}/{min(len(episodes), 10)}] {episode['name'][:40]}...")
            
            # Önce API'den almayı dene
            stream_url = None
            
            if episode.get("id"):
                stream_url = get_video_stream_from_api(episode["id"])
            
            # Eğer API'den alamazsak, video sayfasına git
            if not stream_url and episode.get("id"):
                video_page = f"{BASE_URL}/video/{episode['id']}"
                stream_url = get_video_stream_from_page(video_page)
            
            if stream_url:
                final_episodes.append({
                    "ad": extract_episode_number_only(episode["name"]),
                    "link": stream_url,
                    "episode_num": extract_episode_number(episode["name"])
                })
                print(f"      ✅ Stream URL bulundu")
            else:
                print(f"      ⚠ Stream URL bulunamadı")
            
            time.sleep(0.5)
        
        if final_episodes:
            # Bölümleri sırala
            final_episodes.sort(key=lambda x: x["episode_num"])
            
            diziler_data[series_id] = {
                "name": series_name,
                "resim": series_poster or f"https://via.placeholder.com/300x450/1e3a5f/ffffff?text={series_name.replace(' ', '+')}",
                "url": series_url,
                "bolumler": [{"ad": ep["ad"], "link": ep["link"]} for ep in final_episodes]
            }
            
            print(f"  ✅ {len(final_episodes)} bölüm eklendi")
        else:
            print(f"  ⚠ Stream URL'si bulunan bölüm yok")
    
    print("\n" + "=" * 60)
    
    if diziler_data:
        print(f"Toplam {len(diziler_data)} dizi başarıyla işlendi!")
        print("=" * 60)
        
        # HTML dosyasını oluştur
        create_html_file(diziler_data)
    else:
        print("Hiç dizi işlenemedi! Test verisi ile HTML oluşturuluyor...")
        create_test_html()

def create_html_file(data):
    """HTML arayüz dosyasını oluşturur"""
    # JSON verisini hazırla
    json_str = json.dumps(data, ensure_ascii=False)
    
    html_template = f'''<!DOCTYPE html>
<html lang="tr">
<head>
    <title>Kanal D VOD</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, user-scalable=no, initial-scale=1.0">
    <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Roboto', sans-serif;
            background: linear-gradient(135deg, #0c233b 0%, #1a3a5c 100%);
            color: #fff;
            min-height: 100vh;
            padding-bottom: 50px;
        }}
        
        .header {{
            background: rgba(12, 35, 59, 0.95);
            padding: 20px;
            text-align: center;
            border-bottom: 3px solid #e62117;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            position: sticky;
            top: 0;
            z-index: 100;
        }}
        
        .logo {{
            font-size: 32px;
            font-weight: 700;
            color: #fff;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
        }}
        
        .logo span {{
            color: #e62117;
        }}
        
        .subtitle {{
            font-size: 14px;
            color: #a0c8ff;
            margin-top: 5px;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }}
        
        .search-container {{
            margin: 30px auto;
            max-width: 600px;
            position: relative;
        }}
        
        .search-box {{
            width: 100%;
            padding: 16px 50px 16px 20px;
            border: 2px solid #2a4a75;
            border-radius: 30px;
            background: rgba(255,255,255,0.1);
            color: white;
            font-size: 16px;
            outline: none;
            transition: all 0.3s;
        }}
        
        .search-box:focus {{
            border-color: #e62117;
            background: rgba(255,255,255,0.15);
            box-shadow: 0 0 15px rgba(230, 33, 23, 0.3);
        }}
        
        .search-box::placeholder {{
            color: rgba(255,255,255,0.6);
        }}
        
        .search-icon {{
            position: absolute;
            right: 20px;
            top: 50%;
            transform: translateY(-50%);
            color: #a0c8ff;
            font-size: 20px;
        }}
        
        .section-title {{
            font-size: 24px;
            margin: 30px 0 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #2a4a75;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .series-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
            gap: 25px;
        }}
        
        .series-card {{
            background: rgba(26, 58, 92, 0.7);
            border-radius: 15px;
            overflow: hidden;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            cursor: pointer;
            box-shadow: 0 6px 12px rgba(0,0,0,0.2);
            border: 2px solid transparent;
        }}
        
        .series-card:hover {{
            transform: translateY(-10px) scale(1.02);
            box-shadow: 0 15px 30px rgba(0,0,0,0.4);
            border-color: #e62117;
            background: rgba(26, 58, 92, 0.9);
        }}
        
        .series-poster {{
            width: 100%;
            height: 300px;
            object-fit: cover;
            display: block;
            transition: transform 0.5s;
        }}
        
        .series-card:hover .series-poster {{
            transform: scale(1.05);
        }}
        
        .series-info {{
            padding: 18px;
        }}
        
        .series-name {{
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 8px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        
        .series-episodes {{
            font-size: 14px;
            color: #a0c8ff;
            display: flex;
            align-items: center;
            gap: 5px;
        }}
        
        .episodes-container {{
            display: none;
            animation: fadeIn 0.5s;
        }}
        
        .back-button {{
            background: #e62117;
            color: white;
            border: none;
            padding: 12px 25px;
            border-radius: 30px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 10px;
            margin: 20px 0;
            transition: all 0.3s;
        }}
        
        .back-button:hover {{
            background: #ff3d32;
            transform: translateX(-5px);
        }}
        
        .episodes-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }}
        
        .episode-card {{
            background: rgba(42, 74, 117, 0.7);
            border-radius: 12px;
            overflow: hidden;
            cursor: pointer;
            transition: all 0.3s;
            border: 2px solid transparent;
        }}
        
        .episode-card:hover {{
            transform: scale(1.05);
            border-color: #e62117;
            background: rgba(42, 74, 117, 0.9);
            box-shadow: 0 8px 20px rgba(0,0,0,0.3);
        }}
        
        .episode-poster {{
            width: 100%;
            height: 120px;
            object-fit: cover;
        }}
        
        .episode-info {{
            padding: 15px;
        }}
        
        .episode-name {{
            font-size: 14px;
            font-weight: 500;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        
        .player-overlay {{
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.95);
            z-index: 1000;
            display: none;
            flex-direction: column;
        }}
        
        .player-header {{
            padding: 20px;
            background: rgba(12, 35, 59, 0.9);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .player-title {{
            font-size: 20px;
            font-weight: 600;
            color: white;
        }}
        
        .close-player {{
            background: #e62117;
            color: white;
            border: none;
            width: 40px;
            height: 40px;
            border-radius: 50%;
            font-size: 18px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.3s;
        }}
        
        .close-player:hover {{
            background: #ff3d32;
            transform: rotate(90deg);
        }}
        
        .video-container {{
            flex: 1;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }}
        
        video {{
            width: 100%;
            max-width: 1200px;
            max-height: 80vh;
            border-radius: 10px;
            outline: none;
        }}
        
        .no-results {{
            text-align: center;
            padding: 60px 20px;
            color: rgba(255,255,255,0.7);
            display: none;
        }}
        
        .no-results i {{
            font-size: 60px;
            margin-bottom: 20px;
            color: #2a4a75;
        }}
        
        .loading {{
            text-align: center;
            padding: 40px;
            font-size: 18px;
            color: #a0c8ff;
        }}
        
        .loading i {{
            font-size: 40px;
            margin-bottom: 15px;
            animation: spin 2s linear infinite;
        }}
        
        @keyframes spin {{
            0% {{ transform: rotate(0deg); }}
            100% {{ transform: rotate(360deg); }}
        }}
        
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(20px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        
        @media (max-width: 768px) {{
            .series-grid {{
                grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
                gap: 15px;
            }}
            
            .series-poster {{
                height: 220px;
            }}
            
            .episodes-grid {{
                grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
                gap: 15px;
            }}
            
            .container {{
                padding: 15px;
            }}
            
            .logo {{
                font-size: 28px;
            }}
        }}
        
        @media (max-width: 480px) {{
            .series-grid {{
                grid-template-columns: repeat(2, 1fr);
            }}
            
            .series-poster {{
                height: 180px;
            }}
            
            .episodes-grid {{
                grid-template-columns: repeat(2, 1fr);
            }}
            
            .search-box {{
                padding: 14px 45px 14px 15px;
                font-size: 14px;
            }}
        }}
        
        .stats {{
            display: flex;
            justify-content: center;
            gap: 30px;
            margin: 20px 0 40px;
            flex-wrap: wrap;
        }}
        
        .stat-item {{
            background: rgba(255,255,255,0.1);
            padding: 15px 25px;
            border-radius: 10px;
            text-align: center;
            min-width: 150px;
        }}
        
        .stat-number {{
            font-size: 32px;
            font-weight: 700;
            color: #e62117;
            display: block;
        }}
        
        .stat-label {{
            font-size: 14px;
            color: #a0c8ff;
        }}
    </style>
</head>
<body>
    <div class="header">
        <div class="logo">KANAL<span>D</span> VOD</div>
        <div class="subtitle">Tüm diziler ve bölümler burada</div>
    </div>
    
    <div class="container">
        <div class="search-container">
            <input type="text" id="searchInput" class="search-box" placeholder="Dizi ara...">
            <div class="search-icon">
                <i class="fas fa-search"></i>
            </div>
        </div>
        
        <div class="stats" id="statsContainer">
            <div class="stat-item">
                <span class="stat-number" id="seriesCount">0</span>
                <span class="stat-label">Dizi</span>
            </div>
            <div class="stat-item">
                <span class="stat-number" id="episodesCount">0</span>
                <span class="stat-label">Bölüm</span>
            </div>
        </div>
        
        <div id="mainContent">
            <div class="section-title">
                <span>Tüm Diziler</span>
                <span id="seriesCounter">0 dizi</span>
            </div>
            <div id="seriesList" class="series-grid">
                <!-- Diziler buraya eklenecek -->
            </div>
        </div>
        
        <div id="episodesContent" class="episodes-container">
            <button class="back-button" onclick="goBackToSeries()">
                <i class="fas fa-arrow-left"></i> Dizilere Dön
            </button>
            <div class="section-title">
                <span id="currentSeriesTitle">Bölümler</span>
                <span id="episodesCounter">0 bölüm</span>
            </div>
            <div id="episodesList" class="episodes-grid">
                <!-- Bölümler buraya eklenecek -->
            </div>
        </div>
        
        <div class="no-results" id="noResults">
            <i class="fas fa-search"></i>
            <h3>Aradığınız dizi bulunamadı</h3>
            <p>Lütfen farklı bir anahtar kelime deneyin</p>
        </div>
        
        <div class="loading" id="loadingIndicator" style="display: none;">
            <i class="fas fa-spinner"></i>
            <p>Yükleniyor...</p>
        </div>
    </div>
    
    <div class="player-overlay" id="playerOverlay">
        <div class="player-header">
            <div class="player-title" id="playerTitle">Video Oynatıcı</div>
            <button class="close-player" onclick="closePlayer()">
                <i class="fas fa-times"></i>
            </button>
        </div>
        <div class="video-container">
            <video id="videoPlayer" controls autoplay playsinline>
                <source id="videoSource" src="" type="video/mp4">
                Tarayıcınız video etiketini desteklemiyor.
            </video>
        </div>
    </div>

    <script>
        // Dizi verileri
        const diziler = {json_str};
        
        // İstatistikleri güncelle
        function updateStats() {{
            const seriesCount = Object.keys(diziler).length;
            let episodesCount = 0;
            
            Object.values(diziler).forEach(series => {{
                episodesCount += series.bolumler ? series.bolumler.length : 0;
            }});
            
            document.getElementById('seriesCount').textContent = seriesCount;
            document.getElementById('episodesCount').textContent = episodesCount;
            document.getElementById('seriesCounter').textContent = `${{seriesCount}} dizi`;
        }}
        
        // Dizileri yükle
        function loadSeries() {{
            const container = document.getElementById('seriesList');
            container.innerHTML = '';
            
            Object.keys(diziler).forEach(seriesId => {{
                const series = diziler[seriesId];
                const episodesCount = series.bolumler ? series.bolumler.length : 0;
                
                const card = document.createElement('div');
                card.className = 'series-card';
                card.onclick = () => showEpisodes(seriesId);
                
                const poster = series.resim || `https://via.placeholder.com/300x450/1e3a5f/ffffff?text=${{encodeURIComponent(series.name)}}`;
                const name = series.name || seriesId.replace(/-/g, ' ').toUpperCase();
                
                card.innerHTML = `
                    <img src="${{poster}}" alt="${{name}}" class="series-poster"
                         onerror="this.src='https://via.placeholder.com/300x450/1e3a5f/ffffff?text=Dizi'">
                    <div class="series-info">
                        <div class="series-name">${{name}}</div>
                        <div class="series-episodes">
                            <i class="fas fa-play-circle"></i>
                            <span>${{episodesCount}} bölüm</span>
                        </div>
                    </div>
                `;
                
                container.appendChild(card);
            }});
            
            updateStats();
        }}
        
        // Bölümleri göster
        function showEpisodes(seriesId) {{
            const series = diziler[seriesId];
            if (!series || !series.bolumler || series.bolumler.length === 0) {{
                alert('Bu dizi için bölüm bulunamadı.');
                return;
            }}
            
            // Ana içeriği gizle
            document.getElementById('mainContent').style.display = 'none';
            document.getElementById('statsContainer').style.display = 'none';
            document.getElementById('noResults').style.display = 'none';
            
            // Bölümleri göster
            const episodesContainer = document.getElementById('episodesContent');
            const episodesList = document.getElementById('episodesList');
            const seriesTitle = document.getElementById('currentSeriesTitle');
            const episodesCounter = document.getElementById('episodesCounter');
            
            seriesTitle.textContent = series.name;
            episodesCounter.textContent = `${{series.bolumler.length}} bölüm`;
            
            episodesList.innerHTML = '';
            
            series.bolumler.forEach((episode, index) => {{
                const card = document.createElement('div');
                card.className = 'episode-card';
                card.onclick = () => playVideo(episode.link, episode.ad || `Bölüm ${{index + 1}}`);
                
                const poster = series.resim || `https://via.placeholder.com/300x450/1e3a5f/ffffff?text=${{encodeURIComponent(series.name)}}`;
                const name = episode.ad || `Bölüm ${{index + 1}}`;
                
                card.innerHTML = `
                    <img src="${{poster}}" alt="${{name}}" class="episode-poster"
                         onerror="this.src='https://via.placeholder.com/300x169/1e3a5f/ffffff?text=Bölüm'">
                    <div class="episode-info">
                        <div class="episode-name">${{name}}</div>
                    </div>
                `;
                
                episodesList.appendChild(card);
            }});
            
            episodesContainer.style.display = 'block';
            window.scrollTo({{ top: 0, behavior: 'smooth' }});
        }}
        
        // Dizilere dön
        function goBackToSeries() {{
            document.getElementById('episodesContent').style.display = 'none';
            document.getElementById('mainContent').style.display = 'block';
            document.getElementById('statsContainer').style.display = 'flex';
            document.getElementById('searchInput').value = '';
            filterSeries();
            window.scrollTo({{ top: 0, behavior: 'smooth' }});
        }}
        
        // Video oynat
        function playVideo(videoUrl, videoTitle) {{
            const playerOverlay = document.getElementById('playerOverlay');
            const videoPlayer = document.getElementById('videoPlayer');
            const videoSource = document.getElementById('videoSource');
            const playerTitle = document.getElementById('playerTitle');
            
            playerTitle.textContent = videoTitle || 'Video';
            
            // Video kaynağını ayarla
            videoSource.src = videoUrl;
            videoPlayer.load();
            
            // Player'ı göster
            playerOverlay.style.display = 'flex';
            
            // Video oynat
            const playPromise = videoPlayer.play();
            
            if (playPromise !== undefined) {{
                playPromise.catch(error => {{
                    console.log('Otomatik oynatma engellendi:', error);
                }});
            }}
        }}
        
        // Player'ı kapat
        function closePlayer() {{
            const playerOverlay = document.getElementById('playerOverlay');
            const videoPlayer = document.getElementById('videoPlayer');
            
            videoPlayer.pause();
            videoPlayer.currentTime = 0;
            playerOverlay.style.display = 'none';
        }}
        
        // Dizileri filtrele
        function filterSeries() {{
            const searchTerm = document.getElementById('searchInput').value.toLowerCase().trim();
            const container = document.getElementById('seriesList');
            const noResults = document.getElementById('noResults');
            const cards = container.getElementsByClassName('series-card');
            
            let visibleCount = 0;
            
            for (let card of cards) {{
                const seriesName = card.querySelector('.series-name').textContent.toLowerCase();
                const isVisible = searchTerm === '' || seriesName.includes(searchTerm);
                
                card.style.display = isVisible ? 'block' : 'none';
                if (isVisible) visibleCount++;
            }}
            
            if (searchTerm !== '' && visibleCount === 0) {{
                noResults.style.display = 'block';
                container.style.display = 'none';
            }} else {{
                noResults.style.display = 'none';
                container.style.display = 'grid';
            }}
        }}
        
        // Sayfa yüklendiğinde
        document.addEventListener('DOMContentLoaded', () => {{
            loadSeries();
            
            // Arama kutusu event listener
            document.getElementById('searchInput').addEventListener('input', filterSeries);
            
            // ESC tuşu ile player'ı kapat
            document.addEventListener('keydown', (e) => {{
                if (e.key === 'Escape') {{
                    closePlayer();
                }}
            }});
            
            // Video hata yönetimi
            document.getElementById('videoPlayer').addEventListener('error', (e) => {{
                console.error('Video hatası:', e);
                alert('Video yüklenirken bir hata oluştu. Lütfen daha sonra tekrar deneyin.');
            }});
        }});
        
        // İlk yükleme
        loadSeries();
    </script>
</body>
</html>'''
    
    filename = "kanald_vod.html"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html_template)
    
    print(f"\n✅ HTML dosyası '{filename}' başarıyla oluşturuldu!")
    
    total_series = len(data)
    total_episodes = sum(len(dizi['bolumler']) for dizi in data.values())
    
    print(f"📂 Dosya boyutu: {os.path.getsize(filename) / 1024:.1f} KB")
    print(f"🎬 Toplam dizi: {total_series}")
    print(f"📺 Toplam bölüm: {total_episodes}")

def create_test_html():
    """Test HTML dosyası oluştur"""
    test_data = {
        "test-dizi-1": {
            "name": "Test Dizi 1",
            "resim": "https://via.placeholder.com/300x450/1e3a5f/ffffff?text=Test+Dizi+1",
            "url": "https://www.kanald.com.tr/test",
            "bolumler": [
                {"ad": "1. Bölüm", "link": "https://example.com/test1.m3u8"},
                {"ad": "2. Bölüm", "link": "https://example.com/test2.m3u8"}
            ]
        },
        "test-dizi-2": {
            "name": "Test Dizi 2",
            "resim": "https://via.placeholder.com/300x450/1e3a5f/ffffff?text=Test+Dizi+2",
            "url": "https://www.kanald.com.tr/test2",
            "bolumler": [
                {"ad": "1. Bölüm", "link": "https://example.com/test3.m3u8"},
                {"ad": "2. Bölüm", "link": "https://example.com/test4.m3u8"},
                {"ad": "3. Bölüm", "link": "https://example.com/test5.m3u8"}
            ]
        }
    }
    
    create_html_file(test_data)

if __name__ == "__main__":
    main()

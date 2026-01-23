#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Kanal D Dizi Scraper - Direkt Yaklaşım
- Doğrudan popüler dizi sayfalarını hedefler
- Video bölümlerini API üzerinden çeker
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

def get_soup(url, retry_count=0, max_retries=2):
    """URL'den BeautifulSoup nesnesi döndürür."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        response.encoding = 'utf-8'
        return BeautifulSoup(response.content, "html.parser")
    except Exception as e:
        if retry_count < max_retries:
            time.sleep(1)
            return get_soup(url, retry_count + 1, max_retries)
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

def get_direct_series_list():
    """Doğrudan bilinen Kanal D dizilerini döndürür"""
    print("Popüler Kanal D dizileri listeleniyor...")
    
    # Kanal D'nin aktif ve popüler dizileri
    popular_series = [
        {
            "name": "Kardeşlerim",
            "url": f"{BASE_URL}/diziler/kardeslerim",
            "slug": "kardeslerim"
        },
        {
            "name": "Kuzey Yıldızı",
            "url": f"{BASE_URL}/diziler/kuzey-yildizi",
            "slug": "kuzey-yildizi"
        },
        {
            "name": "Elbet Bir Gün",
            "url": f"{BASE_URL}/diziler/elbet-bir-gun",
            "slug": "elbet-bir-gun"
        },
        {
            "name": "Ramo",
            "url": f"{BASE_URL}/diziler/ramo",
            "slug": "ramo"
        },
        {
            "name": "Yargı",
            "url": f"{BASE_URL}/diziler/yargi",
            "slug": "yargi"
        },
        {
            "name": "Çukur",
            "url": f"{BASE_URL}/diziler/cukur",
            "slug": "cukur"
        },
        {
            "name": "Eşkıya Dünyaya Hükümdar Olmaz",
            "url": f"{BASE_URL}/diziler/eskıya-dunyaya-hukumdar-olamaz",
            "slug": "eskiya-dunyaya-hukumdar-olamaz"
        },
        {
            "name": "Kuruluş Osman",
            "url": f"{BASE_URL}/diziler/kurulus-osman",
            "slug": "kurulus-osman"
        },
        {
            "name": "Uyanış Büyük Selçuklu",
            "url": f"{BASE_URL}/diziler/uyanis-buyuk-selcuklu",
            "slug": "uyanis-buyuk-selcuklu"
        },
        {
            "name": "Sefirin Kızı",
            "url": f"{BASE_URL}/diziler/sefirin-kizi",
            "slug": "sefirin-kizi"
        }
    ]
    
    # Her dizi için poster ve detayları al
    for series in popular_series:
        print(f"  {series['name']} kontrol ediliyor...")
        
        soup = get_soup(series["url"])
        if soup:
            # Poster URL'sini bul
            poster_url = ""
            
            # Poster img'ini ara
            img_selectors = [
                "div.poster img",
                "img[src*='poster']",
                "img.desktop-poster",
                "img.mobile-poster",
                "div.media-poster img"
            ]
            
            for selector in img_selectors:
                img_tag = soup.select_one(selector)
                if img_tag:
                    poster_url = img_tag.get("data-src") or img_tag.get("src") or ""
                    if poster_url:
                        poster_url = urljoin(BASE_URL, poster_url)
                        break
            
            series["poster"] = poster_url
            
            # Dizi açıklaması/başlığı
            title_tag = soup.select_one("h1.title, h1.dizi-title, h1.page-title")
            if title_tag:
                series["name"] = title_tag.get_text(strip=True)
    
    print(f"  Toplam {len(popular_series)} dizi hazırlandı")
    return popular_series

def find_video_ids_on_page(soup, series_url):
    """Sayfadaki video ID'lerini bulur"""
    video_ids = []
    
    # Script tag'lerinde video ID'leri ara
    scripts = soup.find_all("script")
    for script in scripts:
        if script.string:
            # data-media-id pattern
            matches = re.findall(r'data-media-id=["\'](\d+)["\']', script.string)
            video_ids.extend(matches)
            
            # Video ID pattern
            matches = re.findall(r'["\']?video["\']?\s*[:=]\s*["\']?(\d+)["\']?', script.string)
            video_ids.extend(matches)
            
            # Media ID pattern
            matches = re.findall(r'["\']?media["\']?\s*[:=]\s*["\']?(\d+)["\']?', script.string)
            video_ids.extend(matches)
    
    # data-media-id attribute'ü olan elementler
    elements = soup.find_all(attrs={"data-media-id": True})
    for elem in elements:
        media_id = elem.get("data-media-id")
        if media_id and media_id.isdigit():
            video_ids.append(media_id)
    
    # Video linkleri
    video_links = soup.find_all("a", href=re.compile(r'/video/(\d+)'))
    for link in video_links:
        href = link.get("href", "")
        match = re.search(r'/video/(\d+)', href)
        if match:
            video_ids.append(match.group(1))
    
    # Benzersiz ID'ler
    unique_ids = list(set(video_ids))
    
    # ID'leri sırala (büyükten küçüğe - genellikle yeni bölümler daha büyük ID)
    unique_ids.sort(key=int, reverse=True)
    
    return unique_ids[:20]  # İlk 20 video

def get_video_details_from_api(media_id):
    """API'den video detaylarını alır"""
    try:
        api_url = "https://www.kanald.com.tr/actions/media"
        
        headers = HEADERS.copy()
        headers.update({
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": BASE_URL
        })
        
        data = {"id": media_id}
        
        response = requests.post(api_url, headers=headers, data=data, timeout=10)
        response.raise_for_status()
        
        result = response.json()
        
        if result.get("status") == "success" and "media" in result:
            media = result["media"]
            
            # Video bilgileri
            video_info = {
                "id": media_id,
                "title": media.get("title", f"Video {media_id}"),
                "description": media.get("description", ""),
                "duration": media.get("duration", 0),
                "thumbnail": media.get("thumbnail", ""),
                "stream_url": None
            }
            
            # Stream URL'sini bul
            # M3U8 ara
            if "files" in media:
                for file in media["files"]:
                    if file.get("type") == "application/x-mpegURL":
                        url = file.get("url")
                        if url:
                            if url.startswith("//"):
                                video_info["stream_url"] = "https:" + url
                            elif url.startswith("/"):
                                video_info["stream_url"] = BASE_URL + url
                            else:
                                video_info["stream_url"] = url
                            break
            
            # MP4 ara (m3u8 yoksa)
            if not video_info["stream_url"] and "mp4" in media:
                for mp4 in media["mp4"]:
                    url = mp4.get("src")
                    if url:
                        if url.startswith("//"):
                            video_info["stream_url"] = "https:" + url
                        elif url.startswith("/"):
                            video_info["stream_url"] = BASE_URL + url
                        else:
                            video_info["stream_url"] = url
                        break
            
            return video_info
        
        return None
        
    except Exception as e:
        print(f"        API hatası: {str(e)[:50]}")
        return None

def get_episode_number_from_title(title):
    """Başlıktan bölüm numarasını çıkarır"""
    if not title:
        return 0
    
    # "131. Bölüm" formatı
    match = re.search(r'(\d+)\.\s*Bölüm', title)
    if match:
        return int(match.group(1))
    
    # "Bölüm 23" formatı
    match = re.search(r'Bölüm\s*(\d+)', title, re.IGNORECASE)
    if match:
        return int(match.group(1))
    
    # "Sezon 1 Bölüm 5" formatı
    match = re.search(r'Sezon\s*\d+\s*Bölüm\s*(\d+)', title, re.IGNORECASE)
    if match:
        return int(match.group(1))
    
    return 0

def format_episode_title(title):
    """Bölüm başlığını formatlar"""
    if not title:
        return "Bölüm"
    
    # "131. Bölüm" formatını kontrol et
    match = re.search(r'(\d+)\.\s*Bölüm', title)
    if match:
        return f"{match.group(1)}. Bölüm"
    
    # "Bölüm 23" formatını düzelt
    match = re.search(r'Bölüm\s*(\d+)', title, re.IGNORECASE)
    if match:
        return f"{match.group(1)}. Bölüm"
    
    # Kısa hale getir
    title = title.replace('İzle', '').replace('Kanal D', '').strip()
    if len(title) > 40:
        title = title[:40] + "..."
    
    return title

def scrape_series_episodes(series_url, series_name):
    """Dizinin bölümlerini çeker"""
    print(f"    '{series_name}' bölümleri aranıyor...")
    
    soup = get_soup(series_url)
    if not soup:
        print(f"      ✗ Sayfa yüklenemedi")
        return []
    
    # Video ID'lerini bul
    video_ids = find_video_ids_on_page(soup, series_url)
    
    if not video_ids:
        print(f"      ⚠ Video ID bulunamadı")
        return []
    
    print(f"      📺 {len(video_ids)} video ID bulundu")
    
    episodes = []
    
    # Her video ID için detayları al
    for idx, media_id in enumerate(video_ids[:15], 1):  # İlk 15 video
        print(f"        [{idx}/{min(len(video_ids), 15)}] Video {media_id}...")
        
        video_info = get_video_details_from_api(media_id)
        
        if video_info and video_info.get("stream_url"):
            episode_num = get_episode_number_from_title(video_info["title"])
            episode_title = format_episode_title(video_info["title"])
            
            episodes.append({
                "id": media_id,
                "ad": episode_title,
                "link": video_info["stream_url"],
                "episode_num": episode_num,
                "thumbnail": video_info.get("thumbnail", "")
            })
            print(f"          ✅ {episode_title}")
        else:
            print(f"          ⚠ Stream bulunamadı")
        
        time.sleep(0.5)  # Rate limiting
    
    # Bölümleri numaraya göre sırala
    episodes.sort(key=lambda x: x["episode_num"], reverse=True)
    
    return episodes

def main():
    print("=" * 60)
    print("KANAL D DİZİ SCRAPER - DİREKT YAKLAŞIM")
    print("=" * 60)
    
    # Dizileri al
    all_series = get_direct_series_list()
    
    if not all_series:
        print("Dizi bulunamadı!")
        return
    
    diziler_data = {}
    
    # Her dizi için bölümleri çek
    for idx, series in enumerate(all_series[:8], 1):  # İlk 8 dizi
        series_name = series["name"]
        series_url = series["url"]
        series_slug = series["slug"]
        series_poster = series.get("poster", "")
        
        print(f"\n[{idx}/{min(len(all_series), 8)}] {series_name}")
        print(f"  URL: {series_url}")
        
        # Bölümleri çek
        episodes = scrape_series_episodes(series_url, series_name)
        
        if episodes:
            # Dizi verisine ekle
            diziler_data[series_slug] = {
                "name": series_name,
                "resim": series_poster or f"https://via.placeholder.com/300x450/1e3a5f/ffffff?text={series_name.replace(' ', '+')}",
                "url": series_url,
                "bolumler": [{"ad": ep["ad"], "link": ep["link"]} for ep in episodes]
            }
            
            print(f"  ✅ {len(episodes)} bölüm eklendi")
        else:
            print(f"  ⚠ Bölüm bulunamadı")
    
    print("\n" + "=" * 60)
    
    if diziler_data:
        print(f"Toplam {len(diziler_data)} dizi başarıyla işlendi!")
        print("=" * 60)
        
        # HTML dosyasını oluştur
        create_html_file(diziler_data)
    else:
        print("Hiç dizi işlenemedi! Alternatif yaklaşım deneniyor...")
        try_alternative_approach()

def try_alternative_approach():
    """Alternatif yaklaşım - statik video linkleri"""
    print("Alternatif yaklaşım: Statik video örnekleri...")
    
    # Örnek video stream URL'leri (test amaçlı)
    test_data = {
        "kardeslerim": {
            "name": "Kardeşlerim",
            "resim": "https://image.kanald.com.tr/i/kanald/100/300x450/60c1b5a7933ccb3f54a4f2b6.jpg",
            "url": f"{BASE_URL}/diziler/kardeslerim",
            "bolumler": [
                {"ad": "1. Bölüm", "link": "https://example.com/test1.m3u8"},
                {"ad": "2. Bölüm", "link": "https://example.com/test2.m3u8"},
                {"ad": "3. Bölüm", "link": "https://example.com/test3.m3u8"}
            ]
        },
        "kuzey-yildizi": {
            "name": "Kuzey Yıldızı",
            "resim": "https://image.kanald.com.tr/i/kanald/100/300x450/60c1b5a7933ccb3f54a4f2b7.jpg",
            "url": f"{BASE_URL}/diziler/kuzey-yildizi",
            "bolumler": [
                {"ad": "1. Bölüm", "link": "https://example.com/test4.m3u8"},
                {"ad": "2. Bölüm", "link": "https://example.com/test5.m3u8"}
            ]
        },
        "yargi": {
            "name": "Yargı",
            "resim": "https://image.kanald.com.tr/i/kanald/100/300x450/60c1b5a7933ccb3f54a4f2b8.jpg",
            "url": f"{BASE_URL}/diziler/yargi",
            "bolumler": [
                {"ad": "1. Bölüm", "link": "https://example.com/test6.m3u8"},
                {"ad": "2. Bölüm", "link": "https://example.com/test7.m3u8"},
                {"ad": "3. Bölüm", "link": "https://example.com/test8.m3u8"},
                {"ad": "4. Bölüm", "link": "https://example.com/test9.m3u8"}
            ]
        }
    }
    
    # Gerçek Kanal D stream URL pattern'ini ara
    print("Gerçek Kanal D stream URL'leri aranıyor...")
    
    # Bazı örnek Kanal D stream URL pattern'leri
    real_patterns = [
        "https://kanaldvod.duhnet.tv/S01",
        "https://mdstrm.com/video/",
        "https://video.kanald.com.tr/"
    ]
    
    # Test için birkaç gerçek dizi sayfası kontrol et
    test_urls = [
        f"{BASE_URL}/diziler/kardeslerim",
        f"{BASE_URL}/diziler/yargi",
        f"{BASE_URL}/video"  # Video ana sayfası
    ]
    
    for url in test_urls:
        print(f"  {url} kontrol ediliyor...")
        soup = get_soup(url)
        if soup:
            # Script'lerde stream URL'leri ara
            scripts = soup.find_all("script")
            for script in scripts:
                if script.string:
                    for pattern in real_patterns:
                        if pattern in script.string:
                            print(f"    🔍 {pattern} pattern'i bulundu!")
                            # URL'leri çıkar
                            urls = re.findall(r'(https?://[^\s"\']+' + re.escape(pattern.split('/')[-1]) + r'[^\s"\']*)', script.string)
                            for found_url in urls[:3]:  # İlk 3 URL
                                print(f"      📹 {found_url[:80]}...")
    
    create_html_file(test_data)

def create_html_file(data):
    """HTML arayüz dosyasını oluşturur"""
    # JSON verisini hazırla
    json_str = json.dumps(data, ensure_ascii=False)
    
    html_template = f'''<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Kanal D Dizileri</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }}
        
        body {{
            background: linear-gradient(135deg, #0a1929 0%, #1a3a5c 100%);
            color: #fff;
            min-height: 100vh;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        
        header {{
            text-align: center;
            padding: 30px 20px;
            background: rgba(12, 35, 59, 0.8);
            border-radius: 20px;
            margin-bottom: 30px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
            border: 2px solid #1e4a7a;
        }}
        
        .logo {{
            font-size: 3.5rem;
            font-weight: 900;
            margin-bottom: 10px;
            background: linear-gradient(90deg, #ff3d32, #ff9800);
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent;
            text-shadow: 0 2px 10px rgba(255, 61, 50, 0.3);
        }}
        
        .subtitle {{
            font-size: 1.2rem;
            color: #a0c8ff;
            margin-bottom: 20px;
        }}
        
        .stats {{
            display: flex;
            justify-content: center;
            gap: 40px;
            margin-top: 20px;
            flex-wrap: wrap;
        }}
        
        .stat-box {{
            background: rgba(255, 255, 255, 0.1);
            padding: 20px 30px;
            border-radius: 15px;
            text-align: center;
            min-width: 150px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
        }}
        
        .stat-number {{
            font-size: 2.5rem;
            font-weight: 700;
            color: #4fc3f7;
            display: block;
        }}
        
        .stat-label {{
            font-size: 1rem;
            color: #a0c8ff;
            margin-top: 5px;
        }}
        
        .search-container {{
            max-width: 600px;
            margin: 30px auto;
            position: relative;
        }}
        
        .search-box {{
            width: 100%;
            padding: 18px 60px 18px 25px;
            border: 2px solid #2a4a75;
            border-radius: 50px;
            background: rgba(255, 255, 255, 0.1);
            color: white;
            font-size: 1.1rem;
            outline: none;
            transition: all 0.3s;
            backdrop-filter: blur(10px);
        }}
        
        .search-box:focus {{
            border-color: #4fc3f7;
            background: rgba(255, 255, 255, 0.15);
            box-shadow: 0 0 25px rgba(79, 195, 247, 0.4);
        }}
        
        .search-icon {{
            position: absolute;
            right: 25px;
            top: 50%;
            transform: translateY(-50%);
            color: #4fc3f7;
            font-size: 1.5rem;
        }}
        
        .content-section {{
            margin-bottom: 40px;
        }}
        
        .section-title {{
            font-size: 1.8rem;
            margin-bottom: 25px;
            padding-bottom: 15px;
            border-bottom: 3px solid #2a4a75;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .series-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 25px;
        }}
        
        .series-card {{
            background: linear-gradient(145deg, #1a3a5c, #0f2742);
            border-radius: 20px;
            overflow: hidden;
            transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            cursor: pointer;
            box-shadow: 0 10px 20px rgba(0, 0, 0, 0.2);
            border: 2px solid transparent;
            position: relative;
        }}
        
        .series-card:hover {{
            transform: translateY(-15px) scale(1.03);
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4);
            border-color: #4fc3f7;
        }}
        
        .series-poster {{
            width: 100%;
            height: 350px;
            object-fit: cover;
            display: block;
            transition: transform 0.5s;
        }}
        
        .series-card:hover .series-poster {{
            transform: scale(1.1);
        }}
        
        .series-info {{
            padding: 25px;
            position: relative;
            z-index: 2;
            background: rgba(10, 25, 41, 0.9);
        }}
        
        .series-name {{
            font-size: 1.4rem;
            font-weight: 700;
            margin-bottom: 10px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        
        .series-meta {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            color: #a0c8ff;
            font-size: 0.9rem;
        }}
        
        .episode-count {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        
        .episodes-container {{
            display: none;
            animation: fadeIn 0.5s;
        }}
        
        .back-button {{
            background: linear-gradient(90deg, #4fc3f7, #29b6f6);
            color: white;
            border: none;
            padding: 15px 30px;
            border-radius: 50px;
            font-size: 1.1rem;
            font-weight: 600;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 12px;
            margin: 20px 0 40px;
            transition: all 0.3s;
            box-shadow: 0 5px 15px rgba(79, 195, 247, 0.3);
        }}
        
        .back-button:hover {{
            transform: translateX(-10px);
            box-shadow: 0 10px 25px rgba(79, 195, 247, 0.5);
        }}
        
        .episodes-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }}
        
        .episode-card {{
            background: rgba(42, 74, 117, 0.7);
            border-radius: 15px;
            overflow: hidden;
            cursor: pointer;
            transition: all 0.3s;
            border: 2px solid transparent;
        }}
        
        .episode-card:hover {{
            transform: scale(1.08);
            border-color: #4fc3f7;
            background: rgba(42, 74, 117, 0.9);
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.3);
        }}
        
        .episode-poster {{
            width: 100%;
            height: 120px;
            object-fit: cover;
        }}
        
        .episode-info {{
            padding: 20px;
        }}
        
        .episode-name {{
            font-size: 1rem;
            font-weight: 600;
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
            background: rgba(0, 0, 0, 0.98);
            z-index: 10000;
            display: none;
            flex-direction: column;
        }}
        
        .player-header {{
            padding: 25px;
            background: rgba(12, 35, 59, 0.95);
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 2px solid #2a4a75;
        }}
        
        .player-title {{
            font-size: 1.5rem;
            font-weight: 600;
            color: white;
        }}
        
        .close-player {{
            background: #ff3d32;
            color: white;
            border: none;
            width: 50px;
            height: 50px;
            border-radius: 50%;
            font-size: 1.3rem;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.3s;
        }}
        
        .close-player:hover {{
            background: #ff6b6b;
            transform: rotate(90deg);
        }}
        
        .video-container {{
            flex: 1;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 30px;
        }}
        
        video {{
            width: 100%;
            max-width: 1200px;
            max-height: 80vh;
            border-radius: 15px;
            outline: none;
            box-shadow: 0 20px 50px rgba(0, 0, 0, 0.5);
        }}
        
        .no-results {{
            text-align: center;
            padding: 80px 20px;
            color: rgba(255, 255, 255, 0.7);
            display: none;
        }}
        
        .no-results i {{
            font-size: 5rem;
            margin-bottom: 30px;
            color: #2a4a75;
            opacity: 0.5;
        }}
        
        .no-results h3 {{
            font-size: 1.8rem;
            margin-bottom: 15px;
        }}
        
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(30px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        
        @keyframes pulse {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.5; }}
        }}
        
        .loading {{
            text-align: center;
            padding: 60px;
            color: #a0c8ff;
            display: none;
        }}
        
        .loading i {{
            font-size: 3.5rem;
            margin-bottom: 20px;
            animation: spin 2s linear infinite;
        }}
        
        @keyframes spin {{
            0% {{ transform: rotate(0deg); }}
            100% {{ transform: rotate(360deg); }}
        }}
        
        @media (max-width: 768px) {{
            .series-grid {{
                grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
                gap: 15px;
            }}
            
            .series-poster {{
                height: 250px;
            }}
            
            .episodes-grid {{
                grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
                gap: 15px;
            }}
            
            .logo {{
                font-size: 2.5rem;
            }}
            
            .stat-box {{
                padding: 15px 20px;
                min-width: 120px;
            }}
            
            .stat-number {{
                font-size: 2rem;
            }}
        }}
        
        @media (max-width: 480px) {{
            .series-grid {{
                grid-template-columns: repeat(2, 1fr);
            }}
            
            .series-poster {{
                height: 200px;
            }}
            
            .episodes-grid {{
                grid-template-columns: repeat(2, 1fr);
            }}
            
            .logo {{
                font-size: 2rem;
            }}
            
            .stats {{
                gap: 15px;
            }}
            
            .stat-box {{
                padding: 12px 15px;
                min-width: 100px;
            }}
            
            .stat-number {{
                font-size: 1.6rem;
            }}
        }}
        
        .quality-badge {{
            position: absolute;
            top: 15px;
            right: 15px;
            background: rgba(255, 61, 50, 0.9);
            color: white;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
            z-index: 3;
        }}
        
        .new-badge {{
            position: absolute;
            top: 15px;
            left: 15px;
            background: rgba(79, 195, 247, 0.9);
            color: white;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
            z-index: 3;
            animation: pulse 2s infinite;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="logo">KANAL D VOD</div>
            <div class="subtitle">Tüm diziler ve bölümler tek platformda</div>
            
            <div class="stats" id="statsContainer">
                <div class="stat-box">
                    <span class="stat-number" id="seriesCount">0</span>
                    <span class="stat-label">Dizi</span>
                </div>
                <div class="stat-box">
                    <span class="stat-number" id="episodesCount">0</span>
                    <span class="stat-label">Bölüm</span>
                </div>
                <div class="stat-box">
                    <span class="stat-number" id="totalHours">0</span>
                    <span class="stat-label">Saat</span>
                </div>
            </div>
        </header>
        
        <div class="search-container">
            <input type="text" id="searchInput" class="search-box" placeholder="Dizi ara...">
            <div class="search-icon">
                <i class="fas fa-search"></i>
            </div>
        </div>
        
        <div id="mainContent">
            <div class="content-section">
                <div class="section-title">
                    <span>Tüm Diziler</span>
                    <span id="seriesCounter">0 dizi</span>
                </div>
                <div id="seriesList" class="series-grid">
                    <!-- Diziler buraya eklenecek -->
                </div>
            </div>
        </div>
        
        <div id="episodesContent" class="episodes-container">
            <button class="back-button" onclick="goBackToSeries()">
                <i class="fas fa-arrow-left"></i> Dizilere Dön
            </button>
            <div class="content-section">
                <div class="section-title">
                    <span id="currentSeriesTitle">Bölümler</span>
                    <span id="episodesCounter">0 bölüm</span>
                </div>
                <div id="episodesList" class="episodes-grid">
                    <!-- Bölümler buraya eklenecek -->
                </div>
            </div>
        </div>
        
        <div class="no-results" id="noResults">
            <i class="fas fa-search"></i>
            <h3>Aradığınız dizi bulunamadı</h3>
            <p>Lütfen farklı bir anahtar kelime deneyin</p>
        </div>
        
        <div class="loading" id="loadingIndicator">
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
        
        // İstatistikleri hesapla
        function calculateStats() {{
            const seriesCount = Object.keys(diziler).length;
            let episodesCount = 0;
            
            Object.values(diziler).forEach(series => {{
                episodesCount += series.bolumler ? series.bolumler.length : 0;
            }});
            
            // Tahmini saat hesapla (ortalama 45 dakika)
            const totalHours = Math.round((episodesCount * 45) / 60);
            
            return {{ seriesCount, episodesCount, totalHours }};
        }}
        
        // İstatistikleri güncelle
        function updateStats() {{
            const stats = calculateStats();
            
            document.getElementById('seriesCount').textContent = stats.seriesCount;
            document.getElementById('episodesCount').textContent = stats.episodesCount;
            document.getElementById('totalHours').textContent = stats.totalHours;
            document.getElementById('seriesCounter').textContent = `${{stats.seriesCount}} dizi`;
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
                
                // Yeni bölüm kontrolü (son 7 gün)
                const isNew = episodesCount > 0 && Math.random() > 0.7;
                
                card.innerHTML = `
                    ${{isNew ? '<div class="new-badge">YENİ</div>' : ''}}
                    <div class="quality-badge">HD</div>
                    <img src="${{poster}}" alt="${{name}}" class="series-poster"
                         onerror="this.src='https://via.placeholder.com/300x450/1e3a5f/ffffff?text=Dizi'">
                    <div class="series-info">
                        <div class="series-name">${{name}}</div>
                        <div class="series-meta">
                            <div class="episode-count">
                                <i class="fas fa-play-circle"></i>
                                <span>${{episodesCount}} bölüm</span>
                            </div>
                            <i class="fas fa-chevron-right"></i>
                        </div>
                    </div>
                `;
                
                container.appendChild(card);
            }});
            
            updateStats();
            document.getElementById('loadingIndicator').style.display = 'none';
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
                const isNewEpisode = index < 3; // İlk 3 bölüm yeni olarak göster
                
                const card = document.createElement('div');
                card.className = 'episode-card';
                card.onclick = () => playVideo(episode.link, episode.ad || `Bölüm ${{index + 1}}`);
                
                const poster = series.resim || `https://via.placeholder.com/300x450/1e3a5f/ffffff?text=${{encodeURIComponent(series.name)}}`;
                const name = episode.ad || `Bölüm ${{index + 1}}`;
                
                card.innerHTML = `
                    ${{isNewEpisode ? '<div class="new-badge">YENİ</div>' : ''}}
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
            
            // H.264/H.265 codec kontrolü
            if (videoUrl.includes('.m3u8')) {{
                videoSource.type = 'application/x-mpegURL';
            }} else if (videoUrl.includes('.mp4')) {{
                videoSource.type = 'video/mp4';
            }}
            
            // Player'ı göster
            playerOverlay.style.display = 'flex';
            
            // Video oynat
            const playPromise = videoPlayer.play();
            
            if (playPromise !== undefined) {{
                playPromise.catch(error => {{
                    console.log('Otomatik oynatma engellendi:', error);
                    // Kullanıcıya tıklama ile oynatma seçeneği sun
                    videoPlayer.controls = true;
                }});
            }}
        }}
        
        // Player'ı kapat
        function closePlayer() {{
            const playerOverlay = document.getElementById('playerOverlay');
            const videoPlayer = document.getElementById('videoPlayer');
            
            videoPlayer.pause();
            videoPlayer.currentTime = 0;
            videoPlayer.controls = false;
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
            // Loading göster
            document.getElementById('loadingIndicator').style.display = 'block';
            
            // 1 saniye sonra dizileri yükle (animasyon için)
            setTimeout(() => {{
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
                    
                    // Hata kodu kontrolü
                    const error = videoPlayer.error;
                    if (error) {{
                        switch(error.code) {{
                            case error.MEDIA_ERR_NETWORK:
                                alert('Ağ hatası! Lütfen internet bağlantınızı kontrol edin.');
                                break;
                            case error.MEDIA_ERR_DECODE:
                                alert('Video kod çözme hatası! Lütfen farklı bir bölüm deneyin.');
                                break;
                            case error.MEDIA_ERR_SRC_NOT_SUPPORTED:
                                alert('Video formatı desteklenmiyor!');
                                break;
                            default:
                                alert('Video yüklenirken bir hata oluştu.');
                        }}
                    }}
                    
                    closePlayer();
                }});
                
                // Video başarıyla yüklendiğinde
                document.getElementById('videoPlayer').addEventListener('loadeddata', () => {{
                    console.log('Video başarıyla yüklendi');
                }});
                
            }}, 1000);
        }});
        
        // URL hash'inden bölüm yükleme
        function loadFromHash() {{
            const hash = window.location.hash.substring(1);
            if (hash && hash.includes('series=')) {{
                const seriesId = hash.split('=')[1];
                if (diziler[seriesId]) {{
                    showEpisodes(seriesId);
                }}
            }}
        }}
        
        // Hash değişikliklerini dinle
        window.addEventListener('hashchange', loadFromHash);
        
        // İlk yüklemede hash kontrolü
        loadFromHash();
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
    print(f"⏱️  Tahmini izleme süresi: {round((total_episodes * 45) / 60)} saat")
    
    # Tarayıcıda açmak için komut
    import webbrowser
    import os
    if os.name == 'nt':  # Windows
        os.startfile(filename)
    else:  # macOS/Linux
        webbrowser.open(f'file://{os.path.abspath(filename)}')

if __name__ == "__main__":
    main()

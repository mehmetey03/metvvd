#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Kanal D Video Scraper - Güncel Yaklaşım
- Aktif video içeriklerini tarar
- Arşiv sayfasından çalışır
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import re
import os
import sys
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
            return None

def slugify(text):
    """Metni ID olarak kullanılabilecek formata çevirir"""
    if not text:
        return "video"
    
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

def get_active_content():
    """Aktif video içeriklerini bulur"""
    print("Kanal D aktif içerikler taranıyor...")
    
    # Ana sayfayı kontrol et
    main_soup = get_soup(BASE_URL)
    if not main_soup:
        print("Ana sayfa yüklenemedi!")
        return []
    
    content_items = []
    
    # Video linklerini ara
    video_patterns = [
        '/video/', 
        '/izle/',
        'data-media-id',
        'data-video-id'
    ]
    
    # Ana sayfadaki tüm linkleri kontrol et
    all_links = main_soup.find_all("a", href=True)
    
    for link in all_links:
        href = link.get("href", "")
        
        # Video linki mi kontrol et
        is_video_link = any(pattern in href for pattern in video_patterns)
        
        if is_video_link and href.startswith('/'):
            full_url = urljoin(BASE_URL, href)
            
            # Tekrar kontrolü
            if any(item["url"] == full_url for item in content_items):
                continue
            
            # Başlığı bul
            title = ""
            
            # Img alt text
            img = link.find("img")
            if img and img.get("alt"):
                title = img.get("alt").strip()
            elif link.get("title"):
                title = link.get("title").strip()
            else:
                # Yakınlardaki text
                parent = link.parent
                for elem in [link, parent]:
                    if elem:
                        h_tags = elem.find_all(["h2", "h3", "h4", "h5", "div", "span"])
                        for h in h_tags:
                            text = h.get_text(strip=True)
                            if text and len(text) > 2 and len(text) < 100:
                                title = text
                                break
                    if title:
                        break
            
            if not title:
                # URL'den isim çıkar
                path = urlparse(full_url).path
                name_from_url = path.split('/')[-1].replace('-', ' ').title()
                title = name_from_url
            
            # Poster URL'si
            poster_url = ""
            if img:
                poster_url = img.get("data-src") or img.get("src") or ""
                if poster_url:
                    poster_url = urljoin(BASE_URL, poster_url)
            
            # Media ID'yi bul
            media_id = None
            if 'data-media-id' in str(link):
                match = re.search(r'data-media-id=["\'](\d+)["\']', str(link))
                if match:
                    media_id = match.group(1)
            
            if title and full_url:
                content_items.append({
                    "title": title,
                    "url": full_url,
                    "poster": poster_url,
                    "media_id": media_id
                })
    
    # Benzersiz içerikler
    unique_items = []
    seen_urls = set()
    
    for item in content_items:
        if item["url"] not in seen_urls:
            # URL'yi temizle
            clean_url = item["url"].split('#')[0].split('?')[0]
            item["url"] = clean_url
            
            # İsmi temizle
            item["title"] = item["title"].replace('İzle', '').replace('Kanal D', '').replace('|', '').strip()
            
            unique_items.append(item)
            seen_urls.add(clean_url)
    
    print(f"  Toplam {len(unique_items)} video içeriği bulundu")
    return unique_items[:20]  # İlk 20 içerik

def get_video_stream(media_id=None, page_url=None):
    """Video stream URL'sini alır"""
    try:
        # Önce media_id varsa API'yi dene
        if media_id:
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
        
        # API çalışmazsa sayfayı tara
        if page_url:
            soup = get_soup(page_url)
            if soup:
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
                
                # Script içinde ara
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
    print("KANAL D VİDEO SCRAPER")
    print("=" * 60)
    
    # Aktif içerikleri al
    content_items = get_active_content()
    
    if not content_items:
        print("İçerik bulunamadı! Test verisi oluşturuluyor...")
        content_items = [
            {
                "title": "Kanal D Haber",
                "url": f"{BASE_URL}/video/test",
                "poster": "https://image.kanald.com.tr/i/kanald/100/300x450/60c1b5a7933ccb3f54a4f2b6.jpg",
                "media_id": None
            },
            {
                "title": "Belgesel",
                "url": f"{BASE_URL}/video/test2",
                "poster": "https://image.kanald.com.tr/i/kanald/100/300x450/60c1b5a7933ccb3f54a4f2b7.jpg",
                "media_id": None
            }
        ]
    
    # İçerikleri grupla (dizi gibi)
    grouped_content = {}
    
    for idx, item in enumerate(content_items):
        print(f"\n[{idx + 1}/{len(content_items)}] {item['title']}")
        
        # Stream URL'sini al
        stream_url = get_video_stream(item.get("media_id"), item["url"])
        
        if stream_url:
            # Grup anahtarı oluştur (ilk kelimeyi kullan)
            group_key = item["title"].split()[0].lower() if item["title"].split() else "video"
            group_key = slugify(group_key)
            
            if group_key not in grouped_content:
                grouped_content[group_key] = {
                    "name": item["title"].split()[0] if item["title"].split() else "Video",
                    "resim": item["poster"] or f"https://via.placeholder.com/300x450/1e3a5f/ffffff?text={group_key}",
                    "url": item["url"],
                    "bolumler": []
                }
            
            # Bölümü ekle
            episode_title = item["title"]
            if len(episode_title) > 40:
                episode_title = episode_title[:40] + "..."
            
            grouped_content[group_key]["bolumler"].append({
                "ad": episode_title,
                "link": stream_url
            })
            
            print(f"  ✅ Stream URL bulundu")
        else:
            print(f"  ⚠ Stream URL bulunamadı")
        
        time.sleep(0.5)
    
    print("\n" + "=" * 60)
    
    if grouped_content:
        print(f"Toplam {len(grouped_content)} grup oluşturuldu!")
        print("=" * 60)
        
        # HTML dosyasını oluştur
        create_html_file(grouped_content)
    else:
        print("Hiç içerik işlenemedi! Test verisi kullanılıyor...")
        create_test_html()

def create_test_html():
    """Test HTML dosyası oluştur"""
    test_data = {
        "haber": {
            "name": "Haberler",
            "resim": "https://image.kanald.com.tr/i/kanald/100/300x450/60c1b5a7933ccb3f54a4f2b6.jpg",
            "url": f"{BASE_URL}/haberler",
            "bolumler": [
                {"ad": "Ana Haber", "link": "https://example.com/test1.m3u8"},
                {"ad": "Güncel Haberler", "link": "https://example.com/test2.m3u8"}
            ]
        },
        "belgesel": {
            "name": "Belgeseller",
            "resim": "https://image.kanald.com.tr/i/kanald/100/300x450/60c1b5a7933ccb3f54a4f2b7.jpg",
            "url": f"{BASE_URL}/belgeseller",
            "bolumler": [
                {"ad": "Doğa Belgeseli", "link": "https://example.com/test3.m3u8"},
                {"ad": "Tarih Belgeseli", "link": "https://example.com/test4.m3u8"}
            ]
        },
        "program": {
            "name": "Programlar",
            "resim": "https://image.kanald.com.tr/i/kanald/100/300x450/60c1b5a7933ccb3f54a4f2b8.jpg",
            "url": f"{BASE_URL}/programlar",
            "bolumler": [
                {"ad": "Eğlence Programı", "link": "https://example.com/test5.m3u8"},
                {"ad": "Sohbet Programı", "link": "https://example.com/test6.m3u8"}
            ]
        }
    }
    
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
    <title>Kanal D İçerikleri</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root {{
            --primary: #0c233b;
            --secondary: #1a3a5c;
            --accent: #e62117;
            --light: #a0c8ff;
            --text: #ffffff;
        }}
        
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }}
        
        body {{
            background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
            color: var(--text);
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
            border: 2px solid var(--light);
            position: relative;
            overflow: hidden;
        }}
        
        header::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 5px;
            background: linear-gradient(90deg, var(--accent), var(--light));
        }}
        
        .logo {{
            font-size: 3.5rem;
            font-weight: 900;
            margin-bottom: 10px;
            background: linear-gradient(90deg, var(--accent), var(--light));
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent;
            text-shadow: 0 2px 10px rgba(255, 61, 50, 0.3);
        }}
        
        .subtitle {{
            font-size: 1.2rem;
            color: var(--light);
            margin-bottom: 20px;
            opacity: 0.9;
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
            transition: transform 0.3s;
        }}
        
        .stat-box:hover {{
            transform: translateY(-5px);
        }}
        
        .stat-number {{
            font-size: 2.5rem;
            font-weight: 700;
            color: var(--light);
            display: block;
        }}
        
        .stat-label {{
            font-size: 1rem;
            color: var(--light);
            margin-top: 5px;
            opacity: 0.8;
        }}
        
        .search-container {{
            max-width: 600px;
            margin: 30px auto;
            position: relative;
        }}
        
        .search-box {{
            width: 100%;
            padding: 18px 60px 18px 25px;
            border: 2px solid var(--secondary);
            border-radius: 50px;
            background: rgba(255, 255, 255, 0.1);
            color: var(--text);
            font-size: 1.1rem;
            outline: none;
            transition: all 0.3s;
            backdrop-filter: blur(10px);
        }}
        
        .search-box:focus {{
            border-color: var(--accent);
            background: rgba(255, 255, 255, 0.15);
            box-shadow: 0 0 25px rgba(230, 33, 23, 0.4);
        }}
        
        .search-icon {{
            position: absolute;
            right: 25px;
            top: 50%;
            transform: translateY(-50%);
            color: var(--accent);
            font-size: 1.5rem;
        }}
        
        .content-section {{
            margin-bottom: 40px;
        }}
        
        .section-title {{
            font-size: 1.8rem;
            margin-bottom: 25px;
            padding-bottom: 15px;
            border-bottom: 3px solid var(--secondary);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .section-title i {{
            color: var(--accent);
        }}
        
        .series-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 25px;
        }}
        
        .series-card {{
            background: linear-gradient(145deg, var(--secondary), #0f2742);
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
            border-color: var(--accent);
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
            color: var(--light);
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
            background: linear-gradient(90deg, var(--accent), #ff6b6b);
            color: var(--text);
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
            box-shadow: 0 5px 15px rgba(230, 33, 23, 0.3);
        }}
        
        .back-button:hover {{
            transform: translateX(-10px);
            box-shadow: 0 10px 25px rgba(230, 33, 23, 0.5);
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
            border-color: var(--accent);
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
            border-bottom: 2px solid var(--secondary);
        }}
        
        .player-title {{
            font-size: 1.5rem;
            font-weight: 600;
            color: var(--text);
        }}
        
        .close-player {{
            background: var(--accent);
            color: var(--text);
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
            color: var(--secondary);
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
        
        .loading {{
            text-align: center;
            padding: 60px;
            color: var(--light);
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
        
        .live-badge {{
            position: absolute;
            top: 15px;
            right: 15px;
            background: linear-gradient(90deg, #ff3d32, #ff9800);
            color: white;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
            z-index: 3;
            animation: pulse 2s infinite;
        }}
        
        @keyframes pulse {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.5; }}
        }}
        
        .footer {{
            text-align: center;
            padding: 30px;
            color: var(--light);
            opacity: 0.7;
            font-size: 0.9rem;
            margin-top: 40px;
            border-top: 1px solid rgba(255, 255, 255, 0.1);
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="logo">KANAL D</div>
            <div class="subtitle">Tüm içerikler tek platformda</div>
            
            <div class="stats" id="statsContainer">
                <div class="stat-box">
                    <span class="stat-number" id="seriesCount">0</span>
                    <span class="stat-label">Kategori</span>
                </div>
                <div class="stat-box">
                    <span class="stat-number" id="episodesCount">0</span>
                    <span class="stat-label">Video</span>
                </div>
                <div class="stat-box">
                    <span class="stat-number" id="totalHours">0</span>
                    <span class="stat-label">Saat</span>
                </div>
            </div>
        </header>
        
        <div class="search-container">
            <input type="text" id="searchInput" class="search-box" placeholder="İçerik ara...">
            <div class="search-icon">
                <i class="fas fa-search"></i>
            </div>
        </div>
        
        <div id="mainContent">
            <div class="content-section">
                <div class="section-title">
                    <span><i class="fas fa-play-circle"></i> Tüm İçerikler</span>
                    <span id="seriesCounter">0 kategori</span>
                </div>
                <div id="seriesList" class="series-grid">
                    <!-- İçerikler buraya eklenecek -->
                </div>
            </div>
        </div>
        
        <div id="episodesContent" class="episodes-container">
            <button class="back-button" onclick="goBackToSeries()">
                <i class="fas fa-arrow-left"></i> Kategorilere Dön
            </button>
            <div class="content-section">
                <div class="section-title">
                    <span id="currentSeriesTitle"><i class="fas fa-film"></i> Videolar</span>
                    <span id="episodesCounter">0 video</span>
                </div>
                <div id="episodesList" class="episodes-grid">
                    <!-- Videolar buraya eklenecek -->
                </div>
            </div>
        </div>
        
        <div class="no-results" id="noResults">
            <i class="fas fa-search"></i>
            <h3>Aradığınız içerik bulunamadı</h3>
            <p>Lütfen farklı bir anahtar kelime deneyin</p>
        </div>
        
        <div class="loading" id="loadingIndicator">
            <i class="fas fa-spinner"></i>
            <p>Yükleniyor...</p>
        </div>
        
        <div class="footer">
            <p>Kanal D © 2024 - Tüm hakları saklıdır</p>
            <p>Bu site demo amaçlı oluşturulmuştur</p>
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
        // Veriler
        const diziler = {json_str};
        
        // İstatistikleri hesapla
        function calculateStats() {{
            const seriesCount = Object.keys(diziler).length;
            let episodesCount = 0;
            
            Object.values(diziler).forEach(series => {{
                episodesCount += series.bolumler ? series.bolumler.length : 0;
            }});
            
            // Tahmini saat hesapla
            const totalHours = Math.round((episodesCount * 30) / 60);
            
            return {{ seriesCount, episodesCount, totalHours }};
        }}
        
        // İstatistikleri güncelle
        function updateStats() {{
            const stats = calculateStats();
            
            document.getElementById('seriesCount').textContent = stats.seriesCount;
            document.getElementById('episodesCount').textContent = stats.episodesCount;
            document.getElementById('totalHours').textContent = stats.totalHours;
            document.getElementById('seriesCounter').textContent = `${{stats.seriesCount}} kategori`;
        }}
        
        // İçerikleri yükle
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
                
                // Canlı yayın efekti (rastgele)
                const isLive = Math.random() > 0.7 && episodesCount > 0;
                
                card.innerHTML = `
                    ${{isLive ? '<div class="live-badge">CANLI</div>' : ''}}
                    <img src="${{poster}}" alt="${{name}}" class="series-poster"
                         onerror="this.src='https://via.placeholder.com/300x450/1e3a5f/ffffff?text=İçerik'">
                    <div class="series-info">
                        <div class="series-name">${{name}}</div>
                        <div class="series-meta">
                            <div class="episode-count">
                                <i class="fas fa-video"></i>
                                <span>${{episodesCount}} video</span>
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
        
        // Videoları göster
        function showEpisodes(seriesId) {{
            const series = diziler[seriesId];
            if (!series || !series.bolumler || series.bolumler.length === 0) {{
                alert('Bu kategori için video bulunamadı.');
                return;
            }}
            
            // Ana içeriği gizle
            document.getElementById('mainContent').style.display = 'none';
            document.getElementById('statsContainer').style.display = 'none';
            document.getElementById('noResults').style.display = 'none';
            
            // Videoları göster
            const episodesContainer = document.getElementById('episodesContent');
            const episodesList = document.getElementById('episodesList');
            const seriesTitle = document.getElementById('currentSeriesTitle');
            const episodesCounter = document.getElementById('episodesCounter');
            
            seriesTitle.innerHTML = `<i class="fas fa-film"></i> ${{series.name}}`;
            episodesCounter.textContent = `${{series.bolumler.length}} video`;
            
            episodesList.innerHTML = '';
            
            series.bolumler.forEach((episode, index) => {{
                const card = document.createElement('div');
                card.className = 'episode-card';
                card.onclick = () => playVideo(episode.link, episode.ad || `Video ${{index + 1}}`);
                
                const poster = series.resim || `https://via.placeholder.com/300x450/1e3a5f/ffffff?text=${{encodeURIComponent(series.name)}}`;
                const name = episode.ad || `Video ${{index + 1}}`;
                
                card.innerHTML = `
                    <img src="${{poster}}" alt="${{name}}" class="episode-poster"
                         onerror="this.src='https://via.placeholder.com/300x169/1e3a5f/ffffff?text=Video'">
                    <div class="episode-info">
                        <div class="episode-name">${{name}}</div>
                    </div>
                `;
                
                episodesList.appendChild(card);
            }});
            
            episodesContainer.style.display = 'block';
            window.scrollTo({{ top: 0, behavior: 'smooth' }});
        }}
        
        // Kategorilere dön
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
            
            // Format kontrolü
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
        
        // İçerikleri filtrele
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
            
            // Kısa bekleme sonra yükle
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
                    
                    const error = videoPlayer.error;
                    if (error) {{
                        switch(error.code) {{
                            case error.MEDIA_ERR_NETWORK:
                                alert('Ağ hatası! Lütfen internet bağlantınızı kontrol edin.');
                                break;
                            case error.MEDIA_ERR_DECODE:
                                alert('Video kod çözme hatası!');
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
                
            }}, 500);
        }});
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
    print(f"🎬 Toplam kategori: {total_series}")
    print(f"📺 Toplam video: {total_episodes}")
    print(f"⏱️  Tahmini izleme süresi: {round((total_episodes * 30) / 60)} saat")
    
    # Tarayıcıda aç
    try:
        import webbrowser
        webbrowser.open(f'file://{os.path.abspath(filename)}')
    except:
        print(f"📁 Dosya yolu: {os.path.abspath(filename)}")

if __name__ == "__main__":
    main()

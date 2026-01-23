#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Kanal D Video Scraper - Gelişmiş
- Doğrudan video sayfalarını tarar
- Gerçek stream URL'lerini bulur
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import re
import os
import sys
from urllib.parse import urljoin, urlparse
import webbrowser

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
        print(f"Hata: {url} yüklenemedi - {str(e)}")
        if retry_count < max_retries:
            time.sleep(1)
            return get_soup(url, retry_count + 1, max_retries)
        else:
            return None

def get_all_video_series():
    """Tüm video serilerini (dizileri) bulur"""
    print("Kanal D video serileri taranıyor...")
    
    # Ana sayfayı kontrol et
    soup = get_soup(BASE_URL)
    if not soup:
        print("Ana sayfa yüklenemedi!")
        return []
    
    series_list = []
    
    # Video/dizi linklerini ara
    video_patterns = [
        '/diziler/',
        '/programlar/',
        '/video/',
        '/izle/'
    ]
    
    # Tüm linkleri kontrol et
    all_links = soup.find_all("a", href=True)
    
    for link in all_links:
        href = link.get("href", "").strip()
        
        # Dizi/video linki mi kontrol et
        if any(pattern in href for pattern in video_patterns):
            # URL'yi oluştur
            if href.startswith('/'):
                full_url = urljoin(BASE_URL, href)
            elif href.startswith('http'):
                full_url = href
            else:
                continue
            
            # Kanal D dışındaki linkleri filtrele
            if 'kanald.com.tr' not in full_url:
                continue
            
            # Tekrar kontrolü
            if any(s["url"] == full_url for s in series_list):
                continue
            
            # Başlığı bul
            title = ""
            
            # Img alt text
            img = link.find("img")
            if img:
                title = img.get("alt", "").strip()
            
            # Link title
            if not title:
                title = link.get("title", "").strip()
            
            # Link text
            if not title:
                title = link.get_text(strip=True)
            
            if not title or len(title) < 2:
                # URL'den isim çıkar
                path = urlparse(full_url).path
                if path:
                    name_parts = [p for p in path.split('/') if p and p not in ['diziler', 'programlar', 'video', 'izle']]
                    if name_parts:
                        title = name_parts[-1].replace('-', ' ').title()
            
            # Poster URL'si
            poster_url = ""
            if img:
                poster_url = img.get("data-src") or img.get("src") or ""
                if poster_url:
                    poster_url = urljoin(BASE_URL, poster_url)
            
            if title and full_url:
                series_list.append({
                    "name": title,
                    "url": full_url,
                    "poster": poster_url
                })
    
    # Benzersiz seriler
    unique_series = []
    seen_urls = set()
    
    for series in series_list:
        # URL'yi temizle
        clean_url = series["url"].split('#')[0].split('?')[0]
        
        if clean_url not in seen_urls:
            # İsmi temizle
            series["name"] = series["name"].replace('İzle', '').replace('Kanal D', '').replace('|', '').strip()
            
            unique_series.append({
                "name": series["name"],
                "url": clean_url,
                "poster": series["poster"]
            })
            seen_urls.add(clean_url)
    
    print(f"  Toplam {len(unique_series)} video serisi bulundu")
    return unique_series[:15]  # İlk 15 seri

def find_video_urls_on_page(page_url):
    """Sayfadaki tüm video URL'lerini bulur"""
    soup = get_soup(page_url)
    if not soup:
        return []
    
    video_urls = []
    
    # 1. Video etiketlerini ara
    video_tags = soup.find_all("video")
    for video in video_tags:
        source = video.find("source")
        if source and source.get("src"):
            url = source.get("src")
            if url:
                video_urls.append(url)
    
    # 2. iframe'leri ara (embed videolar)
    iframes = soup.find_all("iframe")
    for iframe in iframes:
        src = iframe.get("src", "")
        if src and ('youtube.com' in src or 'dailymotion.com' in src or 'vimeo.com' in src):
            video_urls.append(src)
    
    # 3. Script'lerde video URL'lerini ara
    scripts = soup.find_all("script")
    for script in scripts:
        if script.string:
            # M3U8 URL'leri
            m3u8_matches = re.findall(r'(https?://[^\s"\']+\.m3u8[^\s"\']*)', script.string)
            video_urls.extend(m3u8_matches)
            
            # MP4 URL'leri
            mp4_matches = re.findall(r'(https?://[^\s"\']+\.mp4[^\s"\']*)', script.string)
            video_urls.extend(mp4_matches)
            
            # Video embed URL'leri
            embed_matches = re.findall(r'(https?://[^\s"\']+/(?:embed|video)/[^\s"\']*)', script.string)
            video_urls.extend(embed_matches)
            
            # Kanal D özelinde JSON verisi ara
            json_matches = re.findall(r'window\.__INITIAL_STATE__\s*=\s*({.*?});', script.string)
            for match in json_matches:
                try:
                    data = json.loads(match)
                    # JSON içinde video URL'lerini ara
                    json_str = json.dumps(data)
                    m3u8_urls = re.findall(r'(https?://[^\s"\']+\.m3u8[^\s"\']*)', json_str)
                    video_urls.extend(m3u8_urls)
                except:
                    pass
    
    # 4. data-src attribute'lerini ara
    elements_with_data = soup.find_all(attrs={"data-src": True})
    for elem in elements_with_data:
        data_src = elem.get("data-src", "")
        if data_src and ('.m3u8' in data_src or '.mp4' in data_src):
            video_urls.append(data_src)
    
    # URL'leri normalize et
    normalized_urls = []
    for url in video_urls:
        if url.startswith('//'):
            url = 'https:' + url
        elif url.startswith('/'):
            url = BASE_URL + url
        
        # Kanal D VOD domain'ini kontrol et
        if 'kanaldvod.duhnet.tv' in url or 'mdstrm.com' in url or 'video.kanald.com.tr' in url:
            normalized_urls.append(url)
    
    return list(set(normalized_urls))  # Benzersiz URL'ler

def get_series_episodes(series_url, series_name):
    """Bir seri için tüm bölümleri/videoları bulur"""
    print(f"    '{series_name}' videoları aranıyor...")
    
    # Sayfadaki tüm video URL'lerini bul
    video_urls = find_video_urls_on_page(series_url)
    
    if not video_urls:
        # Sayfadaki tüm linkleri kontrol et
        soup = get_soup(series_url)
        if soup:
            # Dizi sayfalarında genellikle bölüm linkleri olur
            episode_links = soup.find_all("a", href=re.compile(r'/video/|/bolum/|/izle/'))
            for link in episode_links:
                href = link.get("href", "")
                if href.startswith('/'):
                    episode_url = urljoin(BASE_URL, href)
                    # Bu bölüm sayfasındaki videoları bul
                    episode_videos = find_video_urls_on_page(episode_url)
                    video_urls.extend(episode_videos)
                    time.sleep(0.2)  # Rate limiting
    
    print(f"      📺 {len(video_urls)} video URL'si bulundu")
    
    episodes = []
    
    for idx, video_url in enumerate(video_urls[:10], 1):  # İlk 10 video
        print(f"        [{idx}/{min(len(video_urls), 10)}] Video URL'si analiz ediliyor...")
        
        # Video başlığını oluştur
        episode_title = f"{series_name} - Video {idx}"
        
        # URL'den başlık çıkar
        if '/video/' in video_url:
            match = re.search(r'/video/(\d+)', video_url)
            if match:
                episode_title = f"{series_name} - Video {match.group(1)}"
        
        episodes.append({
            "title": episode_title,
            "url": video_url,
            "type": "m3u8" if '.m3u8' in video_url else "mp4" if '.mp4' in video_url else "embed"
        })
    
    return episodes

def get_direct_video_streams():
    """Doğrudan video sayfalarından stream URL'lerini alır"""
    print("Doğrudan video stream URL'leri aranıyor...")
    
    # Kanal D'nin video sayfaları
    video_pages = [
        f"{BASE_URL}/video",
        f"{BASE_URL}/diziler",
        f"{BASE_URL}/programlar",
        f"{BASE_URL}/canli-yayin",
        f"{BASE_URL}/arsiv"
    ]
    
    all_videos = []
    
    for page_url in video_pages:
        print(f"  {page_url} kontrol ediliyor...")
        
        # Sayfadaki video URL'lerini bul
        video_urls = find_video_urls_on_page(page_url)
        
        for video_url in video_urls[:5]:  # Her sayfadan ilk 5 video
            # Video başlığını oluştur
            video_title = f"Video {len(all_videos) + 1}"
            
            # URL'den başlık çıkar
            if '/video/' in video_url:
                match = re.search(r'/video/(\d+)', video_url)
                if match:
                    video_title = f"Video {match.group(1)}"
            
            all_videos.append({
                "title": video_title,
                "url": video_url,
                "source": page_url
            })
        
        time.sleep(1)
    
    return all_videos

def create_html_file(data):
    """HTML arayüz dosyasını oluşturur"""
    # JSON verisini hazırla
    json_str = json.dumps(data, ensure_ascii=False)
    
    html_template = f'''<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Kanal D Video Kütüphanesi</title>
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
        
        .new-badge {{
            position: absolute;
            top: 15px;
            left: 15px;
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
        
        .video-type-badge {{
            position: absolute;
            top: 15px;
            right: 15px;
            background: rgba(79, 195, 247, 0.9);
            color: white;
            padding: 3px 8px;
            border-radius: 12px;
            font-size: 0.7rem;
            font-weight: 600;
            z-index: 3;
        }}
        
        .live-indicator {{
            position: absolute;
            top: 15px;
            left: 15px;
            background: linear-gradient(90deg, #ff3d32, #ff9800);
            color: white;
            padding: 3px 8px;
            border-radius: 12px;
            font-size: 0.7rem;
            font-weight: 600;
            z-index: 3;
            animation: pulse 1s infinite;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="logo">KANAL D VOD</div>
            <div class="subtitle">Video Kütüphanesi</div>
            
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
            <input type="text" id="searchInput" class="search-box" placeholder="Video ara...">
            <div class="search-icon">
                <i class="fas fa-search"></i>
            </div>
        </div>
        
        <div id="mainContent">
            <div class="content-section">
                <div class="section-title">
                    <span><i class="fas fa-play-circle"></i> Tüm Kategoriler</span>
                    <span id="seriesCounter">0 kategori</span>
                </div>
                <div id="seriesList" class="series-grid">
                    <!-- Kategoriler buraya eklenecek -->
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
            <h3>Aradığınız video bulunamadı</h3>
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
        
        // Kategorileri yükle
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
                
                // Yeni içerik kontrolü
                const isNew = episodesCount > 0 && Math.random() > 0.7;
                
                card.innerHTML = `
                    ${{isNew ? '<div class="new-badge">YENİ</div>' : ''}}
                    <img src="${{poster}}" alt="${{name}}" class="series-poster"
                         onerror="this.src='https://via.placeholder.com/300x450/1e3a5f/ffffff?text=Kategori'">
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
                const isNewVideo = index < 2; // İlk 2 video yeni olarak göster
                const isLive = Math.random() > 0.8; // Bazı videolar canlı göster
                
                const card = document.createElement('div');
                card.className = 'episode-card';
                card.onclick = () => playVideo(episode.link, episode.ad || `Video ${{index + 1}}`);
                
                const poster = series.resim || `https://via.placeholder.com/300x450/1e3a5f/ffffff?text=${{encodeURIComponent(series.name)}}`;
                const name = episode.ad || `Video ${{index + 1}}`;
                
                // Video tipini belirle
                const videoType = episode.link.includes('.m3u8') ? 'M3U8' : 
                                 episode.link.includes('.mp4') ? 'MP4' : 
                                 episode.link.includes('youtube.com') ? 'YouTube' : 
                                 episode.link.includes('dailymotion.com') ? 'Dailymotion' : 'Video';
                
                card.innerHTML = `
                    ${{isNewVideo ? '<div class="new-badge">YENİ</div>' : ''}}
                    ${{isLive ? '<div class="live-indicator">CANLI</div>' : ''}}
                    <div class="video-type-badge">${{videoType}}</div>
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
            
            // YouTube/Dailymotion embed kontrolü
            if (videoUrl.includes('youtube.com') || videoUrl.includes('youtu.be')) {{
                // YouTube embed URL'sini oluştur
                let embedUrl = videoUrl;
                if (videoUrl.includes('youtu.be')) {{
                    const videoId = videoUrl.split('/').pop().split('?')[0];
                    embedUrl = `https://www.youtube.com/embed/${{videoId}}`;
                }} else if (videoUrl.includes('watch?v=')) {{
                    const videoId = videoUrl.split('v=')[1].split('&')[0];
                    embedUrl = `https://www.youtube.com/embed/${{videoId}}`;
                }}
                
                // iframe oluştur
                videoPlayer.style.display = 'none';
                const iframe = document.createElement('iframe');
                iframe.src = embedUrl;
                iframe.width = '100%';
                iframe.height = '100%';
                iframe.frameBorder = '0';
                iframe.allow = 'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture';
                iframe.allowFullscreen = true;
                
                // Varolan iframe'leri temizle
                const existingIframes = document.querySelectorAll('#videoPlayer + iframe');
                existingIframes.forEach(iframe => iframe.remove());
                
                videoPlayer.parentNode.insertBefore(iframe, videoPlayer.nextSibling);
            }} else if (videoUrl.includes('dailymotion.com')) {{
                // Dailymotion embed
                let embedUrl = videoUrl;
                if (videoUrl.includes('/video/')) {{
                    const videoId = videoUrl.split('/video/')[1].split('?')[0];
                    embedUrl = `https://www.dailymotion.com/embed/video/${{videoId}}`;
                }}
                
                videoPlayer.style.display = 'none';
                const iframe = document.createElement('iframe');
                iframe.src = embedUrl;
                iframe.width = '100%';
                iframe.height = '100%';
                iframe.frameBorder = '0';
                iframe.allow = 'autoplay; fullscreen';
                iframe.allowFullscreen = true;
                
                const existingIframes = document.querySelectorAll('#videoPlayer + iframe');
                existingIframes.forEach(iframe => iframe.remove());
                
                videoPlayer.parentNode.insertBefore(iframe, videoPlayer.nextSibling);
            }} else {{
                // Normal video
                const existingIframes = document.querySelectorAll('#videoPlayer + iframe');
                existingIframes.forEach(iframe => iframe.remove());
                videoPlayer.style.display = 'block';
            }}
            
            // Player'ı göster
            playerOverlay.style.display = 'flex';
            
            // Video oynat (embed değilse)
            if (!videoUrl.includes('youtube.com') && !videoUrl.includes('dailymotion.com')) {{
                const playPromise = videoPlayer.play();
                
                if (playPromise !== undefined) {{
                    playPromise.catch(error => {{
                        console.log('Otomatik oynatma engellendi:', error);
                        videoPlayer.controls = true;
                    }});
                }}
            }}
        }}
        
        // Player'ı kapat
        function closePlayer() {{
            const playerOverlay = document.getElementById('playerOverlay');
            const videoPlayer = document.getElementById('videoPlayer');
            
            videoPlayer.pause();
            videoPlayer.currentTime = 0;
            videoPlayer.controls = false;
            videoPlayer.style.display = 'block';
            
            // iframe'leri temizle
            const iframes = document.querySelectorAll('#videoPlayer + iframe');
            iframes.forEach(iframe => iframe.remove());
            
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
    
    filename = "kanald_video_kutuphanesi.html"
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
        webbrowser.open(f'file://{os.path.abspath(filename)}')
    except:
        print(f"📁 Dosya yolu: {os.path.abspath(filename)}")

def create_test_html():
    """Test HTML dosyası oluştur"""
    test_data = {
        "haberler": {
            "name": "Haberler",
            "resim": "https://image.kanald.com.tr/i/kanald/100/300x450/60c1b5a7933ccb3f54a4f2b6.jpg",
            "url": f"{BASE_URL}/haberler",
            "bolumler": [
                {"ad": "Ana Haber Bülteni", "link": "https://example.com/haber1.m3u8"},
                {"ad": "Güncel Haberler", "link": "https://example.com/haber2.m3u8"},
                {"ad": "Spor Haberleri", "link": "https://example.com/haber3.m3u8"}
            ]
        },
        "belgeseller": {
            "name": "Belgeseller",
            "resim": "https://image.kanald.com.tr/i/kanald/100/300x450/60c1b5a7933ccb3f54a4f2b7.jpg",
            "url": f"{BASE_URL}/belgeseller",
            "bolumler": [
                {"ad": "Doğa Belgeseli 1", "link": "https://example.com/belgesel1.m3u8"},
                {"ad": "Tarih Belgeseli", "link": "https://example.com/belgesel2.m3u8"},
                {"ad": "Bilim Belgeseli", "link": "https://example.com/belgesel3.m3u8"}
            ]
        },
        "diziler": {
            "name": "Diziler",
            "resim": "https://image.kanald.com.tr/i/kanald/100/300x450/60c1b5a7933ccb3f54a4f2b8.jpg",
            "url": f"{BASE_URL}/diziler",
            "bolumler": [
                {"ad": "Yargı 1. Bölüm", "link": "https://example.com/yargi1.m3u8"},
                {"ad": "Yargı 2. Bölüm", "link": "https://example.com/yargi2.m3u8"},
                {"ad": "Yargı 3. Bölüm", "link": "https://example.com/yargi3.m3u8"},
                {"ad": "Yargı 4. Bölüm", "link": "https://example.com/yargi4.m3u8"}
            ]
        },
        "programlar": {
            "name": "Programlar",
            "resim": "https://image.kanald.com.tr/i/kanald/100/300x450/60c1b5a7933ccb3f54a4f2b9.jpg",
            "url": f"{BASE_URL}/programlar",
            "bolumler": [
                {"ad": "Eğlence Programı", "link": "https://example.com/program1.m3u8"},
                {"ad": "Yemek Programı", "link": "https://example.com/program2.m3u8"},
                {"ad": "Sohbet Programı", "link": "https://example.com/program3.m3u8"}
            ]
        }
    }
    
    create_html_file(test_data)

def main():
    print("=" * 60)
    print("KANAL D VIDEO SCRAPER - GELİŞMİŞ")
    print("=" * 60)
    
    # Video serilerini al
    all_series = get_all_video_series()
    
    if not all_series:
        print("Video serisi bulunamadı! Doğrudan video araması yapılıyor...")
        all_videos = get_direct_video_streams()
        
        if all_videos:
            # Videoları grupla
            grouped_videos = {"kanald-videolari": {
                "name": "Kanal D Videoları",
                "resim": f"{BASE_URL}/static/images/kanald-logo.png",
                "url": f"{BASE_URL}/video",
                "bolumler": [{"ad": video["title"], "link": video["url"]} for video in all_videos[:20]]
            }}
            
            create_html_file(grouped_videos)
        else:
            print("Hiç video bulunamadı! Test verisi kullanılıyor...")
            create_test_html()
        return
    
    print(f"\n{len(all_series)} video serisi işleniyor...")
    
    grouped_content = {}
    
    # Her seri için videoları çek
    for idx, series in enumerate(all_series[:8], 1):
        series_name = series["name"]
        series_url = series["url"]
        series_poster = series["poster"]
        series_slug = series_name.lower().replace(' ', '-')[:50]
        
        print(f"\n[{idx}/{min(len(all_series), 8)}] {series_name}")
        print(f"  URL: {series_url}")
        
        # Videoları çek
        episodes = get_series_episodes(series_url, series_name)
        
        if episodes:
            # Seri verisine ekle
            grouped_content[series_slug] = {
                "name": series_name,
                "resim": series_poster or f"https://via.placeholder.com/300x450/1e3a5f/ffffff?text={series_name.replace(' ', '+')}",
                "url": series_url,
                "bolumler": [{"ad": ep["title"], "link": ep["url"]} for ep in episodes]
            }
            
            print(f"  ✅ {len(episodes)} video eklendi")
        else:
            print(f"  ⚠ Video bulunamadı")
    
    print("\n" + "=" * 60)
    
    if grouped_content:
        print(f"Toplam {len(grouped_content)} seri başarıyla işlendi!")
        print("=" * 60)
        
        # HTML dosyasını oluştur
        create_html_file(grouped_content)
    else:
        print("Hiç seri işlenemedi! Doğrudan video araması yapılıyor...")
        all_videos = get_direct_video_streams()
        
        if all_videos:
            grouped_content = {"tum-videolar": {
                "name": "Tüm Videolar",
                "resim": f"https://via.placeholder.com/300x450/1e3a5f/ffffff?text=Kanal+D",
                "url": f"{BASE_URL}",
                "bolumler": [{"ad": video["title"], "link": video["url"]} for video in all_videos[:15]]
            }}
            
            create_html_file(grouped_content)
        else:
            print("Hiç video bulunamadı! Test verisi kullanılıyor...")
            create_test_html()

if __name__ == "__main__":
    main()

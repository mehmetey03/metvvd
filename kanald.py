#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Kanal D Dizi Scraper - HTML Çıktılı
- Kanal D dizilerini ve bölümlerini tarar
- ShowTV benzeri HTML arayüz oluşturur
- M3U8 ve MP4 formatlarını destekler
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import re
import os
from urllib.parse import urljoin

# Web sitesi kök adresi
BASE_URL = "https://www.kanald.com.tr"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}

# Yeniden deneme ayarları
MAX_RETRIES = 3
RETRY_DELAY = 2

def get_soup(url, retry_count=0):
    """URL'den BeautifulSoup nesnesi döndürür."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=20)
        response.raise_for_status()
        # Kanal D genellikle UTF-8 kullanır, ama güvenli olması için
        response.encoding = 'utf-8'
        return BeautifulSoup(response.content, "html.parser")
    except requests.exceptions.Timeout:
        if retry_count < MAX_RETRIES:
            print(f"      ⚠ Timeout! Yeniden deneniyor ({retry_count + 1}/{MAX_RETRIES})")
            time.sleep(RETRY_DELAY)
            return get_soup(url, retry_count + 1)
        else:
            print(f"      ✗ Maksimum deneme sayısına ulaşıldı: {url}")
            return None
    except Exception as e:
        if retry_count < MAX_RETRIES:
            print(f"      ⚠ Hata: {str(e)[:50]}... Yeniden deneniyor ({retry_count + 1}/{MAX_RETRIES})")
            time.sleep(RETRY_DELAY)
            return get_soup(url, retry_count + 1)
        else:
            print(f"      ✗ Hata: {str(e)[:50]}")
            return None

def slugify(text):
    """Metni ID olarak kullanılabilecek formata çevirir"""
    if not text:
        return "dizi"
    
    # Türkçe karakterleri değiştir
    replacements = {
        'ı': 'i', 'İ': 'i', 'ğ': 'g', 'Ğ': 'g',
        'ü': 'u', 'Ü': 'u', 'ş': 's', 'Ş': 's',
        'ö': 'o', 'Ö': 'o', 'ç': 'c', 'Ç': 'c'
    }
    
    for old, new in replacements.items():
        text = text.replace(old, new)
    
    # Küçük harfe çevir ve özel karakterleri temizle
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '-', text)
    text = text.strip('-')
    
    return text

def extract_episode_number(name):
    """Bölüm adından numarayı çeker"""
    if not name:
        return 9999
    
    # "131. Bölüm" formatını ara
    match = re.search(r'(\d+)\.\s*Bölüm', name)
    if match:
        return int(match.group(1))
    
    # "Bölüm 23" formatını ara
    match = re.search(r'Bölüm\s*(\d+)', name, re.IGNORECASE)
    if match:
        return int(match.group(1))
    
    # "Sezon 1 Bölüm 5" formatını ara
    match = re.search(r'Sezon\s*\d+\s*Bölüm\s*(\d+)', name, re.IGNORECASE)
    if match:
        return int(match.group(1))
    
    return 9999

def extract_episode_number_only(name):
    """Bölüm adından sadece sayıyı çıkarır"""
    if not name:
        return "Bölüm"
    
    # "131. Bölüm" formatı
    match = re.search(r'(\d+)\.\s*Bölüm', name)
    if match:
        return f"{match.group(1)}. Bölüm"
    
    # "Bölüm 23" formatı
    match = re.search(r'Bölüm\s*(\d+)', name, re.IGNORECASE)
    if match:
        return f"{match.group(1)}. Bölüm"
    
    # "Sezon 1 Bölüm 5" formatı
    match = re.search(r'Sezon\s*\d+\s*Bölüm\s*(\d+)', name, re.IGNORECASE)
    if match:
        return f"{match.group(1)}. Bölüm"
    
    return name

def get_series_from_archive():
    """Arşiv sayfasındaki tüm dizileri çeker"""
    print("Kanal D Arşiv sayfası taranıyor...")
    
    # Önce arşiv sayfasına git
    archive_url = f"{BASE_URL}/diziler/arsiv"
    soup = get_soup(archive_url)
    
    if not soup:
        print("Arşiv sayfası yüklenemedi!")
        return []
    
    # Dizi listesini bul (Kanal D'de genellikle bu yapıda olur)
    series_list = []
    
    # Dizi kartlarını ara - farklı olası class'lar
    possible_selectors = [
        "a[href*='/diziler/']",  # Dizi linkleri
        "div.dizi-item",  # Dizi item div'leri
        "div.series-item",
        "div.card",
        "div.program-item"
    ]
    
    for selector in possible_selectors:
        items = soup.select(selector)
        if items and len(items) > 5:  # Eğer yeterli sayıda öğe bulduysak
            print(f"  {selector} selector'ı ile {len(items)} öğe bulundu")
            
            for item in items:
                try:
                    # Linki bul
                    link_tag = item
                    if item.name != 'a':
                        link_tag = item.find("a")
                    
                    if not link_tag or not link_tag.get("href"):
                        continue
                    
                    dizi_url = urljoin(BASE_URL, link_tag.get("href"))
                    
                    # Sadece /diziler/ içeren linkleri al
                    if "/diziler/" not in dizi_url:
                        continue
                    
                    # Tekrar edenleri kontrol et
                    if any(s["url"] == dizi_url for s in series_list):
                        continue
                    
                    # Dizi adını bul
                    dizi_adi = ""
                    
                    # Önce img alt text'ini kontrol et
                    img_tag = item.find("img")
                    if img_tag and img_tag.get("alt"):
                        dizi_adi = img_tag.get("alt").strip()
                    else:
                        # Title attribute'ünü kontrol et
                        title_attr = link_tag.get("title") or link_tag.get("data-title")
                        if title_attr:
                            dizi_adi = title_attr.strip()
                        else:
                            # Text içeriğini kontrol et
                            text_elem = item.find(["h3", "h4", "h2", "div.title", "span.title"])
                            if text_elem:
                                dizi_adi = text_elem.get_text(strip=True)
                    
                    # Poster URL'sini bul
                    poster_url = ""
                    if img_tag:
                        poster_url = img_tag.get("data-src") or img_tag.get("src") or ""
                        if poster_url:
                            poster_url = urljoin(BASE_URL, poster_url)
                    
                    if dizi_adi and dizi_url:
                        series_list.append({
                            "name": dizi_adi,
                            "url": dizi_url,
                            "poster": poster_url
                        })
                        
                except Exception as e:
                    continue
    
    # Eğer yukarıdaki selector'lar işe yaramazsa, alternatif yaklaşım
    if not series_list:
        print("  Standart selector'lar işe yaramadı, alternatif yaklaşım deneniyor...")
        
        # Tüm linkleri kontrol et
        all_links = soup.find_all("a", href=True)
        for link in all_links:
            href = link.get("href", "")
            if "/diziler/" in href and href.count('/') >= 3:
                dizi_url = urljoin(BASE_URL, href)
                
                # Tekrar kontrolü
                if any(s["url"] == dizi_url for s in series_list):
                    continue
                
                # Dizi adını bul
                dizi_adi = ""
                img_tag = link.find("img")
                if img_tag and img_tag.get("alt"):
                    dizi_adi = img_tag.get("alt").strip()
                elif link.get("title"):
                    dizi_adi = link.get("title").strip()
                else:
                    # Link text'ini al
                    dizi_adi = link.get_text(strip=True)
                
                # Poster URL'si
                poster_url = ""
                if img_tag:
                    poster_url = img_tag.get("data-src") or img_tag.get("src") or ""
                    if poster_url:
                        poster_url = urljoin(BASE_URL, poster_url)
                
                if dizi_adi and len(dizi_adi) > 2:
                    series_list.append({
                        "name": dizi_adi,
                        "url": dizi_url,
                        "poster": poster_url
                    })
    
    # Benzersiz dizileri filtrele
    unique_series = []
    seen_urls = set()
    for series in series_list:
        if series["url"] not in seen_urls:
            unique_series.append(series)
            seen_urls.add(series["url"])
    
    print(f"  Toplam {len(unique_series)} benzersiz dizi bulundu")
    return unique_series

def get_episodes_for_series(series_url, series_name):
    """Bir dizi için tüm bölümleri çeker"""
    episodes = []
    
    print(f"    '{series_name}' bölümleri aranıyor...")
    
    # Önce bölümler sayfasını kontrol et
    bolumler_url = series_url.rstrip('/') + '/bolumler'
    soup = get_soup(bolumler_url)
    
    if not soup:
        # Bölümler sayfası yoksa, ana sayfadan bölümleri ara
        soup = get_soup(series_url)
        if not soup:
            return episodes
    
    # Video listesini ara
    video_items = []
    
    # Olası video container'ları
    video_selectors = [
        "div.video-item",
        "div.episode-item",
        "div.media-item",
        "a[data-media-id]",
        "div[data-media-id]"
    ]
    
    for selector in video_selectors:
        items = soup.select(selector)
        if items:
            video_items.extend(items)
    
    # Eğer video container bulamazsak, tüm linkleri kontrol et
    if not video_items:
        all_links = soup.find_all("a", href=True)
        for link in all_links:
            href = link.get("href", "")
            if "/video/" in href or "/izle/" in href:
                video_items.append(link)
    
    print(f"      {len(video_items)} video öğesi bulundu")
    
    for item in video_items:
        try:
            # Media ID'yi bul
            media_id = item.get("data-media-id") or item.get("data-id")
            
            # Eğer media_id yoksa, linkten çıkar
            if not media_id:
                href = item.get("href", "")
                match = re.search(r'/video/(\d+)', href)
                if match:
                    media_id = match.group(1)
            
            if not media_id:
                continue
            
            # Bölüm adını bul
            bolum_adi = ""
            
            # Title attribute
            title_attr = item.get("title") or item.get("data-title")
            if title_attr:
                bolum_adi = title_attr.strip()
            else:
                # Text içeriği
                title_elem = item.find(["h3", "h4", "div.title", "span.title"])
                if title_elem:
                    bolum_adi = title_elem.get_text(strip=True)
                else:
                    # Item'ın kendi text'i
                    bolum_adi = item.get_text(strip=True)
            
            # Poster URL'sini bul
            poster_url = ""
            img_tag = item.find("img")
            if img_tag:
                poster_url = img_tag.get("data-src") or img_tag.get("src") or ""
                if poster_url:
                    poster_url = urljoin(BASE_URL, poster_url)
            
            # Video URL'sini oluştur
            video_page_url = urljoin(BASE_URL, f"/video/{media_id}")
            
            episodes.append({
                "id": media_id,
                "name": bolum_adi or f"Bölüm {len(episodes) + 1}",
                "page_url": video_page_url,
                "poster": poster_url
            })
            
        except Exception as e:
            continue
    
    return episodes

def get_video_stream_url(media_id):
    """Media ID'den video stream URL'sini alır"""
    try:
        # Kanal D'nin video API endpoint'i
        api_url = f"https://www.kanald.com.tr/actions/media"
        
        headers = HEADERS.copy()
        headers.update({
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": BASE_URL
        })
        
        data = {"id": media_id}
        
        response = requests.post(api_url, headers=headers, data=data, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        
        # Stream URL'sini ara
        if data.get("status") == "success" and "media" in data:
            media_info = data["media"]
            
            # Önce m3u8 ara
            if "files" in media_info:
                for file in media_info["files"]:
                    if file.get("type") == "application/x-mpegURL":
                        return file.get("url")
            
            # MP4 ara
            if "mp4" in media_info:
                mp4_files = media_info["mp4"]
                if mp4_files and len(mp4_files) > 0:
                    return mp4_files[0].get("src")
        
        return None
        
    except Exception as e:
        print(f"        Video stream alınırken hata: {str(e)[:50]}")
        return None

def main():
    print("=" * 60)
    print("KANAL D DİZİ SCRAPER")
    print("=" * 60)
    
    # Tüm dizileri al
    all_series = get_series_from_archive()
    
    if not all_series:
        print("Hiç dizi bulunamadı!")
        return
    
    diziler_data = {}
    
    # Her dizi için bölümleri çek
    for idx, series in enumerate(all_series, 1):
        series_name = series["name"]
        series_url = series["url"]
        series_poster = series["poster"]
        series_id = slugify(series_name)
        
        print(f"\n[{idx}/{len(all_series)}] {series_name}")
        print(f"  URL: {series_url}")
        
        # Bölümleri al
        episodes = get_episodes_for_series(series_url, series_name)
        
        if not episodes:
            print(f"  ⚠ Hiç bölüm bulunamadı!")
            continue
        
        print(f"  📺 {len(episodes)} bölüm bulundu, stream URL'leri alınıyor...")
        
        final_episodes = []
        
        # Her bölüm için stream URL'sini al
        for ep_idx, episode in enumerate(episodes[:50], 1):  # İlk 50 bölümü al
            print(f"    [{ep_idx}/{min(len(episodes), 50)}] {episode['name'][:40]}...")
            
            stream_url = get_video_stream_url(episode["id"])
            
            if stream_url:
                # Stream URL'sini düzelt
                if stream_url.startswith("//"):
                    stream_url = "https:" + stream_url
                elif stream_url.startswith("/"):
                    stream_url = BASE_URL + stream_url
                
                final_episodes.append({
                    "ad": extract_episode_number_only(episode["name"]),
                    "link": stream_url,
                    "episode_num": extract_episode_number(episode["name"]),
                    "poster": episode["poster"] or series_poster
                })
            
            # Rate limiting
            time.sleep(0.3)
        
        if final_episodes:
            # Bölümleri sırala
            final_episodes.sort(key=lambda x: x["episode_num"])
            
            diziler_data[series_id] = {
                "name": series_name,
                "resim": series_poster,
                "url": series_url,
                "bolumler": [{"ad": ep["ad"], "link": ep["link"]} for ep in final_episodes]
            }
            
            print(f"  ✅ {len(final_episodes)} bölüm eklendi")
        else:
            print(f"  ⚠ Stream URL'si bulunan bölüm yok")
    
    print("\n" + "=" * 60)
    print(f"Toplam {len(diziler_data)} dizi başarıyla işlendi!")
    print("=" * 60)
    
    # HTML dosyasını oluştur
    create_html_file(diziler_data)

def create_html_file(data):
    """HTML arayüz dosyasını oluşturur"""
    # JSON verisini hazırla
    json_str = json.dumps(data, ensure_ascii=False, indent=2)
    
    # HTML şablonu (ShowTV benzeri)
    html_template = '''<!DOCTYPE html>
<html lang="tr">
<head>
    <title>Kanal D VOD</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, user-scalable=no, initial-scale=1.0">
    <link href="https://fonts.googleapis.com/css?family=PT+Sans:700i" rel="stylesheet">
    <script src="https://code.jquery.com/jquery-3.5.1.min.js"></script>
    <script src="https://kit.fontawesome.com/bbe955c5ed.js" crossorigin="anonymous"></script>
    <style>
        *:not(input):not(textarea) {
            -moz-user-select: -moz-none;
            -khtml-user-select: none;
            -webkit-user-select: none;
            -o-user-select: none;
            -ms-user-select: none;
            user-select: none
        }
        body {
            margin: 0;
            padding: 0;
            background: #0c233b;
            font-family: 'PT Sans', sans-serif;
            font-size: 15px;
            -webkit-tap-highlight-color: transparent;
            font-style: italic;
            line-height: 20px;
            -webkit-text-size-adjust: 100%;
            text-decoration: none;
            -webkit-text-decoration: none;
            overflow-x: hidden;
            color: #fff;
        }
        .container {
            width: 96%;
            margin: 0 auto;
            padding: 10px 2%;
        }
        .header {
            background: #0c233b;
            padding: 15px 0;
            border-bottom: 2px solid #1a3a5c;
            text-align: center;
        }
        .logo {
            font-size: 28px;
            color: #fff;
            font-weight: bold;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        .logo span {
            color: #e62117;
        }
        .search-box {
            margin: 20px auto;
            width: 90%;
            max-width: 500px;
        }
        .search-box input {
            width: 100%;
            padding: 12px 20px;
            border: 2px solid #1a3a5c;
            border-radius: 25px;
            background: rgba(255,255,255,0.1);
            color: white;
            font-size: 16px;
            outline: none;
        }
        .search-box input::placeholder {
            color: rgba(255,255,255,0.6);
        }
        .series-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        .series-item {
            background: #1a3a5c;
            border-radius: 10px;
            overflow: hidden;
            transition: all 0.3s ease;
            cursor: pointer;
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        }
        .series-item:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 16px rgba(0,0,0,0.3);
            border: 2px solid #e62117;
        }
        .series-poster {
            width: 100%;
            height: 280px;
            object-fit: cover;
            display: block;
        }
        .series-name {
            padding: 15px;
            text-align: center;
            font-size: 16px;
            font-weight: bold;
            color: white;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .episodes-container {
            display: none;
            margin-top: 20px;
        }
        .back-btn {
            background: #e62117;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
            margin-bottom: 20px;
            transition: background 0.3s;
        }
        .back-btn:hover {
            background: #ff3d32;
        }
        .episodes-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
            gap: 15px;
        }
        .episode-item {
            background: #1a3a5c;
            border-radius: 8px;
            overflow: hidden;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        .episode-item:hover {
            transform: scale(1.05);
            border: 2px solid #e62117;
        }
        .episode-poster {
            width: 100%;
            height: 120px;
            object-fit: cover;
        }
        .episode-name {
            padding: 10px;
            text-align: center;
            font-size: 14px;
            color: white;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .player-container {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.95);
            z-index: 1000;
            display: none;
            flex-direction: column;
        }
        .player-header {
            padding: 20px;
            background: rgba(0,0,0,0.8);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .player-title {
            color: white;
            font-size: 18px;
        }
        .close-player {
            background: #e62117;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
        }
        #video-player {
            flex: 1;
            width: 100%;
        }
        .loading {
            text-align: center;
            padding: 40px;
            color: white;
            font-size: 18px;
        }
        .loading i {
            font-size: 40px;
            color: #e62117;
            margin-bottom: 20px;
        }
        .no-results {
            text-align: center;
            padding: 40px;
            color: rgba(255,255,255,0.7);
            font-size: 18px;
            display: none;
        }
        @media (max-width: 768px) {
            .series-grid {
                grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
                gap: 15px;
            }
            .series-poster {
                height: 220px;
            }
            .episodes-grid {
                grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
                gap: 10px;
            }
            .container {
                width: 94%;
                padding: 10px 3%;
            }
        }
        @media (max-width: 480px) {
            .series-grid {
                grid-template-columns: repeat(2, 1fr);
                gap: 10px;
            }
            .series-poster {
                height: 180px;
            }
            .episodes-grid {
                grid-template-columns: repeat(2, 1fr);
            }
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="logo">KANAL<span>D</span> VOD</div>
    </div>
    
    <div class="container">
        <div class="search-box">
            <input type="text" id="searchInput" placeholder="Dizi ara...">
        </div>
        
        <div id="mainContent">
            <div id="seriesList" class="series-grid">
                <!-- Diziler buraya eklenecek -->
            </div>
        </div>
        
        <div id="episodesContent" class="episodes-container">
            <button class="back-btn" onclick="goBackToSeries()">
                <i class="fas fa-arrow-left"></i> Dizilere Dön
            </button>
            <div id="episodesList" class="episodes-grid">
                <!-- Bölümler buraya eklenecek -->
            </div>
        </div>
        
        <div class="no-results" id="noResults">
            <i class="fas fa-search"></i>
            <div>Aradığınız dizi bulunamadı</div>
        </div>
    </div>
    
    <div class="player-container" id="playerContainer">
        <div class="player-header">
            <div class="player-title" id="playerTitle">Video Oynatıcı</div>
            <button class="close-player" onclick="closePlayer()">
                <i class="fas fa-times"></i> Kapat
            </button>
        </div>
        <video id="video-player" controls autoplay playsinline>
            <source id="videoSource" src="" type="application/x-mpegURL">
            Tarayıcınız video etiketini desteklemiyor.
        </video>
    </div>

    <script>
        const diziler = ''' + json_str + ''';
        
        // Başlangıçta dizileri yükle
        document.addEventListener('DOMContentLoaded', function() {
            loadSeries();
            setupSearch();
        });
        
        function loadSeries() {
            const container = document.getElementById('seriesList');
            container.innerHTML = '';
            
            Object.keys(diziler).forEach(function(seriesId) {
                const series = diziler[seriesId];
                const item = document.createElement('div');
                item.className = 'series-item';
                item.onclick = function() { showEpisodes(seriesId); };
                
                const poster = series.resim || 'https://via.placeholder.com/200x280/1a3a5c/ffffff?text=Kanal+D';
                const name = series.name || seriesId.replace(/-/g, ' ').toUpperCase();
                
                item.innerHTML = `
                    <img src="${poster}" alt="${name}" class="series-poster" 
                         onerror="this.src='https://via.placeholder.com/200x280/1a3a5c/ffffff?text=Kanal+D'">
                    <div class="series-name">${name}</div>
                `;
                
                container.appendChild(item);
            });
        }
        
        function showEpisodes(seriesId) {
            const series = diziler[seriesId];
            if (!series || !series.bolumler) return;
            
            // Dizi listesini gizle
            document.getElementById('mainContent').style.display = 'none';
            document.getElementById('noResults').style.display = 'none';
            
            // Bölümleri göster
            const episodesContainer = document.getElementById('episodesContent');
            const episodesList = document.getElementById('episodesList');
            
            episodesList.innerHTML = '';
            
            series.bolumler.forEach(function(episode, index) {
                const item = document.createElement('div');
                item.className = 'episode-item';
                item.onclick = function() { playVideo(episode.link, episode.ad); };
                
                const poster = series.resim || 'https://via.placeholder.com/180x120/1a3a5c/ffffff?text=Bölüm';
                const name = episode.ad || `Bölüm ${index + 1}`;
                
                item.innerHTML = `
                    <img src="${poster}" alt="${name}" class="episode-poster"
                         onerror="this.src='https://via.placeholder.com/180x120/1a3a5c/ffffff?text=Bölüm'">
                    <div class="episode-name">${name}</div>
                `;
                
                episodesList.appendChild(item);
            });
            
            episodesContainer.style.display = 'block';
            
            // Sayfa başına kaydır
            window.scrollTo({ top: 0, behavior: 'smooth' });
        }
        
        function goBackToSeries() {
            // Bölümleri gizle
            document.getElementById('episodesContent').style.display = 'none';
            
            // Dizileri göster
            document.getElementById('mainContent').style.display = 'block';
            
            // Arama sonuçlarını sıfırla
            document.getElementById('searchInput').value = '';
            loadSeries();
            
            // Sayfa başına kaydır
            window.scrollTo({ top: 0, behavior: 'smooth' });
        }
        
        function playVideo(videoUrl, videoTitle) {
            const playerContainer = document.getElementById('playerContainer');
            const videoPlayer = document.getElementById('video-player');
            const videoSource = document.getElementById('videoSource');
            const playerTitle = document.getElementById('playerTitle');
            
            // Player'ı hazırla
            playerTitle.textContent = videoTitle || 'Video Oynatıcı';
            
            // Video kaynağını ayarla
            videoSource.src = videoUrl;
            videoPlayer.load();
            
            // Player'ı göster
            playerContainer.style.display = 'flex';
            
            // Video oynat
            videoPlayer.play().catch(e => {
                console.log('Otomatik oynatma engellendi:', e);
            });
        }
        
        function closePlayer() {
            const playerContainer = document.getElementById('playerContainer');
            const videoPlayer = document.getElementById('video-player');
            
            // Videoyu durdur
            videoPlayer.pause();
            videoPlayer.currentTime = 0;
            
            // Player'ı gizle
            playerContainer.style.display = 'none';
        }
        
        function setupSearch() {
            const searchInput = document.getElementById('searchInput');
            const noResults = document.getElementById('noResults');
            
            searchInput.addEventListener('input', function() {
                const searchTerm = this.value.toLowerCase().trim();
                
                if (searchTerm === '') {
                    loadSeries();
                    noResults.style.display = 'none';
                    return;
                }
                
                const container = document.getElementById('seriesList');
                container.innerHTML = '';
                
                let found = false;
                
                Object.keys(diziler).forEach(function(seriesId) {
                    const series = diziler[seriesId];
                    const seriesName = (series.name || seriesId).toLowerCase();
                    
                    if (seriesName.includes(searchTerm)) {
                        found = true;
                        
                        const item = document.createElement('div');
                        item.className = 'series-item';
                        item.onclick = function() { showEpisodes(seriesId); };
                        
                        const poster = series.resim || 'https://via.placeholder.com/200x280/1a3a5c/ffffff?text=Kanal+D';
                        const name = series.name || seriesId.replace(/-/g, ' ').toUpperCase();
                        
                        item.innerHTML = `
                            <img src="${poster}" alt="${name}" class="series-poster"
                                 onerror="this.src='https://via.placeholder.com/200x280/1a3a5c/ffffff?text=Kanal+D'">
                            <div class="series-name">${name}</div>
                        `;
                        
                        container.appendChild(item);
                    }
                });
                
                if (found) {
                    noResults.style.display = 'none';
                } else {
                    noResults.style.display = 'block';
                }
            });
        }
        
        // ESC tuşu ile player'ı kapat
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                closePlayer();
            }
        });
        
        // Video oynatıcı hata yönetimi
        document.getElementById('video-player').addEventListener('error', function(e) {
            console.log('Video oynatma hatası:', e);
            alert('Video oynatılırken bir hata oluştu. Lütfen başka bir bölüm deneyin.');
        });
    </script>
</body>
</html>'''
    
    # HTML dosyasını kaydet
    filename = "kanald_vod.html"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html_template)
    
    print(f"\n✅ HTML dosyası '{filename}' başarıyla oluşturuldu!")
    print(f"📂 Dosya boyutu: {os.path.getsize(filename) / 1024:.1f} KB")
    print(f"🎬 Toplam dizi: {len(data)}")
    
    # Bölüm sayısını hesapla
    total_episodes = sum(len(dizi['bolumler']) for dizi in data.values())
    print(f"📺 Toplam bölüm: {total_episodes}")

if __name__ == "__main__":
    main()

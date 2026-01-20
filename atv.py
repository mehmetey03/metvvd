import requests
import re
import time
import json

def get_all_series():
    """Hem güncel hem eski dizileri al"""
    base = "https://www.atv.com.tr"
    series_dict = {}
    
    for page_name, page_url in [("Güncel Diziler", "/diziler"), 
                                ("Eski Diziler", "/eski-diziler")]:
        try:
            print(f"{page_name} sayfası taranıyor...")
            r = requests.get(f"{base}{page_url}", headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            
            # TÜM DİZİLER İÇİN TEK PATTERN
            # <a href="/(dizi-slug)" class="blankpage"> içindeki her şeyi al
            pattern = r'<a href="/([^"]+)"[^>]*?class="[^"]*blankpage[^"]*"[^>]*?>.*?<img[^>]*?src="([^"]+)"[^>]*?alt="([^"]+)"'
            matches = re.findall(pattern, r.text, re.DOTALL)
            
            for slug, logo, name in matches:
                # canli-yayin, fragman gibi şeyleri atla
                if any(x in slug.lower() for x in ['canli-yayin', 'fragman', 'programlar', 'haber']):
                    continue
                
                clean_logo = logo.split('?u=')[1] if '?u=' in logo else logo
                group = "ATV-Güncel-Diziler" if page_url == "/diziler" else "ATV-Eski-Diziler"
                
                if slug not in series_dict:
                    series_dict[slug] = {
                        'name': name.strip(),
                        'slug': slug,
                        'url': f"{base}/{slug}",
                        'logo': clean_logo,
                        'group': group
                    }
            
            print(f"  {len(matches)} dizi bulundu, {len(series_dict)} benzersiz dizi eklendi")
        except Exception as e:
            print(f"  Hata: {e}")
            continue
    
    return list(series_dict.values())

def get_episodes(series_slug, series_name):
    """Dizinin TÜM bölümlerini al - KESİN YÖNTEM"""
    episodes = []
    
    try:
        # 1. ÖNCE /bolumler sayfasını dene
        bolumler_url = f"https://www.atv.com.tr/{series_slug}/bolumler"
        r = requests.get(bolumler_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        
        # Dropdown'dan bölüm numaralarını al
        # <option value="/avrupa-yakasi/189-bolum/izle"> şeklinde
        dropdown_pattern = r'<option[^>]*value="/([^/]+)/(\d+)-bolum/izle"[^>]*>'
        dropdown_matches = re.findall(dropdown_pattern, r.text)
        
        if dropdown_matches:
            for slug, ep_num_str in dropdown_matches:
                if slug == series_slug:
                    ep_url = f"https://www.atv.com.tr/{slug}/{ep_num_str}-bolum/izle"
                    episodes.append((ep_url, int(ep_num_str)))
        
        # 2. Eğer dropdown yoksa, manuel bölüm sayısı tahmini
        if not episodes:
            # Önce kaç bölüm olduğunu tahmin et
            print(f"    ⚠️  Dropdown bulunamadı, bölüm sayısı tahmin ediliyor...")
            
            # Diziye göre tahmini maksimum bölüm
            max_episodes = {
                'karadayi': 115,    # Gerçek bölüm sayısı
                'kara-para-ask': 200,
                'avrupa-yakasi': 300,
                'eskiya-dunyaya-hukmdar-olmaz': 200,
                'sen-anlat-karadeniz': 200,
                'hercai': 200,
                'kurulus-osman': 300,
                'kardeslerim': 200,
                'abi': 20,
                'kurulus-orhan': 20,
                'ayni-yagmur-altinda': 20
            }
            
            # Varsayılan değer
            max_to_check = max_episodes.get(series_slug, 100)
            
            # Her bölümü test et
            found_count = 0
            for i in range(1, max_to_check + 1):
                test_url = f"https://www.atv.com.tr/{series_slug}/{i}-bolum/izle"
                try:
                    test_r = requests.head(test_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=3, allow_redirects=True)
                    if test_r.status_code < 400:  # Başarılı
                        episodes.append((test_url, i))
                        found_count += 1
                        if found_count % 20 == 0:
                            print(f"      {found_count} bölüm bulundu...")
                except:
                    pass
                
                # Çok uzun sürmesin
                if i % 50 == 0:
                    time.sleep(0.1)
            
            print(f"    ✅ {found_count} bölüm bulundu")
        
        # Sırala ve döndür
        if episodes:
            episodes.sort(key=lambda x: x[1])
            return [ep[0] for ep in episodes]
            
    except Exception as e:
        print(f"    Hata: {e}")
    
    return []

def fix_fake_url(video_url):
    """Fake URL'leri gerçek URL'lere çevir"""
    if not video_url:
        return video_url
    
    # Eğer i.tmgrup.com.trvideo/ ile başlıyorsa
    if 'i.tmgrup.com.trvideo/' in video_url:
        # Örnek: https://i.tmgrup.com.trvideo/karadayi_008_0150.mp4
        # Çıkarılacak: karadayi_008_0150.mp4
        try:
            # Dosya adını al
            filename = video_url.split('/')[-1]
            
            # Pattern: diziadi_bölümno_....
            # Örnek: karadayi_008_0150.mp4
            match = re.match(r'([a-zA-Z0-9-]+)_(\d+)_', filename)
            if match:
                dizi_adı = match.group(1)  # karadayi
                bölüm_no = match.group(2)  # 008
                
                # Bölüm numarasını düzelt (008 -> 8)
                bölüm_no_int = int(bölüm_no)
                
                # Gerçek URL'yi oluştur
                # Format: https://atv-vod.ercdn.net/diziadi/bölümno/diziadi_bölümno.smil/playlist.m3u8
                real_url = f"https://atv-vod.ercdn.net/{dizi_adı}/{bölüm_no_int:03d}/{dizi_adı}_{bölüm_no_int:03d}.smil/playlist.m3u8"
                
                print(f"      🔄 Fake URL düzeltildi: {real_url}")
                return real_url
        except Exception as e:
            print(f"      ⚠️  URL düzeltme hatası: {e}")
    
    # Diğer fake URL'ler için
    fake_patterns = [
        (r'i\.tmgrup\.com\.trvideo/([^/]+)_(\d+)_', 
         lambda m: f"https://atv-vod.ercdn.net/{m.group(1)}/{int(m.group(2)):03d}/{m.group(1)}_{int(m.group(2)):03d}.smil/playlist.m3u8"),
        
        (r'//i\.tmgrup\.com\.tr/([^/]+)/(\d+)/', 
         lambda m: f"https://atv-vod.ercdn.net/{m.group(1)}/{int(m.group(2)):03d}/{m.group(1)}_{int(m.group(2)):03d}.smil/playlist.m3u8"),
    ]
    
    for pattern, replacement_func in fake_patterns:
        match = re.search(pattern, video_url)
        if match:
            try:
                real_url = replacement_func(match)
                print(f"      🔄 Fake URL düzeltildi: {real_url}")
                return real_url
            except:
                pass
    
    return video_url

def extract_video_url(episode_url):
    """Video URL'sini çıkar - Fake URL'leri düzelt"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://www.atv.com.tr/'
        }
        
        r = requests.get(episode_url, headers=headers, timeout=15)
        
        # 1. Önce contentUrl ara
        pattern = r'"contentUrl"\s*:\s*"([^"]+)"'
        matches = re.findall(pattern, r.text)
        
        if matches:
            for url in matches:
                # Fake URL'leri kontrol et
                url = fix_fake_url(url)
                
                # MP4 veya M3U8 farketmez, direk döndür
                if any(x in url.lower() for x in ['.mp4', '.m3u8', '//']):
                    return url
        
        # 2. Video dosyalarını ara
        video_patterns = [
            r'(https?://[^\s"\']+\.mp4[^\s"\']*)',
            r'(https?://[^\s"\']+\.m3u8[^\s"\']*)',
            r'src="(https?://[^"]+\.(?:mp4|m3u8)[^"]*)"',
            r'video-src="([^"]+)"'
        ]
        
        for pattern in video_patterns:
            video_matches = re.findall(pattern, r.text, re.IGNORECASE)
            for url in video_matches:
                if 'fragman' not in url.lower():
                    # Fake URL'leri kontrol et
                    url = fix_fake_url(url)
                    return url
        
        # 3. atv-vod.ercdn.net domain'ini ara (eski diziler için)
        if 'atv-vod.ercdn.net' in r.text:
            ercdn_pattern = r'(https?://atv-vod\.ercdn\.net/[^\s"\']+\.(?:mp4|m3u8|smil)[^\s"\']*)'
            ercdn_matches = re.findall(ercdn_pattern, r.text)
            if ercdn_matches:
                return ercdn_matches[0]
        
        # 4. Son çare: Sayfadaki tüm URL'leri ara
        url_pattern = r'(https?://[^\s"\']+/[^\s"\']+\.(?:mp4|m3u8|smil)[^\s"\']*)'
        all_urls = re.findall(url_pattern, r.text)
        for url in all_urls:
            if 'fragman' not in url.lower():
                # Fake URL'leri kontrol et
                url = fix_fake_url(url)
                return url
                
    except Exception as e:
        print(f"      Video URL hatası: {e}")
    
    return None

def slugify(text):
    """Metni ID olarak kullanılabilecek formata çevirir"""
    text = text.lower()
    text = text.replace('ı', 'i').replace('ğ', 'g').replace('ü', 'u')
    text = text.replace('ş', 's').replace('ö', 'o').replace('ç', 'c')
    text = re.sub(r'[^a-z0-9]', '-', text)
    text = re.sub(r'-+', '-', text)
    return text.strip('-')

def clean_image_url(url):
    """Resim URL'sini temizle"""
    if not url:
        return ""
    
    if "?" in url:
        url = url.split("?")[0]
    
    return url.strip()

def main():
    print("ATV TÜM DİZİLER HTML OLUŞTURUCU (FAKE URL DÜZELTİCİ)")
    print("=" * 60)
    
    # Tüm dizileri al
    all_series = get_all_series()
    
    print(f"\nTOPLAM {len(all_series)} DİZİ BULUNDU")
    print("-" * 40)
    
    # Dizi verilerini topla (HTML için)
    diziler_data = {}
    successful_series = 0
    
    for idx, series in enumerate(all_series, 1):
        group_icon = "🆕" if series['group'] == "ATV-Güncel-Diziler" else "📼"
        print(f"\n[{idx}/{len(all_series)}] {group_icon} {series['name']} ({series['group']})")
        
        episodes = get_episodes(series['slug'], series['name'])
        
        if not episodes:
            print(f"  ⚠️  Bölüm bulunamadı")
            continue
            
        print(f"  📺 {len(episodes)} bölüm bulundu")
        successful_series += 1
        
        # Bölüm verilerini işle
        bolum_list = []
        added_count = 0
        
        for ep_url in episodes:
            ep_num = "?"
            match = re.search(r'/(\d+)-bolum', ep_url)
            if match:
                ep_num = match.group(1)
            
            video_url = extract_video_url(ep_url)
            
            if video_url:
                # Fake URL kontrolü
                if 'i.tmgrup.com.trvideo/' in video_url:
                    print(f"    ⚠️  Bölüm {ep_num}: Fake URL tespit edildi, düzeltiliyor...")
                    video_url = fix_fake_url(video_url)
                
                # HTML formatında sadece "1. Bölüm", "2. Bölüm" şeklinde kaydet
                bolum_list.append({
                    "ad": f"{ep_num}. Bölüm",
                    "link": video_url
                })
                added_count += 1
                
                # URL tipini belirle
                url_type = "Fake" if 'i.tmgrup.com.tr' in video_url else ('MP4' if '.mp4' in video_url else 'M3U8')
                print(f"    ✓ Bölüm {ep_num} ({url_type})")
            else:
                print(f"    ✗ Bölüm {ep_num} (video bulunamadı)")
            
            time.sleep(0.1)  # Sunucu yükü için
        
        if added_count > 0:
            # Dizi ID'sini oluştur
            dizi_id = slugify(series['name'])
            
            # Resim URL'sini temizle
            poster_url = clean_image_url(series['logo'])
            if not poster_url:
                poster_url = f"https://via.placeholder.com/300x450/15161a/ffffff?text={series['name'].replace(' ', '+')}"
            
            # Dizi verisini kaydet
            diziler_data[dizi_id] = {
                "resim": poster_url,
                "bolumler": bolum_list
            }
            
            print(f"  ✅ {added_count} bölüm HTML'ye eklendi")
    
    # HTML dosyasını oluştur
    if diziler_data:
        create_html_file(diziler_data, successful_series, len(all_series))
    else:
        print("\n❌ Hiç video bulunamadı!")

def create_html_file(data, processed_count, total_count):
    """HTML dosyasını oluştur"""
    json_str = json.dumps(data, ensure_ascii=False)
    
    html_template = f'''<!DOCTYPE html>
<html lang="tr">
<head>
    <title>ME TV ATV VOD</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, user-scalable=no, initial-scale=1.0">
    <link href="https://fonts.googleapis.com/css?family=PT+Sans:700i" rel="stylesheet">
    <script src="https://code.jquery.com/jquery-3.5.1.min.js"></script>
    <script src="https://kit.fontawesome.com/bbe955c5ed.js" crossorigin="anonymous"></script>
    <script src="https://cdn.jsdelivr.net/npm/@splidejs/splide@4.1.4/dist/js/splide.min.js"></script>
    <style>
        *:not(input):not(textarea) {{
            -moz-user-select: -moz-none;
            -khtml-user-select: none;
            -webkit-user-select: none;
            -o-user-select: none;
            -ms-user-select: none;
            user-select: none
        }}
        body {{
            margin: 0;
            padding: 0;
            background: #00040d;
            font-family: sans-serif;
            font-size: 15px;
            -webkit-tap-highlight-color: transparent;
            font-style: italic;
            line-height: 20px;
            -webkit-text-size-adjust: 100%;
            text-decoration: none;
            -webkit-text-decoration: none;
            overflow-x: hidden;
        }}
        .hataekran i {{
            color: #ff0000;
            font-size: 80px;
            text-align: center;
            width: 100%;
        }}
        .hataekran {{
            width: 80%;
            margin: 20px auto;
            color: #fff;
            background: #15161a;
            border: 1px solid #323442;
            padding: 10px;
            box-sizing: border-box;
            border-radius: 10px;
        }}
        .hatayazi {{
            color: #fff;
            font-size: 15px;
            text-align: center;
            width: 100%;
            margin: 20px 0px;
        }}
        .filmpaneldis {{
            background: #15161a;
            width: 100%;
            margin: 20px auto;
            overflow: hidden;
            padding: 10px 5px;
            box-sizing: border-box;
        }}
        .baslik {{
            width: 96%;
            color: #fff;
            padding: 15px 10px;
            box-sizing: border-box;
            font-size: 18px;
            font-weight: bold;
        }}
        .filmpanel {{
            width: 12%;
            height: 200px;
            background: #15161a;
            float: left;
            margin: 1.14%;
            color: #fff;
            border-radius: 15px;
            box-sizing: border-box;
            box-shadow: 1px 5px 10px rgba(0,0,0,0.1);
            border: 1px solid #323442;
            padding: 0px;
            overflow: hidden;
            transition: border 0.3s ease, box-shadow 0.3s ease;
            cursor: pointer;
        }}
        .filmisimpanel {{
            width: 100%;
            height: 200px;
            position: relative;
            margin-top: -200px;
            background: linear-gradient(to bottom, rgba(0, 0, 0, 0) 0%, rgba(0, 0, 0, 1) 100%);
        }}
        .filmpanel:hover {{
            color: #fff;
            border: 3px solid #ff0000;
            box-shadow: 0 0 10px rgba(255, 0, 0, 0.5);
        }}
        .filmpanel:focus {{
            outline: none;
            border: 3px solid #ff0000;
            box-shadow: 0 0 10px rgba(255, 0, 0, 0.5);
        }}
        .filmresim {{
            width: 100%;
            height: 100%;
            margin-bottom: 0px;
            overflow: hidden;
            position: relative;
        }}
        .filmresim img {{
            width: 100%;
            height: 100%;
            object-fit: cover;
            transition: transform 0.4s ease;
        }}
        .filmpanel:hover .filmresim img {{
            transform: scale(1.1);
        }}
        .filmpanel:focus .filmresim img {{
            transform: none;
        }}
        .filmisim {{
            width: 100%;
            font-size: 14px;
            text-decoration: none;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            padding: 0px 5px;
            box-sizing: border-box;
            color: #fff;
            position: absolute;
            bottom: 5px;
            text-align: center;
            font-weight: bold;
        }}
        .aramapanel {{
            width: 100%;
            height: 60px;
            background: #15161a;
            border-bottom: 1px solid #323442;
            margin: 0px auto;
            padding: 10px;
            box-sizing: border-box;
            overflow: hidden;
            z-index: 11111;
        }}
        .aramapanelsag {{
            width: auto;
            height: 40px;
            box-sizing: border-box;
            overflow: hidden;
            float: right;
        }}
        .aramapanelsol {{
            width: 50%;
            height: 40px;
            box-sizing: border-box;
            overflow: hidden;
            float: left;
        }}
        .aramapanelyazi {{
            height: 40px;
            width: 120px;
            border: 1px solid #ccc;
            box-sizing: border-box;
            padding: 0px 10px;
            background: ;
            color: #000;
            margin: 0px 5px;
        }}
        .aramapanelbuton {{
            height: 40px;
            width: 40px;
            text-align: center;
            background-color: #ff0000;
            border: none;
            color: #fff;
            box-sizing: border-box;
            overflow: hidden;
            float: right;
            transition: .35s;
        }}
        .aramapanelbuton:hover {{
            background-color: #fff;
            color: #000;
        }}
        .logo {{
            width: 40px;
            height: 40px;
            float: left;
        }}
        .logo img {{
            width: 100%;
        }}
        .logoisim {{
            font-size: 15px;
            width: 70%;
            height: 40px;
            line-height: 40px;
            font-weight: 500;
            color: #fff;
        }}
        .hidden {{ display: none; }}
        .bolum-container {{
            background: #15161a;
            padding: 10px;
            margin-top: 10px;
            border-radius: 5px;
        }}
        .geri-btn {{
            background: #ff0000;
            color: white;
            padding: 10px;
            text-align: center;
            border-radius: 5px;
            cursor: pointer;
            margin-top: 10px;
            margin-bottom: 10px;
            display: none;
            width: 100px;
        }}
        .geri-btn:hover {{
            background: #ff3333;
            transition: background 0.3s;
        }}
        .playerpanel {{
            width: 100%;
            height: 100vh;
            position: fixed;
            top: 0;
            left: 0;
            background: #0a0e17;
            z-index: 9999;
            display: none;
            flex-direction: column;
            overflow: hidden;
        }}
        
        #main-player {{
            width: 100%;
            height: 100%; 
            background: #000;
        }}
        
        #bradmax-iframe {{
            width: 100%;
            height: 100%;
            border: none;
        }}

        .player-geri-btn {{
            background: #ff0000;
            color: white;
            padding: 10px;
            text-align: center;
            border-radius: 5px;
            cursor: pointer;
            margin: 10px;
            width: 100px;
            position: absolute;
            top: 10px;
            left: 10px;
            z-index: 10000;
        }}
        
        @media(max-width:550px) {{
            .filmpanel {{
                width: 31.33%;
                height: 190px;
                margin: 1%;
            }}
            #main-player {{
                height: 100%; 
            }}
        }}
    </style>
</head>
<body>
    <div class="aramapanel">
        <div class="aramapanelsol">
            <div class="logo"><img src="https://i.hizliresim.com/t6e66bt.png"></div>
            <div class="logoisim">ME TV ATV VOD</div>
        </div>
        <div class="aramapanelsag">
            <form action="" name="ara" method="GET" onsubmit="return searchSeries()">
                <input type="text" id="seriesSearch" placeholder="Dizi Adını Giriniz..!" class="aramapanelyazi" oninput="resetSeriesSearch()">
                <input type="submit" value="ARA" class="aramapanelbuton">
            </form>
        </div>
    </div>

    <div class="filmpaneldis" id="diziListesiContainer">
        <div class="baslik">ATV DİZİLERİ </div>
    </div>

    <div id="bolumler" class="bolum-container hidden">
        <div id="geriBtn" class="geri-btn" onclick="geriDon()">Geri</div>
        <div id="bolumListesi" class="filmpaneldis"></div>
    </div>

    <div id="playerpanel" class="playerpanel">
        <div class="player-geri-btn" onclick="geriPlayer()">Geri</div>
        <div id="main-player"></div>
    </div>

    <script>
        const BRADMAX_BASE_URL = "https://bradmax.com/client/embed-player/d9decbf0d308f4bb91825c3f3a2beb7b0aaee2f6_8493?mediaUrl=";
        const BRADMAX_PARAMS = "&autoplay=true&fs=true"; 

        var diziler = {json_str};

        document.addEventListener('DOMContentLoaded', function() {{
            var container = document.getElementById("diziListesiContainer");
            
            Object.keys(diziler).forEach(function(key) {{
                var dizi = diziler[key];
                var item = document.createElement("div");
                item.className = "filmpanel";
                item.onclick = function() {{ showBolumler(key); }};
                item.innerHTML = `
                    <div class="filmresim"><img src="${{dizi.resim}}" onerror="this.src='https://via.placeholder.com/300x450/15161a/ffffff?text=ATV+TV'"></div>
                    <div class="filmisimpanel">
                        <div class="filmisim">${{key.replace(/-/g, ' ').toUpperCase()}}</div>
                    </div>
                `;
                container.appendChild(item);
            }});

            checkInitialState();
        }});

        let currentScreen = 'anaSayfa';

        function showBolumler(diziID) {{
            sessionStorage.setItem('currentDiziID', diziID);
            var listContainer = document.getElementById("bolumListesi");
            listContainer.innerHTML = "";
            
            if (diziler[diziID]) {{
                diziler[diziID].bolumler.forEach(function(bolum) {{
                    var item = document.createElement("div");
                    item.className = "filmpanel";
                    item.innerHTML = `
                        <div class="filmresim"><img src="${{diziler[diziID].resim}}" onerror="this.src='https://via.placeholder.com/300x450/15161a/ffffff?text=ATV+TV'"></div>
                        <div class="filmisimpanel">
                            <div class="filmisim">${{bolum.ad}}</div>
                        </div>
                    `;
                    item.onclick = function() {{
                        showPlayer(bolum.link, diziID);
                    }};
                    listContainer.appendChild(item);
                }});
            }} else {{
                listContainer.innerHTML = "<p>Bu dizi için bölüm bulunamadı.</p>";
            }}
            
            document.querySelector("#diziListesiContainer").classList.add("hidden");
            document.getElementById("bolumler").classList.remove("hidden");
            document.getElementById("geriBtn").style.display = "block";

            currentScreen = 'bolumler';
            history.replaceState({{ page: 'bolumler', diziID: diziID }}, '', '#bolumler-' + diziID);
        }}

        function showPlayer(streamUrl, diziID) {{
            document.getElementById("playerpanel").style.display = "flex"; 
            document.getElementById("bolumler").classList.add("hidden");

            currentScreen = 'player';
            history.pushState({{ page: 'player', diziID: diziID, streamUrl: streamUrl }}, '', '#player-' + diziID);

            document.getElementById("main-player").innerHTML = "";

            const fullUrl = BRADMAX_BASE_URL + encodeURIComponent(streamUrl) + BRADMAX_PARAMS;
            const iframeHtml = `<iframe id="bradmax-iframe" src="${{fullUrl}}" allowfullscreen tabindex="0" autofocus></iframe>`;
            
            document.getElementById("main-player").innerHTML = iframeHtml;
        }}

        function geriPlayer() {{
            document.getElementById("playerpanel").style.display = "none";
            document.getElementById("bolumler").classList.remove("hidden");

            document.getElementById("main-player").innerHTML = "";

            currentScreen = 'bolumler';
            var currentDiziID = sessionStorage.getItem('currentDiziID');
            history.replaceState({{ page: 'bolumler', diziID: currentDiziID }}, '', '#bolumler-' + currentDiziID);
        }}

        function geriDon() {{
            sessionStorage.removeItem('currentDiziID');
            document.querySelector("#diziListesiContainer").classList.remove("hidden");
            document.getElementById("bolumler").classList.add("hidden");
            document.getElementById("geriBtn").style.display = "none";
            
            currentScreen = 'anaSayfa';
            history.replaceState({{ page: 'anaSayfa' }}, '', '#anaSayfa');
        }}

        window.addEventListener('popstate', function(event) {{
            var currentDiziID = sessionStorage.getItem('currentDiziID');
            
            if (event.state && event.state.page === 'player' && event.state.diziID && event.state.streamUrl) {{
                showBolumler(event.state.diziID);
                showPlayer(event.state.streamUrl, event.state.diziID);
            }} else if (event.state && event.state.page === 'bolumler' && event.state.diziID) {{
                showBolumler(event.state.diziID);
            }} else {{
                sessionStorage.removeItem('currentDiziID');
                document.querySelector("#diziListesiContainer").classList.remove("hidden");
                document.getElementById("bolumler").classList.add("hidden");
                document.getElementById("playerpanel").style.display = "none";
                document.getElementById("geriBtn").style.display = "none";
                currentScreen = 'anaSayfa';
            }}
        }});

        function checkInitialState() {{
            var hash = window.location.hash;
            if (hash.startsWith('#bolumler-')) {{
                var diziID = hash.replace('#bolumler-', '');
                showBolumler(diziID);
            }} else if (hash.startsWith('#player-')) {{
                var parts = hash.split('-');
                var diziID = parts[1];
                var streamUrl = sessionStorage.getItem('lastStreamUrl');
                if (streamUrl) {{
                    showBolumler(diziID);
                    setTimeout(() => {{ showPlayer(streamUrl, diziID); }}, 100);
                }}
            }}
        }}

        function searchSeries() {{
            var searchTerm = document.getElementById('seriesSearch').value.toLowerCase();
            var container = document.getElementById('diziListesiContainer');
            var panels = container.querySelectorAll('.filmpanel');
            var found = false;

            panels.forEach(function(panel) {{
                var seriesName = panel.querySelector('.filmisim').textContent.toLowerCase();
                if (seriesName.includes(searchTerm)) {{
                    panel.style.display = 'block';
                    found = true;
                }} else {{
                    panel.style.display = 'none';
                }}
            }});

            if (!found) {{
                var noResults = document.createElement('div');
                noResults.className = 'hataekran';
                noResults.innerHTML = '<i class="fas fa-search"></i><div class="hatayazi">Sonuç bulunamadı!</div>';
                container.appendChild(noResults);
            }}

            return false;
        }}

        function resetSeriesSearch() {{
            var container = document.getElementById('diziListesiContainer');
            var panels = container.querySelectorAll('.filmpanel');
            panels.forEach(function(panel) {{
                panel.style.display = 'block';
            }});
            var noResults = container.querySelector('.hataekran');
            if (noResults) {{
                noResults.remove();
            }}
        }}

        // Yükleme tamamlandığında hash kontrolü yap
        window.addEventListener('load', function() {{
            setTimeout(checkInitialState, 100);
        }});
    </script>
</body>
</html>'''
    
    filename = "atv.html"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html_template)
    
    print(f"\n" + "=" * 60)
    print("✅ HTML OLUŞTURULDU!")
    print("=" * 60)
    print(f"📊 İSTATİSTİKLER:")
    print(f"   • Toplam Dizi: {total_count}")
    print(f"   • İşlenen Dizi: {processed_count}")
    print(f"   • HTML Dosyası: '{filename}'")
    print("=" * 60)

if __name__ == "__main__":
    main()

import json
import os

def create_now_vod_html():
    # 1. JSON Verisini Oku
    json_file = 'nowtv_data.json'
    if not os.path.exists(json_file):
        print(f"❌ {json_file} bulunamadı! Lütfen önce json dosyanızı oluşturun.")
        return

    with open(json_file, 'r', encoding='utf-8') as f:
        diziler_data = json.load(f)

    # JSON verisini HTML içine gömmek için string'e çevir
    json_str = json.dumps(diziler_data, ensure_ascii=False)

    # 2. HTML Şablonu (Senin verdiğin ME TV Tasarımı)
    html_template = f'''<!DOCTYPE html>
<html lang="tr">
<head>
    <title>ME TV NOW VOD</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, user-scalable=no, initial-scale=1.0">
    <link href="https://fonts.googleapis.com/css?family=PT+Sans:700i" rel="stylesheet">
    <script src="https://code.jquery.com/jquery-3.5.1.min.js"></script>
    <script src="https://kit.fontawesome.com/bbe955c5ed.js" crossorigin="anonymous"></script>
    <style>
        *:not(input):not(textarea) {{ -webkit-user-select: none; user-select: none; }}
        body {{ margin: 0; background: #00040d; font-family: sans-serif; color: #fff; overflow-x: hidden; font-style: italic; }}
        .aramapanel {{ width: 100%; height: 60px; background: #15161a; border-bottom: 1px solid #323442; padding: 10px; box-sizing: border-box; display: flex; justify-content: space-between; align-items: center; }}
        .logo-section {{ display: flex; align-items: center; }}
        .logo {{ width: 40px; height: 40px; margin-right: 10px; }}
        .logo img {{ width: 100%; }}
        .logoisim {{ font-size: 18px; font-weight: bold; color: #572aa7; }}
        
        .aramapanelyazi {{ height: 35px; width: 180px; border: 1px solid #323442; background: #000; color: #fff; padding: 0 10px; border-radius: 5px; }}
        .aramapanelbuton {{ height: 35px; background: #572aa7; border: none; color: #fff; padding: 0 15px; cursor: pointer; border-radius: 5px; }}

        .baslik {{ padding: 20px; font-size: 20px; border-left: 5px solid #572aa7; margin: 20px; background: #15161a; }}
        
        .filmpaneldis {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 15px; padding: 20px; }}
        .filmpanel {{ background: #15161a; border: 1px solid #323442; border-radius: 10px; overflow: hidden; cursor: pointer; transition: 0.3s; position: relative; height: 250px; }}
        .filmpanel:hover {{ border-color: #572aa7; transform: scale(1.05); box-shadow: 0 0 15px rgba(87, 42, 167, 0.5); }}
        
        .filmresim {{ width: 100%; height: 100%; }}
        .filmresim img {{ width: 100%; height: 100%; object-fit: cover; }}
        
        .filmisimpanel {{ position: absolute; bottom: 0; width: 100%; background: linear-gradient(transparent, black); padding: 20px 5px 5px 5px; box-sizing: border-box; }}
        .filmisim {{ font-size: 13px; font-weight: bold; text-align: center; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}

        /* Player Bölümü */
        .playerpanel {{ position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: #000; z-index: 9999; display: none; }}
        .player-geri-btn {{ position: absolute; top: 20px; left: 20px; background: #572aa7; color: #fff; padding: 10px 20px; border-radius: 5px; cursor: pointer; z-index: 10001; }}
        iframe {{ width: 100%; height: 100%; border: none; }}

        @media(max-width: 600px) {{
            .filmpaneldis {{ grid-template-columns: repeat(3, 1fr); padding: 10px; gap: 10px; }}
            .filmpanel {{ height: 180px; }}
        }}
    </style>
</head>
<body>
    <div class="aramapanel">
        <div class="logo-section">
            <div class="logo"><img src="https://i.hizliresim.com/t6e66bt.png"></div>
            <div class="logoisim">ME TV NOW</div>
        </div>
        <div>
            <input type="text" id="search" placeholder="Dizi Ara..." class="aramapanelyazi" oninput="doSearch()">
        </div>
    </div>

    <div class="baslik">NOW TV DİZİ ARŞİVİ</div>
    
    <div class="filmpaneldis" id="mainGrid"></div>

    <div id="playerpanel" class="playerpanel">
        <div class="player-geri-btn" onclick="closePlayer()">GERİ DÖN</div>
        <div id="videoContainer" style="width:100%; height:100%;"></div>
    </div>

    <script>
        var diziler = {json_str};
        var mainGrid = document.getElementById("mainGrid");

        // Listeleme
        function renderList(filter = "") {{
            mainGrid.innerHTML = "";
            Object.keys(diziler).forEach(key => {{
                let dizi = diziler[key];
                if(dizi.isim.toLowerCase().includes(filter.toLowerCase())) {{
                    let item = document.createElement("div");
                    item.className = "filmpanel";
                    item.onclick = () => openPlayer(dizi.link);
                    item.innerHTML = `
                        <div class="filmresim"><img src="${{dizi.resim}}"></div>
                        <div class="filmisimpanel">
                            <div class="filmisim">${{dizi.isim}}</div>
                        </div>
                    `;
                    mainGrid.appendChild(item);
                }}
            }});
        }}

        // Arama
        function doSearch() {{
            renderList(document.getElementById("search").value);
        }}

        // Player Aç (Bradmax üzerinden linki oynatır)
        function openPlayer(url) {{
            const bradmaxUrl = "https://bradmax.com/client/embed-player/d9decbf0d308f4bb91825c3f3a2beb7b0aaee2f6_8493?mediaUrl=";
            document.getElementById("playerpanel").style.display = "block";
            document.getElementById("videoContainer").innerHTML = `<iframe src="${{bradmaxUrl + encodeURIComponent(url)}}&autoplay=true" allowfullscreen></iframe>`;
        }}

        function closePlayer() {{
            document.getElementById("playerpanel").style.display = "none";
            document.getElementById("videoContainer").innerHTML = "";
        }}

        renderList();
    </script>
</body>
</html>
'''
    # 3. HTML'i Kaydet
    with open("nowtv_me_vod.html", "w", encoding="utf-8") as f:
        f.write(html_template)
    
    print(f"✅ İşlem Tamam! {len(diziler_data)} dizi ME TV arayüzüne aktarıldı.")
    print("🚀 'nowtv_me_vod.html' dosyasını tarayıcıda açabilirsiniz.")

if __name__ == "__main__":
    create_now_vod_html()

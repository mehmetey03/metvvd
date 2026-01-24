import requests
import re
import base64
import string
import time

# --- AYARLAR ---
START_PAGE = 1
END_PAGE = 4521
BASE_URL = "https://dizigom104.com/tum-bolumler/page/"
FIRST_PAGE = "https://dizigom104.com/tum-bolumler/"
M3U_FILENAME = "dizigom_arsiv.m3u"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Referer": "https://dizigom104.com/"
}

def check_link_is_active(url):
    try:
        r = requests.head(url, headers=HEADERS, timeout=1.5, allow_redirects=True)
        return r.status_code == 200
    except: return False

def get_m3u8_link(embed_url):
    try:
        r = requests.get(embed_url, headers=HEADERS, timeout=10)
        m2 = re.search(r"eval\(function\(p,a,c,k,e,d\).*?\('(.+?)'\.split\('\|'\)", r.text, re.S)
        if not m2: return None
        parts = m2.group(1).split("|")
        video_hash = next((p for p in parts if re.fullmatch(r"[a-f0-9]{32}", p)), None)
        if not video_hash: return None
        letters = string.ascii_lowercase
        for char in letters:
            for num in ["1", "2"]:
                prefix = f"{char}{num}"
                test_url = f"https://{prefix}.df856-54hilsnz.xyz/storage/media/{video_hash}-720.mp4/gomindex.m3u8"
                if check_link_is_active(test_url): return test_url
        return None
    except: return None

def get_embed_from_episode(episode_url):
    try:
        r = requests.get(episode_url, headers=HEADERS, timeout=10)
        pattern = r'eval\(function\(h,u,n,t,e,r\).*?\("(.*?)",(\d+),"(.*?)",(\d+),(\d+),(\d+)\)'
        match = re.search(pattern, r.text)
        if not match: return None
        h_data, u_val, n_data, t_val, e_val, r_val = match.groups()
        u_val, t_val, e_val, r_val = int(u_val), int(t_val), int(e_val), int(r_val)
        def _0xe2c(d, e, f):
            g = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ+/"
            h, i = g[0:e], g[0:f]
            j = 0
            for idx, char in enumerate(d[::-1]):
                if char in h: j += h.find(char) * (e ** idx)
            k = ""
            while j > 0:
                k = i[j % f] + k
                j = (j - (j % f)) // f
            return k or "0"
        decoded_js = ""
        idx_i = 0
        while idx_i < len(h_data):
            s = ""
            while idx_i < len(h_data) and h_data[idx_i] != n_data[e_val]:
                s += h_data[idx_i]
                idx_i += 1
            for j in range(len(n_data)): s = s.replace(n_data[j], str(j))
            if s: decoded_js += chr(int(_0xe2c(s, e_val, 10)) - t_val)
            idx_i += 1
        api_path_match = re.search(r'/(api/watch/.*?\.dizigom)', decoded_js)
        if not api_path_match: return None
        api_res = requests.get("https://dizigom104.com/" + api_path_match.group(1), headers=HEADERS)
        final_html = base64.b64decode(api_res.text).decode('utf-8')
        embed_match = re.search(r'src=["\'](https?://.*?)["\']', final_html)
        return embed_match.group(1) if embed_match else None
    except: return None

def main():
    print(f"--- DIZIGOM FULL ARSIV BOTU BAŞLATILDI ---")
    with open(M3U_FILENAME, "a", encoding="utf-8") as f:
        if f.tell() == 0: f.write("#EXTM3U\n")
        
        for p_idx in range(START_PAGE, END_PAGE + 1):
            url = FIRST_PAGE if p_idx == 1 else f"{BASE_URL}{p_idx}/"
            print(f"\n[SAYFA {p_idx}] taranıyor: {url}")
            
            try:
                res = requests.get(url, headers=HEADERS, timeout=15)
                # TÜMÜNÜ YAKALAYAN GENİŞ REGEX:
                # Sitedeki her bir bölüm bloğunu (link, resim ve alt başlık) yakalar.
                items = re.findall(r'<div class="bolumust">.*?href="(.*?)".*?src="(.*?)".*?alt="(.*?)"', res.text, re.S)
                
                # Eğer üstteki boş dönerse (Bazı sayfalarda link img'den sonra geliyor olabilir):
                if not items:
                    items = re.findall(r'<a href="(https://dizigom104\.com/.*?bolum/.*?)".*?title="(.*?)"', res.text, re.S)

                if not items:
                    # Manuel Debug: Sayfada ne var?
                    print(f"!!! Veri yakalanamadı. Kaynak kodunda 'bolumust' araması başarısız.")
                    continue

                for item in items:
                    # Pattern'e göre değişkenleri ata
                    if len(item) == 3:
                        b_link, b_img, b_title = item
                    else:
                        b_link, b_title = item
                        b_img = "" # Resim yoksa boş bırak

                    b_title = b_title.replace("izle", "").replace("İzle", "").strip()
                    print(f"  > {b_title}", end=" ", flush=True)
                    
                    embed = get_embed_from_episode(b_link)
                    if embed:
                        m3u8 = get_m3u8_link(embed)
                        if m3u8:
                            f.write(f'#EXTINF:-1 tvg-logo="{b_img}" group-title="Dizigom-Arsiv",{b_title}\n')
                            f.write(f'{m3u8}\n')
                            f.flush()
                            print("[OK]")
                        else: print("[M3U8 YOK]")
                    else: print("[PLAYER YOK]")
                    time.sleep(0.05)

            except Exception as e:
                print(f"\n[HATA] {p_idx}. sayfada: {e}")
                time.sleep(2)

if __name__ == "__main__":
    main()

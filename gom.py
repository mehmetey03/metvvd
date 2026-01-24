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

# Oturum Yönetimi ve Tarayıcı Taklidi
session = requests.Session()
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Referer": "https://dizigom104.com/",
}

def check_link_is_active(url):
    try:
        r = session.head(url, headers=HEADERS, timeout=2, allow_redirects=True)
        return r.status_code == 200
    except: return False

def get_m3u8_link(embed_url):
    try:
        r = session.get(embed_url, headers=HEADERS, timeout=10)
        m2 = re.search(r"eval\(function\(p,a,c,k,e,d\).*?\('(.+?)'\.split\('\|'\)", r.text, re.S)
        if not m2: return None
        parts = m2.group(1).split("|")
        video_hash = next((p for p in parts if re.fullmatch(r"[a-f0-9]{32}", p)), None)
        if not video_hash: return None
        letters = string.ascii_lowercase
        for char in letters:
            for num in ["1", "2"]:
                test_url = f"https://{char}{num}.df856-54hilsnz.xyz/storage/media/{video_hash}-720.mp4/gomindex.m3u8"
                if check_link_is_active(test_url): return test_url
        return None
    except: return None

def get_embed_from_episode(episode_url):
    try:
        r = session.get(episode_url, headers=HEADERS, timeout=10)
        pattern = r'eval\(function\(h,u,n,t,e,r\).*?\("(.*?)",(\d+),"(.*?)",(\d+),(\d+),(\d+)\)'
        match = re.search(pattern, r.text)
        if not match: return None
        h, u, n, t, e, _ = match.groups()
        u, t, e = int(u), int(t), int(e)
        def _dec(d, e, f):
            g = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ+/"
            h_str, i_str = g[0:e], g[0:f]
            j = 0
            for idx, char in enumerate(d[::-1]):
                if char in h_str: j += h_str.find(char) * (e ** idx)
            k = ""
            while j > 0:
                k = i_str[j % f] + k
                j = (j - (j % f)) // f
            return k or "0"
        decoded = ""
        idx = 0
        while idx < len(h):
            s = ""
            while idx < len(h) and h[idx] != n[e]:
                s += h[idx]
                idx += 1
            for j in range(len(n)): s = s.replace(n[j], str(j))
            if s: decoded += chr(int(_dec(s, e, 10)) - t)
            idx += 1
        api_path = re.search(r'/(api/watch/.*?\.dizigom)', decoded)
        if not api_path: return None
        api_res = session.get("https://dizigom104.com/" + api_path.group(1), headers=HEADERS)
        final_html = base64.b64decode(api_res.text).decode('utf-8')
        embed = re.search(r'src=["\'](https?://.*?)["\']', final_html)
        return embed.group(1) if embed else None
    except: return None

def main():
    print(f"--- DIZIGOM FULL ARSIV BOTU (v4.0) BAŞLATILDI ---")
    with open(M3U_FILENAME, "a", encoding="utf-8") as f:
        if f.tell() == 0: f.write("#EXTM3U\n")
        
        for p_idx in range(START_PAGE, END_PAGE + 1):
            url = FIRST_PAGE if p_idx == 1 else f"{BASE_URL}{p_idx}/"
            print(f"\n[SAYFA {p_idx}] taranıyor...", end=" ", flush=True)
            
            try:
                res = session.get(url, headers=HEADERS, timeout=15)
                # PAYLAŞTIĞIN HTML YAPISINA GÖRE YAKALAMA (Regex):
                # 1. Link, 2. Resim (data-src), 3. Başlık (alt)
                items = re.findall(r'<div class="poster">.*?<a href="(.*?)".*?data-src="(.*?)".*?alt="(.*?)"', res.text, re.S)

                if not items:
                    print("Hata: Bölüm bulunamadı!")
                    continue

                print(f"{len(items)} bölüm yakalandı.")

                for b_link, b_img, b_title in items:
                    # Başlıktaki gereksiz "izle" kelimesini temizle
                    b_title = b_title.replace("türkçe altyazılı izle", "").replace("izle", "").strip()
                    
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
                print(f"Hata: {e}")
                time.sleep(2)

if __name__ == "__main__":
    main()

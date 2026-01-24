import requests
import re
import base64
import string
import time

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Referer": "https://play.dizigom104.com/"
}

BASE_URL = "https://dizigom104.com"


# -------------------------------------------------
# LINK AKTİF Mİ
# -------------------------------------------------
def check_link_is_active(url):
    try:
        r = requests.head(url, headers=HEADERS, timeout=2, allow_redirects=True)
        return r.status_code == 200
    except:
        return False


# -------------------------------------------------
# EMBED → M3U8
# -------------------------------------------------
def get_m3u8_link(embed_url):
    try:
        r = requests.get(embed_url, headers=HEADERS, timeout=10)

        m = re.search(
            r"eval\(function\(p,a,c,k,e,d\).*?\('(.+?)'\.split\('\|'\)",
            r.text,
            re.S
        )
        if not m:
            return None

        parts = m.group(1).split("|")
        video_hash = next((p for p in parts if re.fullmatch(r"[a-f0-9]{32}", p)), None)
        if not video_hash:
            return None

        for c in string.ascii_lowercase:
            for n in ("1", "2"):
                url = f"https://{c}{n}.df856-54hilsnz.xyz/storage/media/{video_hash}-720.mp4/gomindex.m3u8"
                if check_link_is_active(url):
                    return url

        return None
    except:
        return None


# -------------------------------------------------
# BÖLÜM → EMBED
# -------------------------------------------------
def get_embed_from_episode(episode_url):
    try:
        r = requests.get(episode_url, headers=HEADERS, timeout=10)

        m = re.search(
            r'eval\(function\(h,u,n,t,e,r\).*?\("(.*?)",(\d+),"(.*?)",(\d+),(\d+),(\d+)\)',
            r.text
        )
        if not m:
            return None

        h_data, u, n_data, t, e, r_ = m.groups()
        u, t, e, r_ = map(int, (u, t, e, r_))

        def dec(d, e, f):
            chars = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ+/"
            h, i = chars[:e], chars[:f]
            j = 0
            for x, c in enumerate(d[::-1]):
                if c in h:
                    j += h.index(c) * (e ** x)
            out = ""
            while j:
                out = i[j % f] + out
                j //= f
            return out or "0"

        decoded = ""
        i = 0
        while i < len(h_data):
            s = ""
            while i < len(h_data) and h_data[i] != n_data[e]:
                s += h_data[i]
                i += 1
            for j in range(len(n_data)):
                s = s.replace(n_data[j], str(j))
            if s:
                decoded += chr(int(dec(s, e, 10)) - t)
            i += 1

        api = re.search(r'/(api/watch/.*?\.dizigom)', decoded)
        if not api:
            return None

        api_res = requests.get(BASE_URL + api.group(1), headers=HEADERS)
        html = base64.b64decode(api_res.text).decode("utf-8")

        src = re.search(r'src=["\'](https?://.*?)["\']', html)
        return src.group(1) if src else None

    except:
        return None


# -------------------------------------------------
# TUM-BOLUMELER → TÜM BÖLÜM LINKLERİ (DOĞRU HAL)
# -------------------------------------------------
def get_all_episode_links(max_page=4521):
    episodes = set()

    for page in range(1, max_page + 1):
        url = f"{BASE_URL}/tum-bolumler/" if page == 1 else f"{BASE_URL}/tum-bolumler/page/{page}/"
        print(f"[SAYFA] {page}/{max_page}")

        try:
            r = requests.get(url, headers=HEADERS, timeout=10)

            # ✔ RELATIVE LINKLER
            links = re.findall(r'<a href="(/[^"]+-izle/)"', r.text)

            for l in links:
                episodes.add(BASE_URL + l)

            time.sleep(0.05)

        except Exception as e:
            print(f"[HATA] {page}: {e}")

    return list(episodes)


# -------------------------------------------------
# MAIN
# -------------------------------------------------
def main():
    out = "dizigom-tum-bolumler.m3u"
    print("\nBOT BAŞLADI\n")

    episodes = get_all_episode_links(4521)
    print(f"\nTOPLAM BÖLÜM: {len(episodes)}\n")

    if not episodes:
        print("❌ HİÇ BÖLÜM BULUNAMADI – ÇIKIYOR")
        return

    with open(out, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")

        for ep in episodes:
            print(f"[BÖLÜM] {ep}")
            try:
                r = requests.get(ep, headers=HEADERS, timeout=10)

                title = re.search(r'<title>(.*?) (?:İzle|izle)', r.text)
                name = title.group(1).strip() if title else "Bilinmeyen"

                logo = ""
                img = re.search(r'"image":"(.*?)"', r.text)
                if img:
                    logo = img.group(1).replace("\\/", "/")

                embed = get_embed_from_episode(ep)
                if not embed:
                    print("  ❌ EMBED YOK")
                    continue

                m3u8 = get_m3u8_link(embed)
                if not m3u8:
                    print("  ❌ M3U8 YOK")
                    continue

                f.write(
                    f'#EXTINF:-1 tvg-name="TR: {name}" tvg-logo="{logo}" group-title="Dizigom",TR: {name}\n'
                )
                f.write(m3u8 + "\n")
                f.flush()

                print("  ✅ EKLENDİ")
                time.sleep(0.1)

            except Exception as e:
                print(f"  ⚠ HATA: {e}")

    print("\n✔ BİTTİ – M3U HAZIR")


if __name__ == "__main__":
    main()

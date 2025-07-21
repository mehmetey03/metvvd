import asyncio
from playwright.async_api import async_playwright
import requests
from bs4 import BeautifulSoup
import re

BASE_URL = "https://thetvapp.to"
CHANNELS_PAGE = BASE_URL + "/tv/"

async def sniff_m3u8_after_click(page, url):
    m3u8_link = None

    async def handle_response(response):
        nonlocal m3u8_link
        if ".m3u8" in response.url and "token=" in response.url and not m3u8_link:
            print(f" m3u8 bulundu: {response.url}")
            m3u8_link = response.url

    page.on("response", handle_response)

    await page.goto(url, timeout=30000)
    await page.wait_for_timeout(3000)

    try:
        
        await page.click("#loadVideoHD")
        print(f"🖱️ {url} sayfasında HD stream seçildi.")
        await page.wait_for_timeout(1000)

        
        await page.click("#loadVideoBtn")
        print(f" {url} sayfasında başlat tuşuna tıklandı")
    except Exception as e:
        print(f" {url} sayfasında tıklama başarısız: {e}")
        return None

    await page.wait_for_timeout(7000)
    return m3u8_link


def get_all_channels():
    print(" Kanal listesi çekiliyor")
    r = requests.get(CHANNELS_PAGE, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(r.text, "html.parser")

    channels = []
    for a in soup.select("a.list-group-item"):
        href = a.get("href")
        name = a.text.strip()
        full_url = f"{BASE_URL}{href}" if href else BASE_URL
        channels.append((name, full_url))
    print(f" Toplam {len(channels)} kanal bulundu.")
    return channels

async def main():
    channels = get_all_channels()
    results = []

    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        for name, url in channels:
            print(f"\n İşleniyor: {name} - {url}")
            m3u8 = await sniff_m3u8_after_click(page, url)
            if m3u8:
                results.append((name, m3u8))
            else:
                print(f" {name} için m3u8 bulunamadı")

        await browser.close()

    
    with open("tvapp.m3u", "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n\n")
        for name, link in results:
            f.write(f'#EXTINF:-1,{name}\n')
            f.write(f"{link}\n\n")
    print("\n tvapp.m3u oluştu")

if __name__ == "__main__":
    asyncio.run(main())

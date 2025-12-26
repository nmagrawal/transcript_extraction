# app/scraper.py
import asyncio
from playwright.async_api import Page, async_playwright
from .utils import parse_vtt
import os
import httpx

async def fetch_youtube_transcript(video_id: str):
    """
    Calls the RapidAPI yt-api.p.rapidapi.com/subtitles endpoint to get a transcript for a YouTube video.
    """
    import requests

    api_key = os.getenv("RAPIDAPI_KEY")
    if not api_key:
        raise ValueError("RAPIDAPI_KEY environment variable not set.")

    url = "https://yt-api.p.rapidapi.com/subtitles"
    querystring = {"id": video_id}
    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": "yt-api.p.rapidapi.com"
    }

    response = requests.get(url, headers=headers, params=querystring, timeout=30)
    response.raise_for_status()
    data = response.json()

    # Find the English or English (auto-generated) subtitle
    subtitles = data.get("subtitles", [])
    if not isinstance(subtitles, list):
        raise TypeError("Expected a list in 'subtitles' from the YouTube API.")

    subtitle_url = None
    for item in subtitles:
        lang = item.get("languageName", "")
        if lang == "English" or lang == "English (auto-generated)":
            subtitle_url = item.get("url")
            break

    if not subtitle_url:
        raise ValueError("No English subtitles found for this video.")

    # Fetch the transcript from the subtitle URL (usually returns .vtt)
    vtt_response = requests.get(subtitle_url, timeout=30)
    vtt_response.raise_for_status()
    vtt_text = vtt_response.text

    # Use parse_vtt from utils to convert VTT to plain text
    from .utils import parse_vtt
    return parse_vtt(vtt_text)

async def handle_granicus_url(page: 'Page'):
    """Performs the UI trigger sequence for Granicus (Dublin) pages."""
    print("  - Detected Granicus platform. Executing trigger sequence...")
#    await page.screenshot(path='/app/screenshots/before_click.png')
    await page.locator(".flowplayer").hover(timeout=10000)


    element = page.locator(".fp-menu").get_by_text("On", exact=True)
    await element.scroll_into_view_if_needed(timeout=10000)
    await element.click(force=True)
#    await page.screenshot(path='/app/screenshots/after_click.png')


async def handle_viebit_url(page: 'Page'):
    """Performs the UI trigger sequence for Viebit (Fremont) pages."""
    print("  - Detected Viebit platform. Executing trigger sequence...")
    await page.locator(".vjs-big-play-button").click(timeout=10000)
    await page.locator(".vjs-play-control").click(timeout=10000)
    await page.wait_for_timeout(500)
    await page.locator("button.vjs-subs-caps-button").click(timeout=10000)
    await page.locator('.vjs-menu-item:has-text("English")').click(timeout=10000)

async def fetch_transcript_for_url(url: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, channel="chrome")
        context = await browser.new_context(viewport={"width": 1280, "height": 800})  # Set a standard viewport size
        page = await context.new_page()
        vtt_future = asyncio.Future()

        async def handle_response(response):
            if ".vtt" in response.url and not vtt_future.done():
                try: vtt_future.set_result(await response.text())
                except Exception as e:
                    if not vtt_future.done(): vtt_future.set_exception(e)
        
        page.on("response", handle_response)
        
        try:
            await page.goto(url, wait_until="load", timeout=45000)
            if "granicus.com" in url:
                await handle_granicus_url(page)
            elif "viebit.com" in url:
                await handle_viebit_url(page)
            else:
                raise ValueError("Unknown platform. Could not process URL.")
            
            vtt_content = await asyncio.wait_for(vtt_future, timeout=20)
            return parse_vtt(vtt_content)
        finally:
            await browser.close()
 
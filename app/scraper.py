# app/scraper.py
import asyncio
from playwright.async_api import Page, async_playwright
from .utils import parse_vtt
import os
import httpx

async def fetch_youtube_transcript(video_id: str):
    """
    Calls the RapidAPI service to get a transcript for a YouTube video.
    """
    api_key = os.getenv("RAPIDAPI_KEY")
    if not api_key:
        raise ValueError("RAPIDAPI_KEY environment variable not set.")

    api_url = f"https://youtube-captions.p.rapidapi.com/transcript?videoId={video_id}"
    headers = {
        "x-rapidapi-host": "youtube-captions.p.rapidapi.com",
        "x-rapidapi-key": api_key,
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(api_url, headers=headers, timeout=30.0)
        # Raise an exception for bad status codes (4xx or 5xx)
        response.raise_for_status() 
        
        data = response.json()

        # Assuming the API returns a list of caption segments, each with a 'text' key.
        # We join them together to form the full transcript.
        if not isinstance(data, list):
            raise TypeError("Expected a list of captions from the YouTube API.")
        
        transcript_lines = [item.get("text", "") for item in data]
        return "\n".join(transcript_lines)

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
 
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

    # Fetch the transcript from the subtitle URL (can be .vtt or .xml)
    vtt_response = requests.get(subtitle_url, timeout=30)
    vtt_response.raise_for_status()
    content_type = vtt_response.headers.get('Content-Type', '')
    vtt_text = vtt_response.text

    # If it's a VTT file, use parse_vtt; if XML, parse XML to plain text
    if subtitle_url.endswith('.vtt') or 'vtt' in content_type:
        from .utils import parse_vtt
        return parse_vtt(vtt_text)
    elif subtitle_url.endswith('.xml') or 'xml' in content_type or vtt_text.strip().startswith('<?xml'):
        # Parse XML and extract readable text
        import xml.etree.ElementTree as ET
        try:
            root = ET.fromstring(vtt_text)
            # YouTube XML subtitles: <transcript><text start="..." dur="...">...</text>...</transcript>
            lines = []
            for text_elem in root.findall('.//text'):
                # Unescape HTML entities
                import html
                line = html.unescape(text_elem.text or '')
                lines.append(line.strip())
            return '\n'.join(lines)
        except Exception as e:
            raise ValueError(f"Failed to parse XML subtitles: {e}")
    else:
        raise ValueError("Unknown subtitle format. Cannot parse transcript.")

async def handle_granicus_url(page: 'Page'):
    """Performs the UI trigger sequence for Granicus (Dublin) pages."""
    print("  - Detected Granicus platform. Executing trigger sequence...")
    await page.locator(".flowplayer").hover(timeout=10000)
    element = page.locator(".fp-menu").get_by_text("On", exact=True)
    await element.scroll_into_view_if_needed(timeout=10000)
    await element.click(force=True)

async def handle_vimeo_url(page: 'Page'):
    """Performs the UI trigger sequence for Vimeo pages."""
    print("  - Detected Vimeo platform. Executing trigger sequence...")
    # Hover and click play button first
    play_button = page.locator('button[data-play-button="true"]')
    await play_button.scroll_into_view_if_needed(timeout=10000)
    await play_button.click(force=True)
    # Then click the CC (captions) button
    cc_button = page.locator('button[data-cc-button="true"]')
    await cc_button.scroll_into_view_if_needed(timeout=10000)
    await cc_button.click(force=True)


async def fetch_transcript_for_url(url: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, channel="chrome")
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
            await page.goto(url, wait_until="load", timeout=3500)
            if "granicus.com" in url:
                await handle_granicus_url(page)
            elif "vimeo.com" in url:
                await handle_vimeo_url(page)
            
            vtt_content = await asyncio.wait_for(vtt_future, timeout=20)
            return parse_vtt(vtt_content)
        finally:
            await browser.close()
import asyncio
import re
from pathlib import Path
from playwright.async_api import Page, async_playwright, TimeoutError

# --- Configuration ---
URL_FILE = "videos.txt"
OUTPUT_DIR = "transcripts"
BROWSER_TO_USE = "chrome"

# --- Shared Utility Functions ---

def parse_vtt(vtt_content: str) -> str:
    """
    Parses raw VTT content to extract clean subtitle text.
    This version is robust enough for both platforms.
    """
    lines = vtt_content.strip().split('\n')
    transcript_lines = []
    seen_lines = set()

    for line in lines:
        if not line.strip() or "WEBVTT" in line or "-->" in line or line.strip().isdigit():
            continue
        
        # Clean announcer tags from Granicus and extra whitespace
        cleaned_line = re.sub(r'>>\s*', '', line).strip()
        
        if cleaned_line and cleaned_line not in seen_lines:
            transcript_lines.append(cleaned_line)
            seen_lines.add(cleaned_line)
            
    return "\n".join(transcript_lines)

def sanitize_filename(name: str) -> str:
    """Removes characters that are invalid in filenames."""
    sanitized = re.sub(r'[\\/*?:"<>|]', "", name).strip()
    return (sanitized[:150] + '...') if len(sanitized) > 150 else sanitized

# --- Platform-Specific Handlers ---

async def handle_granicus_url(page: 'Page'):
    """Performs the UI trigger sequence for Granicus (Dublin) pages."""
    print("  - Detected Granicus platform. Executing trigger sequence...")
    player_locator = page.locator(".flowplayer")
    cc_button_locator = page.locator(".fp-cc").first

    await player_locator.click(timeout=10000)
    await page.wait_for_timeout(500)
    await player_locator.click(timeout=10000)
    await page.wait_for_timeout(500)
    await player_locator.hover(timeout=5000)
    await cc_button_locator.click(timeout=10000)
    await page.wait_for_timeout(500)
    await page.locator(".fp-menu").get_by_text("On", exact=True).click(timeout=10000)

async def handle_viebit_url(page: 'Page'):
    """Performs the UI trigger sequence for Viebit (Fremont) pages."""
    print("  - Detected Viebit platform. Executing trigger sequence...")
    await page.locator(".vjs-big-play-button").click(timeout=20000)
    await page.locator(".vjs-play-control").click(timeout=10000)
    await page.wait_for_timeout(500)
    await page.locator("button.vjs-subs-caps-button").click(timeout=10000)
    await page.locator('.vjs-menu-item:has-text("English")').click(timeout=10000)

# --- Main Processing Logic ---

async def process_url(url: str):
    """
    Identifies the platform from the URL and runs the appropriate logic
    to capture the transcript via network interception.
    """
    print(f"\n▶️ Processing: {url}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, channel=BROWSER_TO_USE)
        page = await browser.new_page()

        vtt_future = asyncio.Future()

        async def handle_response(response):
            if ".vtt" in response.url and not vtt_future.done():
                print(f"  - ✅ Intercepted VTT file: {response.url}")
                try:
                    vtt_future.set_result(await response.text())
                except Exception as e:
                    vtt_future.set_exception(e)

        page.on("response", handle_response)

        try:
            print("  - Navigating and listening for network traffic...")
            await page.goto(url, wait_until="load", timeout=45000)

            # --- URL Dispatcher ---
            if "granicus.com" in url:
                await handle_granicus_url(page)
            elif "viebit.com" in url:
                await handle_viebit_url(page)
            else:
                print(f"  - ❌ FAILED: Unknown platform. Could not process URL.")
                await browser.close()
                return

            print("  - Waiting for VTT file to be captured by network listener...")
            vtt_content = await asyncio.wait_for(vtt_future, timeout=20)
            
            print("  - VTT content captured successfully!")

            video_title = await page.title()
            sanitized_title = sanitize_filename(video_title)
            output_file = Path(OUTPUT_DIR) / f"{sanitized_title}.txt"

            if output_file.exists():
                print(f"  - Transcript file '{output_file}' already exists. Overwriting.")

            transcript = parse_vtt(vtt_content)
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(transcript)
            print(f"✅ Transcript saved to '{output_file}'")

        except asyncio.TimeoutError:
            print("  - ❌ FAILED: Timed out waiting for VTT file.")
        except Exception as e:
            print(f"  - ❌ An unexpected error occurred: {e}")
        finally:
            await browser.close()


def main():
    Path(OUTPUT_DIR).mkdir(exist_ok=True)
    if not Path(URL_FILE).exists():
        print(f"Error: URL file '{URL_FILE}' not found.")
        with open(URL_FILE, "w") as f:
            f.write("# Please add one video URL per line from a supported platform (Granicus, Viebit)\n")
        print(f"A new file '{URL_FILE}' has been created for you.")
        return
        
    with open(URL_FILE, "r") as f:
        urls = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    if not urls:
        print(f"The file '{URL_FILE}' is empty. Please add video URLs.")
        return

    # Use a single asyncio.run() call for the entire list of URLs
    async def run_all():
        for url in urls:
            await process_url(url)

    asyncio.run(run_all())

if __name__ == "__main__":
    main()
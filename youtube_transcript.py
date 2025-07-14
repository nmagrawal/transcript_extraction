import asyncio
import re
from pathlib import Path
from playwright.async_api import async_playwright, TimeoutError

# --- Configuration ---
OUTPUT_DIR = "youtube_transcripts_playwright"
BROWSER_TO_USE = "chrome"

def sanitize_filename(name: str) -> str:
    """Removes characters that are invalid in filenames."""
    sanitized = re.sub(r'[\\/*?:"<>|]', "", name).strip()
    return (sanitized[:150] + '...') if len(sanitized) > 150 else sanitized

async def get_youtube_transcript_playwright(url: str):
    """
    Uses Playwright to handle YouTube video layouts by targeting
    only the visible, clickable elements.
    """
    print("-" * 50)
    print(f"▶️ Processing with Playwright: {url}")

    async with async_playwright() as p:
        browser = None
        try:
            browser = await p.chromium.launch(headless=True, channel=BROWSER_TO_USE)
            page = await browser.new_page()
            
            # This handles the "Accept cookies" pop-up that can appear.
            # Using get_by_role is very robust.
            try:
                print("  - Navigating to page...")
                await page.goto(url, wait_until="domcontentloaded", timeout=45000)
                
                # Check for and click the cookie consent button with a short timeout
                accept_button = page.get_by_role("button", name="Accept all", exact=True)
                await accept_button.click(timeout=5000)
                print("  - Accepted cookie pop-up.")
            except TimeoutError:
                # This is the expected outcome if no cookie pop-up appears
                print("  - No cookie pop-up found, continuing...")
            except Exception as e:
                print(f"  - A minor, non-blocking error occurred during cookie check: {e}")

            # Wait for the description area to be stable
            await page.wait_for_selector("#description-inline-expander", timeout=15000)

            video_title = await page.title()
            sanitized_title = sanitize_filename(video_title)
            
            Path(OUTPUT_DIR).mkdir(exist_ok=True)
            output_file = Path(OUTPUT_DIR) / f"{sanitized_title}.txt"

            if output_file.exists():
                print(f"  - ✅ INFO: Transcript for '{video_title}' already exists. Skipping.")
                await browser.close()
                return

            print("  - Looking for transcript button...")
            
            # --- THE FINAL FIX IS HERE ---
            # 1. Target the button with id="expand" that is VISIBLE.
            #    Playwright's .locator() automatically prefers visible elements when multiple match.
            #    We can make this even more explicit.
            print("  - Step 1: Clicking visible '#expand' button...")
            await page.locator('#expand:visible').first.click(timeout=15000)

            # 2. Click the "Show transcript" button.
            print("  - Step 2: Clicking 'Show transcript' button...")
            await page.get_by_role("button", name="Show transcript", exact=True).click()

            print("  - Waiting for transcript to load...")
            await page.wait_for_selector('ytd-transcript-segment-renderer', timeout=15000)

            print("  - Scraping transcript text from page...")
            lines_locator = page.locator("yt-formatted-string.ytd-transcript-segment-renderer")
            all_lines = await lines_locator.all_inner_texts()

            if not all_lines:
                print(f"  - ❌ ERROR: Transcript pane was opened, but no text was found.")
                await browser.close()
                return

            full_transcript = " ".join([line.strip() for line in all_lines])

            with open(output_file, "w", encoding="utf-8") as f:
                f.write(full_transcript)
            
            print(f"  - ✅ SUCCESS! Transcript for '{video_title}' saved to '{output_file}'")
            
        except TimeoutError:
            print("  - ❌ ERROR: Timed out. Could not find a required button ('#expand' or 'Show transcript').")
            print("  - This usually means the video does not have a transcript or the page layout has changed.")
        except Exception as e:
            print(f"  - ❌ An unexpected error occurred: {e}")
        finally:
            if browser and browser.is_connected():
                await browser.close()


if __name__ == '__main__':
    print("--- Playwright YouTube Transcript Downloader ---")
    print("Enter a YouTube video URL to get its transcript.")
    print("Type 'exit' or 'quit' to close the program.")
    
    while True:
        user_input = input("\nEnter YouTube URL: ")

        if user_input.lower() in ['exit', 'quit', 'q']:
            print("Exiting program. Goodbye!")
            break
        
        if user_input:
            asyncio.run(get_youtube_transcript_playwright(user_input))
        else:
            print("Please enter a URL.")
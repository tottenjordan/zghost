"""Monitor GE browser E2E test — send messages and capture screenshots.

This script connects to the running CDP Chrome (port 9222) and:
1. Sends follow-up messages to advance the pipeline
2. Takes screenshots at intervals to capture thinking, images, video, focus group, PDF
3. Detects pipeline stages from the chat content

Usage:
  DISPLAY=:20 python tests/ge_browser_monitor.py
"""
import asyncio
import os
import sys
import time
from datetime import datetime
from pathlib import Path

SCREENSHOT_DIR = Path("demo_screenshots/ge_browser_e2e")
CDP_URL = "http://localhost:9222"
MAX_WAVES = 45
SCREENSHOT_INTERVAL = 20  # seconds between screenshots


async def send_message(page, message):
    """Type and send a message in the GE chat."""
    chat_input = None
    for sel in ['div[contenteditable="true"]', 'textarea']:
        try:
            el = await page.wait_for_selector(sel, timeout=5000)
            if el and await el.is_visible():
                chat_input = el
                break
        except:
            continue

    if not chat_input:
        print("  Could not find chat input!")
        return False

    await chat_input.click()
    await page.wait_for_timeout(300)
    await page.keyboard.type(message, delay=5)
    await page.wait_for_timeout(500)
    await page.keyboard.press("Enter")
    print(f"  SENT: {message[:80]}")
    return True


async def take_screenshot(page, name):
    """Take a screenshot with timestamp."""
    ts = datetime.now().strftime("%H%M%S")
    path = SCREENSHOT_DIR / f"{name}_{ts}.png"
    try:
        await page.screenshot(path=str(path), full_page=False)
        return str(path)
    except Exception as e:
        print(f"  Screenshot error: {e}")
        return None


async def check_page_content(page):
    """Check what's visible in the chat — detect pipeline stages."""
    try:
        content = await page.evaluate('''() => {
            const text = document.body.innerText;
            const images = document.querySelectorAll('img:not([src*="avatar"]):not([alt=""])');
            const videos = document.querySelectorAll('video');
            const pdfs = document.querySelectorAll('a[href*=".pdf"]');
            const thinking = document.querySelectorAll('[class*="thinking"], [class*="thought"], [data-thinking]');
            const loading = document.querySelectorAll('[class*="loading"], [class*="spinner"], [class*="progress"]');
            const chips = document.querySelectorAll('[class*="chip"], [class*="status"]');

            // Check for our pipeline keywords
            const hasResearch = text.includes("research") || text.includes("Research");
            const hasImages = images.length > 1;  // more than just the agent icon
            const hasVideo = videos.length > 0 || text.includes("commercial") || text.includes("video");
            const hasFocusGroup = text.includes("focus group") || text.includes("Focus Group");
            const hasPDF = pdfs.length > 0 || text.includes("PDF") || text.includes("campaign brief");
            const isLoading = loading.length > 0;
            const hasThinking = thinking.length > 0 || text.includes("Thinking");

            return {
                textLength: text.length,
                imageCount: images.length,
                videoCount: videos.length,
                pdfCount: pdfs.length,
                chipCount: chips.length,
                hasResearch, hasImages, hasVideo, hasFocusGroup, hasPDF,
                isLoading, hasThinking,
                lastLine: text.split("\\n").filter(l => l.trim()).slice(-3).join(" | ")
            };
        }''')
        return content
    except Exception as e:
        print(f"  Content check error: {e}")
        return {}


async def wait_for_response(page, timeout_s=180):
    """Wait for the agent to finish responding (no more loading indicators)."""
    start = time.time()
    was_loading = False
    idle_count = 0

    while time.time() - start < timeout_s:
        content = await check_page_content(page)
        is_loading = content.get("isLoading", False)

        if is_loading:
            was_loading = True
            idle_count = 0
        else:
            if was_loading:
                idle_count += 1
                if idle_count >= 3:  # 3 consecutive non-loading checks
                    return True
            else:
                idle_count += 1
                if idle_count >= 6:  # If never loading, wait a bit
                    return True

        await asyncio.sleep(5)

    return False


async def scroll_to_bottom(page):
    """Scroll to the bottom of the chat."""
    await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
    await page.wait_for_timeout(500)


async def run_monitor():
    from playwright.async_api import async_playwright

    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    start_time = time.time()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    print(f"\n{'#'*60}")
    print(f"GE BROWSER MONITOR — {timestamp}")
    print(f"{'#'*60}")

    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(CDP_URL)
        context = browser.contexts[0]
        page = context.pages[0]
        await page.set_viewport_size({"width": 1920, "height": 1080})

        # Take initial screenshot
        ss = await take_screenshot(page, "monitor_start")
        print(f"  Initial: {ss}")

        # Check current state
        content = await check_page_content(page)
        print(f"  Content: images={content.get('imageCount', 0)}, videos={content.get('videoCount', 0)}")
        print(f"  Last: {content.get('lastLine', '')[:120]}")

        # Message sequence to drive the pipeline
        messages = [
            "Key selling points: New Hibiscus Scent, Plant-based formula, 2x cleaning power, Biodegradable packaging, Fresh floral fragrance that lasts. Trend: Sustainable Laundry + Eco Cleaning Hacks on YouTube. Please select trend 1 for both search and YouTube trends and proceed with the full pipeline in autopilot mode.",
        ]

        # Send the first message (selling points + proceed)
        print(f"\n{'='*60}")
        print("Phase 1: Send selling points and proceed")
        print(f"{'='*60}")

        for msg in messages:
            await send_message(page, msg)
            await page.wait_for_timeout(3000)

        # Now monitor the pipeline — take screenshots and send "continue" when idle
        print(f"\n{'='*60}")
        print("Phase 2: Monitor pipeline (screenshots + continue)")
        print(f"{'='*60}")

        screenshot_count = 0
        continue_count = 0
        seen_stages = set()

        for wave in range(MAX_WAVES):
            elapsed = (time.time() - start_time) / 60
            print(f"\n--- Wave {wave+1} ({elapsed:.1f} min) ---")

            # Wait for response
            print("  Waiting for response...")
            await wait_for_response(page, timeout_s=120)

            # Scroll down and take screenshot
            await scroll_to_bottom(page)
            await page.wait_for_timeout(1000)

            content = await check_page_content(page)
            screenshot_count += 1

            # Determine stage
            stages = []
            if content.get("hasThinking"):
                stages.append("THINKING")
            if content.get("hasResearch"):
                stages.append("RESEARCH")
            if content.get("hasImages"):
                stages.append("IMAGES")
            if content.get("hasVideo"):
                stages.append("VIDEO")
            if content.get("hasFocusGroup"):
                stages.append("FOCUS_GROUP")
            if content.get("hasPDF"):
                stages.append("PDF")

            stage_str = "_".join(stages) if stages else "working"
            new_stages = set(stages) - seen_stages
            seen_stages.update(stages)

            print(f"  Stages: {stages}")
            print(f"  New: {new_stages}")
            print(f"  Images: {content.get('imageCount', 0)} | Videos: {content.get('videoCount', 0)} | PDFs: {content.get('pdfCount', 0)}")
            print(f"  Last text: {content.get('lastLine', '')[:120]}")

            # Take screenshot (always)
            ss_name = f"wave_{wave+1:02d}_{stage_str}"
            ss = await take_screenshot(page, ss_name)
            if ss:
                print(f"  Screenshot: {ss}")

            # Extra screenshot for new stages
            if new_stages:
                for stage in new_stages:
                    ss = await take_screenshot(page, f"STAGE_{stage}")
                    print(f"  Stage screenshot: {ss}")

            # Check completion
            if content.get("hasPDF") and content.get("hasFocusGroup"):
                print(f"\n  PIPELINE COMPLETE! All gates met.")
                # Take final full-page screenshot
                await page.screenshot(
                    path=str(SCREENSHOT_DIR / f"FINAL_COMPLETE_{timestamp}.png"),
                    full_page=True
                )
                print(f"  Final screenshot saved")
                break

            # Send "continue" to advance pipeline
            if not content.get("isLoading"):
                continue_count += 1
                await send_message(page, "continue")
                await page.wait_for_timeout(5000)

            # Safety: if we've sent many continues with no progress, wait longer
            if continue_count > 5 and not new_stages:
                print("  Waiting 30s for pipeline to process...")
                await page.wait_for_timeout(30000)

        # --- Final results ---
        elapsed = (time.time() - start_time) / 60
        print(f"\n{'='*60}")
        print(f"MONITOR COMPLETE — {elapsed:.1f} minutes")
        print(f"Screenshots: {screenshot_count}")
        print(f"Continues sent: {continue_count}")
        print(f"Stages seen: {seen_stages}")
        print(f"Directory: {SCREENSHOT_DIR}")
        print(f"{'='*60}")

        # Take final screenshots at different scroll positions
        for scroll_pct in [0, 25, 50, 75, 100]:
            await page.evaluate(f'window.scrollTo(0, document.body.scrollHeight * {scroll_pct/100})')
            await page.wait_for_timeout(500)
            await take_screenshot(page, f"final_scroll_{scroll_pct}")

        # Quality gates
        final_content = await check_page_content(page)
        gates = {
            "research": final_content.get("hasResearch", False),
            "images": final_content.get("imageCount", 0) > 1,
            "video/commercial": final_content.get("hasVideo", False),
            "focus_group": final_content.get("hasFocusGroup", False),
            "pdf_brief": final_content.get("hasPDF", False),
        }
        print(f"\nQUALITY GATES:")
        for gate, passed in gates.items():
            print(f"  {gate}: {'PASS' if passed else 'FAIL'}")
        print(f"OVERALL: {'PASS' if all(gates.values()) else 'FAIL'}")


if __name__ == "__main__":
    asyncio.run(run_monitor())

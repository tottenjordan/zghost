"""GE Browser Autopilot — drive a full pipeline in Gemini Enterprise UI.

Connects to CDP Chrome (port 9222), navigates to GE, starts a new chat
with campaign details + autopilot mode, then monitors with screenshots.

Usage:
  DISPLAY=:20 /usr/local/google/home/jwortz/miniconda3/bin/python -u tests/ge_browser_autopilot.py
"""
import asyncio
import time
from datetime import datetime
from pathlib import Path

SS_DIR = Path("demo_screenshots/ge_browser_autopilot")
CDP_URL = "http://localhost:9222"
GE_DASHBOARD_URL = "https://console.cloud.google.com/gemini-enterprise/locations/global/engines/gemini-enterprise-17634901_1763490144996/overview/dashboard?project=wortz-project-352116"
GE_CHAT_URL = "https://vertexaisearch.cloud.google.com/home/cid/c4da98d6-1b97-4e31-bb6a-ba979e363c26?hl=en_US"

CAMPAIGN_MESSAGE = """Create a full marketing campaign for Tide Fabric Softener with Hibiscus Scent.

Brand: Tide
Product: Tide Fabric Softener with Hibiscus Scent
Target Audience: Gen Z eco-conscious consumers
Key Selling Points: New Hibiscus Scent, Plant-based formula, 2x cleaning power, Biodegradable packaging

Run in autopilot mode — auto-select trend 1 for both search and YouTube trends, then proceed through the full pipeline: research, ad creative, image generation, 15s video commercial, focus group evaluation, and final PDF campaign brief."""

# JS to check page content
CHECK_CONTENT_JS = """() => {
    const text = document.body.innerText.toLowerCase();
    const imgs = document.querySelectorAll('img');
    const bigImgs = [];
    imgs.forEach(img => {
        if (img.width > 100 && !img.src.includes('avatar') && !img.src.includes('icon')) {
            bigImgs.push(img.src.substring(0, 80));
        }
    });
    return {
        hasResearch: text.includes('research report') || text.includes('cited report') || text.includes('market research'),
        hasAdCopy: text.includes('ad copy') || text.includes('ad creative') || text.includes('headline'),
        hasImages: bigImgs.length > 0,
        imageCount: bigImgs.length,
        hasVideo: text.includes('commercial') || text.includes('veo') || text.includes('video gen'),
        hasFocusGroup: text.includes('focus group') || text.includes('panelist'),
        hasPDF: text.includes('pdf') || text.includes('campaign brief') || text.includes('final report'),
        hasThinking: text.includes('thinking') || document.querySelectorAll('[class*="think"]').length > 0,
        hasComplete: text.includes('pipeline complete') || text.includes('campaign is complete') || text.includes('all stages complete'),
        hasTrends: text.includes('trending') || text.includes('search trend') || text.includes('youtube trend'),
        hasAutopilot: text.includes('autopilot') || text.includes('auto-select'),
        textLength: text.length,
        lastLines: text.split('\\n').filter(l => l.trim()).slice(-5).join(' | ').substring(0, 300),
    };
}"""

# JS to click continue button
CLICK_CONTINUE_JS = """() => {
    const walker = document.createTreeWalker(
        document.body, NodeFilter.SHOW_TEXT, null, false
    );
    while (walker.nextNode()) {
        if (walker.currentNode.textContent.trim().toLowerCase() === 'continue') {
            const el = walker.currentNode.parentElement;
            const btn = el.closest('button') || el;
            btn.click();
            return true;
        }
    }
    return false;
}"""

# JS to type in the GE chat input
SEND_MESSAGE_JS = """(msg) => {
    // Try contenteditable div first, then textarea
    const els = document.querySelectorAll('div[contenteditable="true"], textarea');
    for (const el of els) {
        if (el.offsetParent !== null) {  // visible
            el.focus();
            el.textContent = msg;
            el.dispatchEvent(new Event('input', {bubbles: true}));
            return true;
        }
    }
    return false;
}"""


async def take_screenshot(page, name):
    ts = datetime.now().strftime("%H%M%S")
    path = SS_DIR / f"{name}_{ts}.png"
    try:
        await page.screenshot(path=str(path))
        print(f"  Screenshot: {path.name}", flush=True)
        return str(path)
    except Exception as e:
        print(f"  Screenshot error: {e}", flush=True)
        return None


async def run():
    from playwright.async_api import async_playwright

    SS_DIR.mkdir(parents=True, exist_ok=True)
    start = time.time()

    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(CDP_URL)
        context = browser.contexts[0]
        page = context.pages[0]
        await page.set_viewport_size({"width": 1920, "height": 1080})

        # Navigate directly to GE chat page
        print(f"Navigating to GE chat...", flush=True)
        await page.goto(GE_CHAT_URL, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(8000)
        await take_screenshot(page, "01_chat_page")

        # Start a new chat
        print(f"Starting new chat...", flush=True)
        for selector in [
            'button:has-text("New chat")',
            'text="New chat"',
            'button[aria-label*="new"]',
            'button[aria-label*="New"]',
        ]:
            try:
                el = await page.wait_for_selector(selector, timeout=3000)
                if el and await el.is_visible():
                    await el.click()
                    print(f"  Started new chat: {selector}", flush=True)
                    await page.wait_for_timeout(3000)
                    break
            except:
                continue

        await take_screenshot(page, "02_new_chat")

        # Send the campaign message
        print(f"\nSending campaign message...", flush=True)

        # Try to find and use the chat input
        chat_sent = False
        for sel in ['div[contenteditable="true"]', 'textarea', 'input[type="text"]']:
            try:
                el = await page.wait_for_selector(sel, timeout=5000)
                if el and await el.is_visible():
                    await el.click()
                    await page.wait_for_timeout(500)
                    # Type the message
                    await page.keyboard.type(CAMPAIGN_MESSAGE, delay=5)
                    await page.wait_for_timeout(500)
                    await page.keyboard.press("Enter")
                    chat_sent = True
                    print(f"  Message sent via {sel}", flush=True)
                    break
            except:
                continue

        if not chat_sent:
            print("  Could not find chat input — trying JS fallback", flush=True)
            try:
                await page.evaluate(SEND_MESSAGE_JS, CAMPAIGN_MESSAGE)
                await page.keyboard.press("Enter")
                chat_sent = True
            except Exception as e:
                print(f"  JS fallback failed: {e}", flush=True)

        await page.wait_for_timeout(3000)
        await take_screenshot(page, "03_message_sent")

        # Monitor pipeline with screenshots
        print(f"\n{'='*60}")
        print("Monitoring pipeline progression...")
        print(f"{'='*60}", flush=True)

        seen_stages = set()
        for wave in range(45):
            elapsed = (time.time() - start) / 60
            print(f"\n=== Wave {wave+1} ({elapsed:.1f} min) ===", flush=True)

            # Scroll to bottom
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(2000)

            # Take screenshot
            await take_screenshot(page, f"wave_{wave+1:02d}")

            # Check content
            try:
                info = await page.evaluate(CHECK_CONTENT_JS)
            except Exception as e:
                print(f"  Check error: {e}", flush=True)
                info = {}

            stages = []
            if info.get("hasTrends"):
                stages.append("TRENDS")
            if info.get("hasResearch"):
                stages.append("RESEARCH")
            if info.get("hasAdCopy"):
                stages.append("AD_COPY")
            if info.get("hasImages"):
                stages.append(f"IMAGES({info.get('imageCount', 0)})")
            if info.get("hasVideo"):
                stages.append("VIDEO")
            if info.get("hasFocusGroup"):
                stages.append("FOCUS_GROUP")
            if info.get("hasPDF"):
                stages.append("PDF")
            if info.get("hasThinking"):
                stages.append("THINKING")

            new_stages = set(stages) - seen_stages
            seen_stages.update(stages)

            print(f"  Stages: {stages}", flush=True)
            if new_stages:
                print(f"  NEW: {new_stages}", flush=True)
            print(f"  Text: {info.get('textLength', 0)} chars", flush=True)
            last = info.get("lastLines", "")
            print(f"  Last: {last[:200]}", flush=True)

            # Check completion
            if info.get("hasComplete") or (info.get("hasFocusGroup") and info.get("hasPDF")):
                print(f"\n*** PIPELINE COMPLETE! ***", flush=True)
                # Take scrolling screenshots
                height = await page.evaluate("document.body.scrollHeight")
                for pct in [0, 25, 50, 75, 100]:
                    await page.evaluate(f"window.scrollTo(0, {int(height * pct / 100)})")
                    await page.wait_for_timeout(500)
                    await take_screenshot(page, f"FINAL_scroll{pct}")
                break

            # Click continue button
            try:
                clicked = await page.evaluate(CLICK_CONTINUE_JS)
                if clicked:
                    print(f"  Clicked continue button", flush=True)
                else:
                    # Type "continue" in chat
                    for sel in ['div[contenteditable="true"]', 'textarea']:
                        try:
                            el = await page.wait_for_selector(sel, timeout=3000)
                            if el and await el.is_visible():
                                await el.click()
                                await page.keyboard.type("continue", delay=10)
                                await page.keyboard.press("Enter")
                                print(f"  Sent 'continue' via chat", flush=True)
                                break
                        except:
                            continue
            except Exception as e:
                print(f"  Continue error: {str(e)[:80]}", flush=True)

            # Wait for response
            print(f"  Waiting 30s...", flush=True)
            await page.wait_for_timeout(30000)

        elapsed = (time.time() - start) / 60
        print(f"\n=== DONE — {elapsed:.1f} minutes ===", flush=True)
        print(f"Stages seen: {seen_stages}", flush=True)
        print(f"Screenshots: {SS_DIR}", flush=True)


if __name__ == "__main__":
    asyncio.run(run())

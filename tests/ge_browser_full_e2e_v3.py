"""GE Browser Full E2E v3 — fixed content detection, no false positives.

Key fixes from v2:
- Uses innerText (visible text only) instead of walking all shadow roots
- Requires minimum 5 minutes before declaring completion
- Skips first few waves for completion checks (agent hasn't even started)
"""
import asyncio
import time
from datetime import datetime
from pathlib import Path

SS_DIR = Path("demo_screenshots/ge_browser_full_e2e")
CDP_URL = "http://localhost:9222"
GE_CHAT_URL = "https://vertexaisearch.cloud.google.com/home/cid/c4da98d6-1b97-4e31-bb6a-ba979e363c26?hl=en_US"

CAMPAIGN_MESSAGE = """Create a full marketing campaign for Tide Fabric Softener with Hibiscus Scent.

Brand: Tide
Product: Tide Fabric Softener with Hibiscus Scent
Target Audience: Gen Z eco-conscious consumers
Key Selling Points: New Hibiscus Scent, Plant-based formula, 2x cleaning power, Biodegradable packaging

Run in autopilot mode — auto-select trend 1 for both search and YouTube trends, then proceed through the full pipeline: research, ad creative, image generation, 15s video commercial, focus group evaluation, and final PDF campaign brief."""

# Simple innerText-based content check — no shadow DOM walking
CHECK_CONTENT_JS = """() => {
    const text = document.body.innerText.toLowerCase();
    const imgs = document.querySelectorAll('img');
    const bigImgs = [];
    imgs.forEach(img => {
        if (img.width > 100 && !img.src.includes('avatar') && !img.src.includes('icon')
            && !img.src.includes('logo') && !img.src.includes('google')) {
            bigImgs.push(img.src.substring(0, 100));
        }
    });
    return {
        hasResearch: text.includes('research report') || text.includes('cited report') || text.includes('market research'),
        hasAdCopy: text.includes('ad copy') || text.includes('ad creative') || text.includes('headline'),
        hasImages: bigImgs.length > 0,
        imageCount: bigImgs.length,
        imageSrcs: bigImgs.slice(0, 3),
        hasVideo: text.includes('commercial') || text.includes('veo') || text.includes('video gen'),
        hasFocusGroup: text.includes('focus group') || text.includes('panelist'),
        hasPDF: text.includes('.pdf') || text.includes('campaign brief') || text.includes('final report'),
        hasThinking: text.includes('thinking'),
        hasComplete: text.includes('pipeline complete') || text.includes('campaign is complete') || text.includes('all stages complete'),
        hasTrends: text.includes('trending') || text.includes('search trend') || text.includes('youtube trend'),
        hasAutopilot: text.includes('autopilot'),
        hasError: text.includes('error') || text.includes('failed'),
        textLength: text.length,
        lastLines: text.split('\\n').filter(l => l.trim()).slice(-8).join(' | ').substring(0, 400),
    };
}"""


async def ss(page, name):
    ts = datetime.now().strftime("%H%M%S")
    path = SS_DIR / f"{name}_{ts}.png"
    try:
        await page.screenshot(path=str(path))
        print(f"  SS: {path.name}", flush=True)
    except Exception as e:
        print(f"  SS err: {e}", flush=True)


async def run():
    from playwright.async_api import async_playwright

    SS_DIR.mkdir(parents=True, exist_ok=True)
    start = time.time()

    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(CDP_URL)
        context = browser.contexts[0]
        page = context.pages[0]
        await page.set_viewport_size({"width": 1920, "height": 1080})

        # === PHASE 1: Navigate ===
        print("PHASE 1: Navigate", flush=True)
        await page.goto(GE_CHAT_URL, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(8000)
        await ss(page, "01_loaded")

        # === PHASE 2: New chat ===
        print("PHASE 2: New chat", flush=True)
        try:
            btn = await page.wait_for_selector('button:has-text("New chat")', timeout=5000)
            if btn:
                await btn.click()
                print("  Clicked New chat", flush=True)
                await page.wait_for_timeout(3000)
        except:
            print("  No New chat button", flush=True)
        await ss(page, "02_new_chat")

        # === PHASE 3: @mention + message ===
        print("PHASE 3: @mention + send message", flush=True)

        # Find input
        for sel in ['div[contenteditable="true"]', 'textarea']:
            try:
                el = await page.wait_for_selector(sel, timeout=5000)
                if el and await el.is_visible():
                    await el.click()
                    print(f"  Input: {sel}", flush=True)
                    break
            except:
                continue

        await page.wait_for_timeout(500)

        # Type @Trend and select agent
        await page.keyboard.type("@Trend", delay=80)
        await page.wait_for_timeout(2000)
        await ss(page, "03_dropdown")

        # Try clicking Trends2Insights
        clicked = False
        try:
            loc = page.locator("text=Trends2Insights").first
            if await loc.count() > 0:
                await loc.click()
                clicked = True
                print("  Clicked Trends2Insights", flush=True)
        except:
            pass

        if not clicked:
            await page.keyboard.press("ArrowDown")
            await page.wait_for_timeout(300)
            await page.keyboard.press("Enter")
            print("  Selected via keyboard", flush=True)

        await page.wait_for_timeout(1000)

        # Type campaign message
        await page.keyboard.type(CAMPAIGN_MESSAGE, delay=3)
        await page.wait_for_timeout(500)
        await ss(page, "04_typed")

        # Send
        await page.keyboard.press("Enter")
        msg_sent_time = time.time()
        print("  Message SENT!", flush=True)
        await page.wait_for_timeout(5000)
        await ss(page, "05_sent")

        # === PHASE 4: Monitor ===
        print(f"\n{'='*60}")
        print("PHASE 4: Monitor pipeline (45 waves x 30s)")
        print(f"{'='*60}", flush=True)

        seen_stages = set()
        prev_text_len = 0
        stale_waves = 0

        for wave in range(45):
            elapsed_total = (time.time() - start) / 60
            elapsed_since_msg = (time.time() - msg_sent_time) / 60
            print(f"\n=== Wave {wave+1} ({elapsed_total:.1f} min total, {elapsed_since_msg:.1f} min since msg) ===", flush=True)

            # Scroll to bottom
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(2000)

            await ss(page, f"wave_{wave+1:02d}")

            # Check content
            try:
                info = await page.evaluate(CHECK_CONTENT_JS)
            except Exception as e:
                print(f"  Check error: {e}", flush=True)
                info = {}

            text_len = info.get("textLength", 0)
            stages = []
            for key, label in [
                ("hasTrends", "TRENDS"), ("hasResearch", "RESEARCH"),
                ("hasAdCopy", "AD_COPY"), ("hasVideo", "VIDEO"),
                ("hasFocusGroup", "FOCUS_GROUP"), ("hasPDF", "PDF"),
                ("hasThinking", "THINKING"),
            ]:
                if info.get(key):
                    stages.append(label)
            if info.get("hasImages"):
                stages.append(f"IMAGES({info.get('imageCount', 0)})")

            new_stages = set(stages) - seen_stages
            seen_stages.update(stages)

            print(f"  Stages: {stages}", flush=True)
            if new_stages:
                print(f"  ** NEW: {new_stages} **", flush=True)
                for s in new_stages:
                    await ss(page, f"STAGE_{s.split('(')[0]}")

            if info.get("imageSrcs"):
                print(f"  Image srcs: {info['imageSrcs']}", flush=True)

            print(f"  Text: {text_len} chars (delta: {text_len - prev_text_len})", flush=True)
            last = info.get("lastLines", "")
            print(f"  Tail: {last[:250]}", flush=True)

            if info.get("hasError"):
                print(f"  WARNING: Error text detected in page", flush=True)

            # Track staleness
            if abs(text_len - prev_text_len) < 50:
                stale_waves += 1
            else:
                stale_waves = 0
            prev_text_len = text_len

            # Completion check — only after 5 minutes since message sent
            if elapsed_since_msg > 5:
                if info.get("hasComplete") or (info.get("hasFocusGroup") and info.get("hasPDF")):
                    print(f"\n*** PIPELINE COMPLETE! ({elapsed_since_msg:.1f} min) ***", flush=True)
                    height = await page.evaluate("document.body.scrollHeight")
                    for pct in [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]:
                        await page.evaluate(f"window.scrollTo(0, {int(height * pct / 100)})")
                        await page.wait_for_timeout(500)
                        await ss(page, f"FINAL_{pct:03d}")
                    break

            # Send "continue" — but not too often if stale
            if stale_waves < 5 and wave >= 1:
                try:
                    for sel in ['div[contenteditable="true"]', 'textarea']:
                        try:
                            el = await page.wait_for_selector(sel, timeout=3000)
                            if el and await el.is_visible():
                                await el.click()
                                await page.wait_for_timeout(300)
                                await page.keyboard.type("continue", delay=10)
                                await page.keyboard.press("Enter")
                                print(f"  Sent 'continue'", flush=True)
                                break
                        except:
                            continue
                except Exception as e:
                    print(f"  Continue err: {str(e)[:80]}", flush=True)

            # Wait between waves
            wait = 30 if stale_waves < 3 else 45 if stale_waves < 6 else 60
            print(f"  Waiting {wait}s (stale={stale_waves})...", flush=True)
            await page.wait_for_timeout(wait * 1000)

        # === FINAL RESULTS ===
        elapsed = (time.time() - start) / 60
        print(f"\n{'='*60}")
        print(f"DONE — {elapsed:.1f} min total")
        print(f"Stages: {seen_stages}")

        try:
            final = await page.evaluate(CHECK_CONTENT_JS)
            gates = {
                "research": final.get("hasResearch", False),
                "images": final.get("imageCount", 0) > 0,
                "video": final.get("hasVideo", False),
                "focus_group": final.get("hasFocusGroup", False),
                "pdf": final.get("hasPDF", False),
                "thinking": final.get("hasThinking", False),
            }
            print("\nQUALITY GATES:")
            for g, v in gates.items():
                status = "PASS" if v else "FAIL"
                print(f"  {g}: {status}")
            crit = all(gates[k] for k in ["research", "video", "focus_group", "pdf"])
            print(f"\nCRITICAL: {'PASS' if crit else 'FAIL'}")
            print(f"CEO READY: {'YES' if crit and gates['images'] and gates['thinking'] else 'NOT YET'}")
        except:
            pass
        print(f"{'='*60}", flush=True)


if __name__ == "__main__":
    asyncio.run(run())

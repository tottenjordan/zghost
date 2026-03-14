"""GE Browser Full E2E v4 — shadow DOM innerText extraction.

Fix: Uses innerText on shadow root elements (excludes scripts).
Previous versions either couldn't see shadow DOM (v3) or pulled in JS source (v2).
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

# Walk shadow DOM using innerText on elements (not textContent — excludes script/style)
CHECK_CONTENT_JS = """() => {
    function getVisibleText(el, depth) {
        if (depth > 10) return '';
        let text = '';
        // Skip script and style tags
        const tag = el.tagName ? el.tagName.toLowerCase() : '';
        if (tag === 'script' || tag === 'style' || tag === 'noscript') return '';

        // If element has shadow root, get text from shadow root children
        if (el.shadowRoot) {
            for (const child of el.shadowRoot.children) {
                text += getVisibleText(child, depth + 1);
            }
        }
        // Get innerText from this element (only if it's a leaf or shallow)
        // Use innerText which excludes hidden/script content
        if (!el.shadowRoot && el.innerText && el.children.length < 50) {
            text += ' ' + el.innerText;
        } else if (!el.shadowRoot) {
            for (const child of el.children || []) {
                text += getVisibleText(child, depth + 1);
            }
        }
        return text;
    }

    const text = getVisibleText(document.body, 0).toLowerCase();

    // Find images across shadow roots
    function findImages(el, depth) {
        if (depth > 10) return [];
        let imgs = [];
        const tag = el.tagName ? el.tagName.toLowerCase() : '';
        if (tag === 'img' && el.width > 100
            && !el.src.includes('avatar') && !el.src.includes('icon')
            && !el.src.includes('logo') && !el.src.includes('google')
            && !el.src.includes('gstatic')) {
            imgs.push(el.src.substring(0, 120));
        }
        if (el.shadowRoot) {
            for (const child of el.shadowRoot.querySelectorAll('*')) {
                imgs = imgs.concat(findImages(child, depth + 1));
            }
        }
        for (const child of el.children || []) {
            imgs = imgs.concat(findImages(child, depth + 1));
        }
        return imgs;
    }
    const bigImgs = findImages(document.body, 0);

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
        hasStatusChips: text.includes('status') || text.includes('running'),
        textLength: text.length,
        lastChars: text.substring(Math.max(0, text.length - 400)),
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

        # === Navigate ===
        print("Navigate to GE chat", flush=True)
        await page.goto(GE_CHAT_URL, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(8000)
        await ss(page, "01_loaded")

        # === New chat ===
        print("New chat", flush=True)
        try:
            btn = await page.wait_for_selector('button:has-text("New chat")', timeout=5000)
            if btn:
                await btn.click()
                print("  Clicked New chat", flush=True)
                await page.wait_for_timeout(3000)
        except:
            print("  No New chat button", flush=True)
        await ss(page, "02_new_chat")

        # === @mention + message ===
        print("@mention + send", flush=True)
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
        await page.keyboard.type("@Trend", delay=80)
        await page.wait_for_timeout(2500)
        await ss(page, "03_dropdown")

        # Click agent from dropdown
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
            print("  Keyboard select", flush=True)

        await page.wait_for_timeout(1000)

        # Type and send
        await page.keyboard.type(CAMPAIGN_MESSAGE, delay=3)
        await page.wait_for_timeout(500)
        await ss(page, "04_typed")
        await page.keyboard.press("Enter")
        msg_time = time.time()
        print("  SENT!", flush=True)
        await page.wait_for_timeout(5000)
        await ss(page, "05_sent")

        # === Monitor ===
        print(f"\n{'='*60}")
        print("MONITORING PIPELINE")
        print(f"{'='*60}", flush=True)

        # First, do a baseline content check to measure "background" text
        try:
            baseline = await page.evaluate(CHECK_CONTENT_JS)
            baseline_len = baseline.get("textLength", 0)
            print(f"  Baseline text: {baseline_len} chars", flush=True)
        except:
            baseline_len = 0

        seen_stages = set()
        prev_text_len = baseline_len
        stale = 0

        for wave in range(45):
            elapsed = (time.time() - msg_time) / 60
            print(f"\n=== Wave {wave+1} ({elapsed:.1f} min) ===", flush=True)

            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(2000)
            await ss(page, f"wave_{wave+1:02d}")

            try:
                info = await page.evaluate(CHECK_CONTENT_JS)
            except Exception as e:
                print(f"  Check err: {e}", flush=True)
                info = {"textLength": prev_text_len}

            text_len = info.get("textLength", 0)
            delta = text_len - baseline_len  # growth from baseline
            text_delta = text_len - prev_text_len  # growth from last wave

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
                stages.append(f"IMG({info.get('imageCount', 0)})")

            new_stages = set(stages) - seen_stages
            seen_stages.update(stages)

            print(f"  Stages: {stages}", flush=True)
            if new_stages:
                print(f"  ** NEW: {new_stages} **", flush=True)
                for s in new_stages:
                    await ss(page, f"STAGE_{s.split('(')[0]}")
            if info.get("imageSrcs"):
                print(f"  Images: {info['imageSrcs']}", flush=True)
            print(f"  Text: {text_len} (growth: +{delta} from baseline, +{text_delta} from prev)", flush=True)
            tail = info.get("lastChars", "")
            # Only show non-JS tail
            if tail and not tail.strip().startswith('{') and 'function' not in tail[:50]:
                print(f"  Tail: {tail[:250]}", flush=True)

            # Staleness
            if abs(text_delta) < 50:
                stale += 1
            else:
                stale = 0
            prev_text_len = text_len

            # Completion — only after 5 min with significant text growth
            if elapsed > 5 and delta > 1000:
                if info.get("hasComplete") or (info.get("hasFocusGroup") and info.get("hasPDF")):
                    print(f"\n*** PIPELINE COMPLETE! ({elapsed:.1f} min) ***", flush=True)
                    height = await page.evaluate("document.body.scrollHeight")
                    for pct in range(0, 101, 10):
                        await page.evaluate(f"window.scrollTo(0, {int(height * pct / 100)})")
                        await page.wait_for_timeout(500)
                        await ss(page, f"FINAL_{pct:03d}")
                    break

            # Send continue (after wave 1, not too often if stale)
            if wave >= 1 and stale < 5:
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

            wait = 30 if stale < 3 else 45 if stale < 6 else 60
            print(f"  Wait {wait}s (stale={stale})", flush=True)
            await page.wait_for_timeout(wait * 1000)

        # === Results ===
        elapsed = (time.time() - start) / 60
        print(f"\n{'='*60}")
        print(f"DONE — {elapsed:.1f} min")
        print(f"Stages: {seen_stages}")

        try:
            final = await page.evaluate(CHECK_CONTENT_JS)
            final_growth = final.get("textLength", 0) - baseline_len
            gates = {
                "research": final.get("hasResearch", False),
                "images": final.get("imageCount", 0) > 0,
                "video": final.get("hasVideo", False),
                "focus_group": final.get("hasFocusGroup", False),
                "pdf": final.get("hasPDF", False),
                "thinking": final.get("hasThinking", False),
                "text_growth": final_growth > 1000,
            }
            print(f"\nQUALITY GATES (text growth: {final_growth}):")
            for g, v in gates.items():
                print(f"  {g}: {'PASS' if v else 'FAIL'}")
            crit = all(gates[k] for k in ["research", "video", "focus_group", "pdf"])
            print(f"\nCRITICAL: {'PASS' if crit else 'FAIL'}")
            print(f"CEO READY: {'YES' if crit and gates['images'] and gates['thinking'] else 'NOT YET'}")
        except:
            pass
        print(f"{'='*60}", flush=True)


if __name__ == "__main__":
    asyncio.run(run())

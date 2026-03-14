"""GE Browser Full E2E v2 — robust @mention + pipeline monitor.

Uses keyboard navigation for @mention dropdown (ArrowDown + Enter).
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

CHECK_CONTENT_JS = """() => {
    // GE uses shadow DOM — try to get text from all shadow roots too
    function getAllText(root) {
        let text = '';
        if (root.shadowRoot) text += getAllText(root.shadowRoot);
        for (const child of root.childNodes) {
            if (child.nodeType === 3) text += child.textContent;
            else if (child.nodeType === 1) text += getAllText(child);
        }
        return text;
    }
    const text = getAllText(document.body).toLowerCase();

    // Also check for images inside shadow roots
    function getAllImages(root) {
        let imgs = [];
        if (root.shadowRoot) imgs = imgs.concat(getAllImages(root.shadowRoot));
        root.querySelectorAll && root.querySelectorAll('img').forEach(img => {
            if (img.width > 100 && !img.src.includes('avatar') && !img.src.includes('icon')) {
                imgs.push(img.src.substring(0, 80));
            }
        });
        for (const child of root.children || []) {
            imgs = imgs.concat(getAllImages(child));
        }
        return imgs;
    }
    const bigImgs = getAllImages(document.body);

    return {
        hasResearch: text.includes('research report') || text.includes('cited report') || text.includes('market research'),
        hasAdCopy: text.includes('ad copy') || text.includes('ad creative') || text.includes('headline'),
        hasImages: bigImgs.length > 0,
        imageCount: bigImgs.length,
        hasVideo: text.includes('commercial') || text.includes('veo') || text.includes('video gen'),
        hasFocusGroup: text.includes('focus group') || text.includes('panelist'),
        hasPDF: text.includes('pdf') || text.includes('campaign brief') || text.includes('final report'),
        hasThinking: text.includes('thinking') || text.includes('thought'),
        hasComplete: text.includes('pipeline complete') || text.includes('campaign is complete') || text.includes('all stages complete'),
        hasTrends: text.includes('trending') || text.includes('search trend') || text.includes('youtube trend'),
        textLength: text.length,
        lastChars: text.substring(text.length - 300),
    };
}"""


async def ss(page, name):
    ts = datetime.now().strftime("%H%M%S")
    path = SS_DIR / f"{name}_{ts}.png"
    try:
        await page.screenshot(path=str(path))
        print(f"  SS: {path.name}", flush=True)
    except Exception as e:
        print(f"  SS error: {e}", flush=True)


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
        print("PHASE 1: Navigate to GE chat", flush=True)
        await page.goto(GE_CHAT_URL, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(8000)
        await ss(page, "01_loaded")

        # === PHASE 2: New chat ===
        print("PHASE 2: New chat", flush=True)
        # Try clicking "New chat" button
        try:
            btn = await page.wait_for_selector('button:has-text("New chat")', timeout=5000)
            if btn:
                await btn.click()
                print("  Clicked New chat", flush=True)
                await page.wait_for_timeout(3000)
        except:
            print("  No 'New chat' button found, continuing", flush=True)
        await ss(page, "02_new_chat")

        # === PHASE 3: Focus input + @mention ===
        print("PHASE 3: @mention agent", flush=True)

        # Find the contenteditable input
        input_found = False
        for sel in ['div[contenteditable="true"]', 'textarea']:
            try:
                el = await page.wait_for_selector(sel, timeout=5000)
                if el and await el.is_visible():
                    await el.click()
                    input_found = True
                    print(f"  Found input: {sel}", flush=True)
                    break
            except:
                continue

        if not input_found:
            # CDP coordinate fallback
            print("  Using CDP coords for input", flush=True)
            cdp = await page.context.new_cdp_session(page)
            for evt in ["mousePressed", "mouseReleased"]:
                await cdp.send("Input.dispatchMouseEvent", {
                    "type": evt, "x": 951, "y": 492, "button": "left", "clickCount": 1,
                })
            await cdp.detach()

        await page.wait_for_timeout(500)

        # Type @Trend to trigger dropdown
        await page.keyboard.type("@Trend", delay=80)
        print("  Typed @Trend", flush=True)
        await page.wait_for_timeout(2000)
        await ss(page, "03_dropdown")

        # Use keyboard to select from dropdown:
        # Based on previous session, Trends2Insights appears in the list
        # Try clicking directly first via various methods
        clicked = False

        # Method 1: Try page.locator with filter
        try:
            loc = page.locator("text=Trends2Insights").first
            if await loc.count() > 0 and await loc.is_visible():
                await loc.click()
                clicked = True
                print("  Clicked via locator: Trends2Insights", flush=True)
        except:
            pass

        # Method 2: Try using keyboard ArrowDown + scan visible text
        if not clicked:
            # Press ArrowDown a few times and Enter — agent was previously at position
            # after filtering with @Trend, "Trends2Insights" should be first or second
            await page.keyboard.press("ArrowDown")
            await page.wait_for_timeout(300)
            await ss(page, "03b_arrow1")
            await page.keyboard.press("Enter")
            await page.wait_for_timeout(1000)
            clicked = True
            print("  Selected via ArrowDown + Enter", flush=True)

        await page.wait_for_timeout(1000)
        await ss(page, "04_agent_selected")

        # === PHASE 4: Type and send message ===
        print("PHASE 4: Send campaign message", flush=True)
        # The agent name chip should now be in the input; type the message after it
        await page.keyboard.type(CAMPAIGN_MESSAGE, delay=3)
        await page.wait_for_timeout(500)
        await ss(page, "05_typed")

        await page.keyboard.press("Enter")
        print("  Message sent!", flush=True)
        await page.wait_for_timeout(5000)
        await ss(page, "06_sent")

        # === PHASE 5: Monitor pipeline ===
        print(f"\n{'='*60}")
        print("PHASE 5: Monitor pipeline")
        print(f"{'='*60}", flush=True)

        seen_stages = set()
        stale_count = 0
        last_text_len = 0

        for wave in range(45):
            elapsed = (time.time() - start) / 60
            print(f"\n=== Wave {wave+1} ({elapsed:.1f} min) ===", flush=True)

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

            text_len = info.get("textLength", 0)
            print(f"  Stages: {stages}", flush=True)
            if new_stages:
                print(f"  NEW: {new_stages}", flush=True)
                for s in new_stages:
                    await ss(page, f"STAGE_{s.split('(')[0]}")
            print(f"  Text: {text_len} chars", flush=True)
            last = info.get("lastChars", "")
            print(f"  Tail: {last[:200]}", flush=True)

            # Detect stale (no text growth)
            if text_len == last_text_len:
                stale_count += 1
            else:
                stale_count = 0
            last_text_len = text_len

            # Check completion
            if info.get("hasComplete") or (info.get("hasFocusGroup") and info.get("hasPDF")):
                print(f"\n*** PIPELINE COMPLETE! ***", flush=True)
                height = await page.evaluate("document.body.scrollHeight")
                for pct in [0, 20, 40, 60, 80, 100]:
                    await page.evaluate(f"window.scrollTo(0, {int(height * pct / 100)})")
                    await page.wait_for_timeout(500)
                    await ss(page, f"FINAL_scroll{pct}")
                break

            # Send "continue" if not stale too long
            if stale_count < 3:
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
                    print(f"  Continue error: {str(e)[:80]}", flush=True)
            else:
                print(f"  Stale {stale_count}x — skipping continue, waiting longer", flush=True)

            # Wait
            wait_s = 30 if stale_count < 3 else 60
            print(f"  Waiting {wait_s}s...", flush=True)
            await page.wait_for_timeout(wait_s * 1000)

        # === RESULTS ===
        elapsed = (time.time() - start) / 60
        print(f"\n{'='*60}")
        print(f"DONE — {elapsed:.1f} min")
        print(f"Stages: {seen_stages}")
        print(f"Screenshots: {SS_DIR}")

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
                print(f"  {g}: {'PASS' if v else 'FAIL'}")
            crit = gates["research"] and gates["video"] and gates["focus_group"] and gates["pdf"]
            print(f"\nCRITICAL: {'PASS' if crit else 'FAIL'}")
            print(f"CEO READY: {'YES' if crit and gates['images'] and gates['thinking'] else 'NOT YET'}")
        except:
            pass
        print(f"{'='*60}", flush=True)


if __name__ == "__main__":
    asyncio.run(run())

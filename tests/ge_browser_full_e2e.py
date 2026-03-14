"""GE Browser Full E2E — navigate, @mention agent, send campaign, monitor pipeline.

Single script that does the complete flow:
1. Navigate to GE chat
2. Start new chat
3. @mention Trends2Insights agent
4. Send full campaign message with autopilot mode
5. Monitor pipeline with screenshots every 30s, sending "continue" as needed

Usage:
  DISPLAY=:20 /usr/local/google/home/jwortz/miniconda3/bin/python -u tests/ge_browser_full_e2e.py
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
        hasStatusChips: document.querySelectorAll('[class*="chip"], [class*="status"]').length,
        textLength: text.length,
        lastLines: text.split('\\n').filter(l => l.trim()).slice(-5).join(' | ').substring(0, 300),
    };
}"""


async def screenshot(page, name):
    ts = datetime.now().strftime("%H%M%S")
    path = SS_DIR / f"{name}_{ts}.png"
    try:
        await page.screenshot(path=str(path))
        print(f"  SS: {path.name}", flush=True)
        return str(path)
    except Exception as e:
        print(f"  SS error: {e}", flush=True)
        return None


async def click_at(page, x, y):
    """Click at exact coordinates using CDP."""
    cdp = await page.context.new_cdp_session(page)
    for evt in ["mousePressed", "mouseReleased"]:
        await cdp.send("Input.dispatchMouseEvent", {
            "type": evt, "x": x, "y": y, "button": "left",
            "clickCount": 1,
        })
    await cdp.detach()


async def find_and_click_chat_input(page):
    """Find the GE chat input (may be in shadow DOM) and click it."""
    # Try standard selectors first
    for sel in ['div[contenteditable="true"]', 'textarea', 'input[type="text"]']:
        try:
            el = await page.wait_for_selector(sel, timeout=3000)
            if el and await el.is_visible():
                await el.click()
                print(f"  Found chat input via: {sel}", flush=True)
                return True
        except:
            continue

    # Fallback: click at known CDP coordinates for GE chat input
    print("  Using CDP coordinates (951, 492) for chat input", flush=True)
    await click_at(page, 951, 492)
    await page.wait_for_timeout(500)
    return True


async def send_chat_message(page, message):
    """Type and send a message in the GE chat."""
    await find_and_click_chat_input(page)
    await page.wait_for_timeout(500)
    await page.keyboard.type(message, delay=5)
    await page.wait_for_timeout(300)
    await page.keyboard.press("Enter")
    print(f"  Sent: {message[:80]}...", flush=True)


async def run():
    from playwright.async_api import async_playwright

    SS_DIR.mkdir(parents=True, exist_ok=True)
    start = time.time()

    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(CDP_URL)
        context = browser.contexts[0]
        page = context.pages[0]
        await page.set_viewport_size({"width": 1920, "height": 1080})

        # === PHASE 1: Navigate to GE chat ===
        print(f"\n{'='*60}")
        print("PHASE 1: Navigate to GE chat")
        print(f"{'='*60}", flush=True)

        await page.goto(GE_CHAT_URL, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(8000)
        await screenshot(page, "01_chat_page")

        # === PHASE 2: Start new chat ===
        print(f"\n{'='*60}")
        print("PHASE 2: Start new chat")
        print(f"{'='*60}", flush=True)

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
                    print(f"  Clicked: {selector}", flush=True)
                    await page.wait_for_timeout(3000)
                    break
            except:
                continue

        await screenshot(page, "02_new_chat")

        # === PHASE 3: @mention Trends2Insights agent ===
        print(f"\n{'='*60}")
        print("PHASE 3: @mention Trends2Insights agent")
        print(f"{'='*60}", flush=True)

        # Focus chat input
        await find_and_click_chat_input(page)
        await page.wait_for_timeout(500)

        # Type @Trend to trigger dropdown
        await page.keyboard.type("@Trend", delay=50)
        print("  Typed @Trend", flush=True)
        await page.wait_for_timeout(2000)
        await screenshot(page, "03_at_mention_dropdown")

        # Click on "Trends2Insights" in the dropdown
        clicked_agent = False
        for text_match in ["Trends2Insights", "trends2insights", "Trends2"]:
            try:
                el = page.get_by_text(text_match, exact=False).first
                if await el.is_visible(timeout=2000):
                    await el.click()
                    clicked_agent = True
                    print(f"  Clicked agent: {text_match}", flush=True)
                    break
            except:
                continue

        if not clicked_agent:
            # Try clicking by role
            try:
                options = await page.query_selector_all('[role="option"], [role="listitem"], li')
                for opt in options:
                    text = await opt.inner_text()
                    if "trend" in text.lower() or "insight" in text.lower():
                        await opt.click()
                        clicked_agent = True
                        print(f"  Clicked option: {text[:50]}", flush=True)
                        break
            except:
                pass

        if not clicked_agent:
            print("  WARNING: Could not click agent from dropdown, sending @Trends2Insights inline", flush=True)
            # Clear what we typed and try inline @mention
            for _ in range(6):  # delete "@Trend"
                await page.keyboard.press("Backspace")
            await page.keyboard.type("@Trends2Insights ", delay=20)

        await page.wait_for_timeout(1000)
        await screenshot(page, "04_agent_selected")

        # === PHASE 4: Send campaign message ===
        print(f"\n{'='*60}")
        print("PHASE 4: Send campaign message")
        print(f"{'='*60}", flush=True)

        await page.keyboard.type(CAMPAIGN_MESSAGE, delay=3)
        await page.wait_for_timeout(500)
        await screenshot(page, "05_message_typed")

        await page.keyboard.press("Enter")
        print("  Message sent!", flush=True)
        await page.wait_for_timeout(5000)
        await screenshot(page, "06_message_sent")

        # === PHASE 5: Monitor pipeline ===
        print(f"\n{'='*60}")
        print("PHASE 5: Monitor pipeline progression")
        print(f"{'='*60}", flush=True)

        seen_stages = set()
        for wave in range(45):
            elapsed = (time.time() - start) / 60
            print(f"\n=== Wave {wave+1} ({elapsed:.1f} min) ===", flush=True)

            # Scroll to bottom
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(2000)

            # Screenshot
            await screenshot(page, f"wave_{wave+1:02d}")

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
                # Extra screenshot for new stages
                for stage in new_stages:
                    await screenshot(page, f"STAGE_{stage.split('(')[0]}")
            print(f"  Text: {info.get('textLength', 0)} chars | Chips: {info.get('hasStatusChips', 0)}", flush=True)
            last = info.get("lastLines", "")
            print(f"  Last: {last[:200]}", flush=True)

            # Check completion
            if info.get("hasComplete") or (info.get("hasFocusGroup") and info.get("hasPDF")):
                print(f"\n*** PIPELINE COMPLETE! ***", flush=True)
                # Capture scrolling final screenshots
                height = await page.evaluate("document.body.scrollHeight")
                for pct in [0, 20, 40, 60, 80, 100]:
                    await page.evaluate(f"window.scrollTo(0, {int(height * pct / 100)})")
                    await page.wait_for_timeout(500)
                    await screenshot(page, f"FINAL_scroll{pct}")
                # Full page screenshot
                try:
                    ts = datetime.now().strftime("%H%M%S")
                    await page.screenshot(
                        path=str(SS_DIR / f"COMPLETE_fullpage_{ts}.png"),
                        full_page=True
                    )
                    print(f"  Full page screenshot saved", flush=True)
                except:
                    pass
                break

            # Send "continue" to advance pipeline
            try:
                await find_and_click_chat_input(page)
                await page.wait_for_timeout(300)
                await page.keyboard.type("continue", delay=10)
                await page.keyboard.press("Enter")
                print(f"  Sent 'continue'", flush=True)
            except Exception as e:
                print(f"  Continue error: {str(e)[:80]}", flush=True)

            # Wait for response
            print(f"  Waiting 30s...", flush=True)
            await page.wait_for_timeout(30000)

        # === RESULTS ===
        elapsed = (time.time() - start) / 60
        print(f"\n{'='*60}")
        print(f"RESULTS — {elapsed:.1f} minutes")
        print(f"{'='*60}")
        print(f"Stages seen: {seen_stages}")
        print(f"Screenshots: {SS_DIR}")

        # Quality gates
        try:
            final = await page.evaluate(CHECK_CONTENT_JS)
            gates = {
                "trends": final.get("hasTrends", False),
                "research": final.get("hasResearch", False),
                "ad_copy": final.get("hasAdCopy", False),
                "images": final.get("imageCount", 0) > 0,
                "video": final.get("hasVideo", False),
                "focus_group": final.get("hasFocusGroup", False),
                "pdf": final.get("hasPDF", False),
                "thinking": final.get("hasThinking", False),
            }
            print(f"\nQUALITY GATES:")
            for gate, passed in gates.items():
                print(f"  {gate}: {'PASS' if passed else 'FAIL'}")
            all_critical = gates["research"] and gates["video"] and gates["focus_group"] and gates["pdf"]
            print(f"\nCRITICAL GATES: {'PASS' if all_critical else 'FAIL'}")
            print(f"CEO IMPRESSIVE: {'YES' if all_critical and gates['images'] and gates['thinking'] else 'NOT YET'}")
        except:
            print("  Could not evaluate final gates")

        print(f"{'='*60}", flush=True)


if __name__ == "__main__":
    asyncio.run(run())

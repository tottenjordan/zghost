"""GE Browser Observe Only — just take screenshots, NO continue messages.

The pipeline should run on its own after the initial message.
Sending "continue" may be interfering by creating new turns.
"""
import asyncio
import time
from datetime import datetime
from pathlib import Path

SS_DIR = Path("demo_screenshots/ge_browser_observe")
CDP_URL = "http://localhost:9222"
GE_CHAT_URL = "https://vertexaisearch.cloud.google.com/home/cid/c4da98d6-1b97-4e31-bb6a-ba979e363c26?hl=en_US"

CAMPAIGN_MESSAGE = """Create a full marketing campaign for Tide Fabric Softener with Hibiscus Scent.

Brand: Tide
Product: Tide Fabric Softener with Hibiscus Scent
Target Audience: Gen Z eco-conscious consumers
Key Selling Points: New Hibiscus Scent, Plant-based formula, 2x cleaning power, Biodegradable packaging

Run in autopilot mode — auto-select trend 1 for both search and YouTube trends, then proceed through the full pipeline: research, ad creative, image generation, 15s video commercial, focus group evaluation, and final PDF campaign brief."""


async def ss(page, name):
    ts = datetime.now().strftime("%H%M%S")
    path = SS_DIR / f"{name}_{ts}.png"
    try:
        await page.screenshot(path=str(path))
        print(f"  SS: {path.name}", flush=True)
    except:
        pass


async def get_ax_text(page):
    try:
        cdp = await page.context.new_cdp_session(page)
        tree = await cdp.send("Accessibility.getFullAXTree")
        await cdp.detach()
        texts = []
        for node in tree.get("nodes", []):
            name = node.get("name", {}).get("value", "")
            if name and len(name) > 3:
                texts.append(name)
        return " ".join(texts)
    except:
        return ""


async def run():
    from playwright.async_api import async_playwright

    SS_DIR.mkdir(parents=True, exist_ok=True)
    start = time.time()

    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(CDP_URL)
        page = browser.contexts[0].pages[0]
        await page.set_viewport_size({"width": 1920, "height": 1080})

        # Navigate + New chat
        print("Navigate + New chat", flush=True)
        await page.goto(GE_CHAT_URL, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(8000)
        try:
            btn = await page.wait_for_selector('button:has-text("New chat")', timeout=5000)
            if btn:
                await btn.click()
                await page.wait_for_timeout(3000)
        except:
            pass

        # @mention + send (one time only)
        print("Send message", flush=True)
        for sel in ['div[contenteditable="true"]', 'textarea']:
            try:
                el = await page.wait_for_selector(sel, timeout=5000)
                if el and await el.is_visible():
                    await el.click()
                    break
            except:
                continue

        await page.wait_for_timeout(500)
        await page.keyboard.type("@Trend", delay=80)
        await page.wait_for_timeout(2500)

        try:
            loc = page.locator("text=Trends2Insights").first
            if await loc.count() > 0:
                await loc.click()
                print("  Clicked Trends2Insights", flush=True)
        except:
            await page.keyboard.press("ArrowDown")
            await page.wait_for_timeout(200)
            await page.keyboard.press("Enter")
            print("  Keyboard select", flush=True)

        await page.wait_for_timeout(1000)
        await page.keyboard.type(CAMPAIGN_MESSAGE, delay=3)
        await page.wait_for_timeout(500)
        await page.keyboard.press("Enter")
        msg_time = time.time()
        print("  SENT! Now observing (no more messages)...", flush=True)
        await page.wait_for_timeout(5000)
        await ss(page, "00_sent")

        # === OBSERVE ONLY — no continue messages ===
        print(f"\n{'='*60}")
        print("OBSERVE ONLY MODE (no continue messages)")
        print(f"{'='*60}", flush=True)

        baseline = len(await get_ax_text(page))
        prev_len = baseline

        for wave in range(60):  # up to 30 min
            elapsed = (time.time() - msg_time) / 60
            print(f"\n=== Wave {wave+1} ({elapsed:.1f} min) ===", flush=True)

            # Scroll to bottom (gentle)
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(2000)
            await ss(page, f"obs_{wave+1:02d}")

            ax = await get_ax_text(page)
            tl = len(ax)
            delta = tl - prev_len
            growth = tl - baseline

            # Quick keyword scan
            lower = ax.lower()
            indicators = []
            for term in ["running", "thinking", "research", "ad copy", "image gen", "veo", "commercial", "focus group", "campaign brief", "pipeline complete"]:
                if term in lower:
                    indicators.append(term.upper())

            print(f"  Text: {tl} (+{growth} total, +{delta} wave)", flush=True)
            print(f"  Indicators: {indicators}", flush=True)
            print(f"  Tail: {ax[-200:]}", flush=True)

            prev_len = tl

            # Check real completion (text must have grown significantly)
            if elapsed > 5 and growth > 2000:
                if "pipeline complete" in lower or ("focus group" in lower and "campaign brief" in lower and growth > 5000):
                    print(f"\n*** PIPELINE COMPLETE! ***", flush=True)
                    height = await page.evaluate("document.body.scrollHeight")
                    for pct in range(0, 101, 5):
                        await page.evaluate(f"window.scrollTo(0, {int(height * pct / 100)})")
                        await page.wait_for_timeout(400)
                        await ss(page, f"FINAL_{pct:03d}")
                    break

            # Wait 30s between observations
            await page.wait_for_timeout(30000)

        elapsed = (time.time() - start) / 60
        print(f"\n{'='*60}")
        print(f"DONE — {elapsed:.1f} min")

        final = await get_ax_text(page)
        fg = len(final) - baseline
        lower = final.lower()
        gates = {
            "research": "research" in lower and fg > 500,
            "commercial": "commercial" in lower and fg > 1000,
            "focus_group": "focus group" in lower and fg > 2000,
            "pdf": "campaign brief" in lower and fg > 3000,
            "thinking": "thinking" in lower,
        }
        print(f"\nGATES (growth: +{fg}):")
        for g, v in gates.items():
            print(f"  {g}: {'PASS' if v else 'FAIL'}")
        print(f"{'='*60}", flush=True)


if __name__ == "__main__":
    asyncio.run(run())

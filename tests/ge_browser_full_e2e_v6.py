"""GE Browser Full E2E v6 — clear agent bar after first message.

Key insight: After sending @Trends2Insights message, the agent bar stays selected.
Subsequent "continue" messages get routed back to Trends2Insights instead of the
root orchestrator. Must clear the agent bar after the first message so "continue"
goes to the orchestrator which checks state and advances the pipeline.
"""
import asyncio
import time
from datetime import datetime
from pathlib import Path

SS_DIR = Path("demo_screenshots/ge_browser_full_e2e_v6")
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

        # === Navigate ===
        print("Navigate", flush=True)
        await page.goto(GE_CHAT_URL, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(8000)
        await ss(page, "01_loaded")

        # === New chat ===
        print("New chat", flush=True)
        try:
            btn = await page.wait_for_selector('button:has-text("New chat")', timeout=5000)
            if btn:
                await btn.click()
                await page.wait_for_timeout(3000)
                print("  Clicked New chat", flush=True)
        except:
            pass
        await ss(page, "02_new_chat")

        # === @mention + send initial message ===
        print("@mention + send initial message", flush=True)
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
        await ss(page, "03_typed")
        await page.keyboard.press("Enter")
        msg_time = time.time()
        print("  SENT!", flush=True)
        await page.wait_for_timeout(8000)
        await ss(page, "04_sent")

        # === CRITICAL: Clear the agent bar ===
        # The agent bar has "Trends2Insights" selected with a clear button.
        # We must clear it so subsequent messages go to the root orchestrator.
        print("Clearing agent bar...", flush=True)
        cleared = False

        # Method 1: Click the clear/close button in the agent bar
        for sel in [
            'button[aria-label*="clear"]',
            'button[aria-label*="Close"]',
            'button[aria-label*="close"]',
            'button[aria-label*="Remove"]',
        ]:
            try:
                el = await page.wait_for_selector(sel, timeout=2000)
                if el and await el.is_visible():
                    await el.click()
                    cleared = True
                    print(f"  Cleared via: {sel}", flush=True)
                    break
            except:
                continue

        # Method 2: Try clicking the "Button to clear the selected agent" from AX tree
        if not cleared:
            try:
                # The AX tree showed: "Trends2Insights Button to clear the selected agent and close the agent bar."
                loc = page.locator('button:near(:text("Trends2Insights"))').first
                if await loc.count() > 0:
                    await loc.click()
                    cleared = True
                    print("  Cleared via near-text button", flush=True)
            except:
                pass

        # Method 3: Press Escape to dismiss
        if not cleared:
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(500)
            print("  Pressed Escape", flush=True)

        await page.wait_for_timeout(2000)
        await ss(page, "05_agent_cleared")

        # Verify agent bar is cleared
        ax = await get_ax_text(page)
        if "Button to clear the selected agent" in ax:
            print("  WARNING: Agent bar still active — trying X button", flush=True)
            # Try finding an X/close button near the agent name
            try:
                buttons = await page.query_selector_all('button')
                for btn in buttons:
                    try:
                        label = await btn.get_attribute('aria-label') or ''
                        text = await btn.inner_text()
                        if 'close' in label.lower() or 'clear' in label.lower() or text.strip() in ['×', 'x', 'X', '✕']:
                            box = await btn.bounding_box()
                            if box and box['y'] > 400:  # likely in chat area
                                await btn.click()
                                cleared = True
                                print(f"  Cleared via button: label='{label}' text='{text}'", flush=True)
                                break
                    except:
                        continue
            except:
                pass

        await page.wait_for_timeout(1000)
        await ss(page, "06_ready_for_continue")

        # === Wait for trends to complete, then send continue messages ===
        print(f"\n{'='*60}")
        print("MONITORING + CONTINUE (agent bar cleared)")
        print(f"{'='*60}", flush=True)

        # Wait for the trends agent to finish (30s initial wait)
        print("  Waiting 30s for trends to complete...", flush=True)
        await page.wait_for_timeout(30000)

        baseline = len(await get_ax_text(page))
        prev_len = baseline
        stale = 0
        seen = set()

        for wave in range(45):
            elapsed = (time.time() - msg_time) / 60
            print(f"\n=== Wave {wave+1} ({elapsed:.1f} min) ===", flush=True)

            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(2000)
            await ss(page, f"wave_{wave+1:02d}")

            ax = await get_ax_text(page)
            tl = len(ax)
            growth = tl - baseline
            delta = tl - prev_len

            lower = ax.lower()
            stages = []
            for term, label in [
                ("trending", "TRENDS"), ("research findings", "RESEARCH"),
                ("research report", "RESEARCH"), ("ad copy", "AD_COPY"),
                ("headline", "AD_COPY"), ("generating image", "IMAGES"),
                ("generated image", "IMAGES"), ("veo", "VIDEO"),
                ("commercial", "VIDEO"), ("focus group", "FOCUS_GROUP"),
                ("panelist", "FOCUS_GROUP"), ("campaign brief", "PDF"),
                ("final report", "PDF"), ("thinking", "THINKING"),
                ("running", "STATUS"),
            ]:
                if term in lower and label not in stages:
                    stages.append(label)

            new = set(stages) - seen
            seen.update(stages)

            print(f"  Stages: {stages}", flush=True)
            if new:
                print(f"  ** NEW: {new} **", flush=True)
                for s in new:
                    await ss(page, f"STAGE_{s}")
            print(f"  Text: {tl} (+{growth} total, +{delta} wave)", flush=True)
            print(f"  Tail: {ax[-200:]}", flush=True)

            if abs(delta) < 30:
                stale += 1
            else:
                stale = 0
            prev_len = tl

            # Completion
            if elapsed > 5 and growth > 2000:
                if "pipeline complete" in lower or "all stages complete" in lower:
                    print(f"\n*** PIPELINE COMPLETE! ***", flush=True)
                    height = await page.evaluate("document.body.scrollHeight")
                    for pct in range(0, 101, 5):
                        await page.evaluate(f"window.scrollTo(0, {int(height * pct / 100)})")
                        await page.wait_for_timeout(400)
                        await ss(page, f"FINAL_{pct:03d}")
                    break

            # Send "continue" (WITHOUT agent bar — goes to root orchestrator)
            if stale < 8:
                try:
                    for sel in ['div[contenteditable="true"]', 'textarea']:
                        try:
                            el = await page.wait_for_selector(sel, timeout=3000)
                            if el and await el.is_visible():
                                await el.click()
                                await page.wait_for_timeout(300)
                                await page.keyboard.type("continue", delay=10)
                                await page.keyboard.press("Enter")
                                print(f"  Sent 'continue' (no agent)", flush=True)
                                break
                        except:
                            continue
                except:
                    pass

            wait = 30 if stale < 3 else 45 if stale < 6 else 60
            print(f"  Wait {wait}s (stale={stale})", flush=True)
            await page.wait_for_timeout(wait * 1000)

        # === Results ===
        elapsed = (time.time() - start) / 60
        final = await get_ax_text(page)
        fg = len(final) - baseline
        lower = final.lower()

        print(f"\n{'='*60}")
        print(f"DONE — {elapsed:.1f} min | Seen: {seen}")
        gates = {
            "research": "research" in lower and fg > 500,
            "video": ("commercial" in lower or "veo" in lower) and fg > 1000,
            "focus_group": ("focus group" in lower or "panelist" in lower) and fg > 2000,
            "pdf": ("campaign brief" in lower or "final report" in lower) and fg > 3000,
            "thinking": "thinking" in lower,
        }
        print(f"\nGATES (growth: +{fg}):")
        for g, v in gates.items():
            print(f"  {g}: {'PASS' if v else 'FAIL'}")
        crit = all(gates[k] for k in ["research", "video", "focus_group", "pdf"])
        print(f"CRITICAL: {'PASS' if crit else 'FAIL'}")
        print(f"{'='*60}", flush=True)


if __name__ == "__main__":
    asyncio.run(run())

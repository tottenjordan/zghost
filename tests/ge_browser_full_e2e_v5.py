"""GE Browser Full E2E v5 — CDP Accessibility tree for shadow DOM text.

Uses CDP Accessibility.getFullAXTree to extract text from GE's shadow DOM.
This is the only reliable method to read chat content from GE's UI.
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


async def ss(page, name):
    ts = datetime.now().strftime("%H%M%S")
    path = SS_DIR / f"{name}_{ts}.png"
    try:
        await page.screenshot(path=str(path))
        print(f"  SS: {path.name}", flush=True)
    except Exception as e:
        print(f"  SS err: {e}", flush=True)


async def get_ax_text(page):
    """Get all visible text from GE page via CDP Accessibility tree."""
    try:
        cdp = await page.context.new_cdp_session(page)
        tree = await cdp.send("Accessibility.getFullAXTree")
        await cdp.detach()
        nodes = tree.get("nodes", [])
        texts = []
        for node in nodes:
            name = node.get("name", {}).get("value", "")
            if name and len(name) > 3:
                texts.append(name)
        return " ".join(texts)
    except Exception as e:
        print(f"  AX err: {e}", flush=True)
        return ""


def analyze_text(text):
    """Analyze AX text for pipeline stage indicators."""
    lower = text.lower()
    return {
        "hasTrends": "search trend" in lower or "youtube trend" in lower or "trending" in lower,
        "hasResearch": "research report" in lower or "cited report" in lower or "market research" in lower or "research findings" in lower,
        "hasAdCopy": "ad copy" in lower or "ad creative" in lower or "headline" in lower or "tagline" in lower,
        "hasVideo": "commercial" in lower or "veo" in lower or "video generation" in lower,
        "hasFocusGroup": "focus group" in lower or "panelist" in lower or "evaluation score" in lower,
        "hasPDF": "campaign brief" in lower or "final report" in lower or ".pdf" in lower,
        "hasThinking": "thinking" in lower,
        "hasComplete": "pipeline complete" in lower or "campaign is complete" in lower or "all stages complete" in lower,
        "hasImages": "image generation" in lower or "generating image" in lower or "generated image" in lower,
        "hasStatus": "running" in lower or "status" in lower or "working on" in lower,
        "textLength": len(text),
    }


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

        # Select agent
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
        await page.keyboard.type(CAMPAIGN_MESSAGE, delay=3)
        await page.wait_for_timeout(500)
        await ss(page, "04_typed")
        await page.keyboard.press("Enter")
        msg_time = time.time()
        print("  SENT!", flush=True)
        await page.wait_for_timeout(5000)
        await ss(page, "05_sent")

        # === Monitor via AX tree ===
        print(f"\n{'='*60}")
        print("MONITORING PIPELINE (AX tree)")
        print(f"{'='*60}", flush=True)

        baseline_text = await get_ax_text(page)
        baseline_len = len(baseline_text)
        print(f"  Baseline: {baseline_len} chars", flush=True)

        seen_stages = set()
        prev_len = baseline_len
        stale = 0

        for wave in range(45):
            elapsed = (time.time() - msg_time) / 60
            print(f"\n=== Wave {wave+1} ({elapsed:.1f} min) ===", flush=True)

            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(2000)
            await ss(page, f"wave_{wave+1:02d}")

            # Get text via AX tree
            ax_text = await get_ax_text(page)
            info = analyze_text(ax_text)
            text_len = info["textLength"]
            growth = text_len - baseline_len
            delta = text_len - prev_len

            stages = []
            for key, label in [
                ("hasTrends", "TRENDS"), ("hasResearch", "RESEARCH"),
                ("hasAdCopy", "AD_COPY"), ("hasImages", "IMAGES"),
                ("hasVideo", "VIDEO"), ("hasFocusGroup", "FOCUS_GROUP"),
                ("hasPDF", "PDF"), ("hasThinking", "THINKING"),
                ("hasStatus", "STATUS_CHIPS"),
            ]:
                if info.get(key):
                    stages.append(label)

            new_stages = set(stages) - seen_stages
            seen_stages.update(stages)

            print(f"  Stages: {stages}", flush=True)
            if new_stages:
                print(f"  ** NEW: {new_stages} **", flush=True)
                for s in new_stages:
                    await ss(page, f"STAGE_{s}")

            print(f"  Text: {text_len} chars (+{growth} total, +{delta} wave)", flush=True)
            # Show tail of AX text (last 300 chars)
            tail = ax_text[-300:] if len(ax_text) > 300 else ax_text
            print(f"  Tail: {tail[:250]}", flush=True)

            # Staleness
            if abs(delta) < 30:
                stale += 1
            else:
                stale = 0
            prev_len = text_len

            # Completion check — only after 5 min with real growth
            if elapsed > 5 and growth > 500:
                if info.get("hasComplete") or (info.get("hasFocusGroup") and info.get("hasPDF")):
                    print(f"\n*** PIPELINE COMPLETE! ({elapsed:.1f} min) ***", flush=True)
                    height = await page.evaluate("document.body.scrollHeight")
                    for pct in range(0, 101, 10):
                        await page.evaluate(f"window.scrollTo(0, {int(height * pct / 100)})")
                        await page.wait_for_timeout(500)
                        await ss(page, f"FINAL_{pct:03d}")
                    break

            # Send continue
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
                except:
                    pass

            wait = 30 if stale < 3 else 45 if stale < 6 else 60
            print(f"  Wait {wait}s (stale={stale})", flush=True)
            await page.wait_for_timeout(wait * 1000)

        # === Results ===
        elapsed = (time.time() - start) / 60
        print(f"\n{'='*60}")
        print(f"DONE — {elapsed:.1f} min")
        print(f"Stages seen: {seen_stages}")

        final_text = await get_ax_text(page)
        final_info = analyze_text(final_text)
        final_growth = final_info["textLength"] - baseline_len

        gates = {
            "trends": final_info.get("hasTrends", False),
            "research": final_info.get("hasResearch", False),
            "ad_creative": final_info.get("hasAdCopy", False),
            "images": final_info.get("hasImages", False),
            "video/commercial": final_info.get("hasVideo", False),
            "focus_group": final_info.get("hasFocusGroup", False),
            "pdf_report": final_info.get("hasPDF", False),
            "thinking": final_info.get("hasThinking", False),
            "text_growth": final_growth > 500,
        }
        print(f"\nQUALITY GATES (growth: +{final_growth} chars):")
        for g, v in gates.items():
            print(f"  {g}: {'PASS' if v else 'FAIL'}")

        crit = all(gates[k] for k in ["research", "video/commercial", "focus_group", "pdf_report"])
        print(f"\nCRITICAL: {'PASS' if crit else 'FAIL'}")
        impressive = crit and gates["images"] and gates["thinking"]
        print(f"CEO READY: {'YES' if impressive else 'NOT YET'}")
        print(f"{'='*60}", flush=True)


if __name__ == "__main__":
    asyncio.run(run())

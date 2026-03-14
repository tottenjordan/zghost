"""GE Browser Monitor v5 — resume monitoring existing session via AX tree.

Does NOT start a new chat. Just monitors the current page, sends "continue",
and takes screenshots until pipeline completes.
"""
import asyncio
import time
from datetime import datetime
from pathlib import Path

SS_DIR = Path("demo_screenshots/ge_browser_full_e2e")
CDP_URL = "http://localhost:9222"


async def ss(page, name):
    ts = datetime.now().strftime("%H%M%S")
    path = SS_DIR / f"{name}_{ts}.png"
    try:
        await page.screenshot(path=str(path))
        print(f"  SS: {path.name}", flush=True)
    except Exception as e:
        print(f"  SS err: {e}", flush=True)


async def get_ax_text(page):
    """Get all visible text via CDP Accessibility tree."""
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
    except Exception as e:
        print(f"  AX err: {e}", flush=True)
        return ""


def check(text):
    lower = text.lower()
    return {
        "hasTrends": "search trend" in lower or "youtube trend" in lower,
        "hasResearch": "research report" in lower or "research findings" in lower or "cited report" in lower or "market research" in lower,
        "hasAdCopy": "ad copy" in lower or "headline" in lower or "tagline" in lower,
        "hasImages": "generated image" in lower or "generating image" in lower or "image generation" in lower,
        "hasVideo": "commercial" in lower or "veo" in lower or "video generation" in lower,
        "hasFocusGroup": "focus group" in lower or "panelist" in lower or "evaluation score" in lower,
        "hasPDF": "campaign brief" in lower or "final report" in lower or ".pdf" in lower,
        "hasThinking": "thinking" in lower,
        "hasComplete": "pipeline complete" in lower or "all stages complete" in lower,
        "hasRunning": "running" in lower,
        "length": len(text),
    }


async def run():
    from playwright.async_api import async_playwright

    SS_DIR.mkdir(parents=True, exist_ok=True)
    start = time.time()

    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(CDP_URL)
        page = browser.contexts[0].pages[0]
        await page.set_viewport_size({"width": 1920, "height": 1080})

        print(f"Resuming monitor on: {page.url}", flush=True)

        baseline = await get_ax_text(page)
        baseline_len = len(baseline)
        print(f"Baseline: {baseline_len} chars", flush=True)

        seen = set()
        prev_len = baseline_len
        stale = 0

        for wave in range(45):
            elapsed = (time.time() - start) / 60
            print(f"\n=== Wave {wave+1} ({elapsed:.1f} min) ===", flush=True)

            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(2000)
            await ss(page, f"monitor_{wave+1:02d}")

            ax = await get_ax_text(page)
            info = check(ax)
            tl = info["length"]
            growth = tl - baseline_len
            delta = tl - prev_len

            stages = []
            for k, l in [("hasTrends", "TRENDS"), ("hasResearch", "RESEARCH"),
                         ("hasAdCopy", "AD_COPY"), ("hasImages", "IMAGES"),
                         ("hasVideo", "VIDEO"), ("hasFocusGroup", "FOCUS_GROUP"),
                         ("hasPDF", "PDF"), ("hasThinking", "THINKING"),
                         ("hasRunning", "RUNNING")]:
                if info.get(k):
                    stages.append(l)

            new = set(stages) - seen
            seen.update(stages)

            print(f"  Stages: {stages}", flush=True)
            if new:
                print(f"  ** NEW: {new} **", flush=True)
                for s in new:
                    await ss(page, f"STAGE_{s}")

            print(f"  Text: {tl} (+{growth} total, +{delta} wave)", flush=True)
            print(f"  Tail: {ax[-250:]}", flush=True)

            if abs(delta) < 30:
                stale += 1
            else:
                stale = 0
            prev_len = tl

            # Completion
            if elapsed > 3 and growth > 300:
                if info.get("hasComplete") or (info.get("hasFocusGroup") and info.get("hasPDF")):
                    print(f"\n*** PIPELINE COMPLETE! ***", flush=True)
                    height = await page.evaluate("document.body.scrollHeight")
                    for pct in range(0, 101, 10):
                        await page.evaluate(f"window.scrollTo(0, {int(height * pct / 100)})")
                        await page.wait_for_timeout(500)
                        await ss(page, f"FINAL_{pct:03d}")
                    break

            # Send continue
            if wave >= 0 and stale < 5:
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

        # Results
        elapsed = (time.time() - start) / 60
        print(f"\n{'='*60}")
        print(f"DONE — {elapsed:.1f} min | Stages: {seen}")

        final = await get_ax_text(page)
        fi = check(final)
        g = fi["length"] - baseline_len
        gates = {
            "trends": fi["hasTrends"],
            "research": fi["hasResearch"],
            "ad_creative": fi["hasAdCopy"],
            "images": fi["hasImages"],
            "video": fi["hasVideo"],
            "focus_group": fi["hasFocusGroup"],
            "pdf": fi["hasPDF"],
            "thinking": fi["hasThinking"],
            "growth": g > 500,
        }
        print(f"\nGATES (growth: +{g}):")
        for k, v in gates.items():
            print(f"  {k}: {'PASS' if v else 'FAIL'}")
        crit = all(gates[k] for k in ["research", "video", "focus_group", "pdf"])
        print(f"\nCRITICAL: {'PASS' if crit else 'FAIL'}")
        print(f"CEO: {'YES' if crit and gates['images'] and gates['thinking'] else 'NOT YET'}")
        print(f"{'='*60}", flush=True)


if __name__ == "__main__":
    asyncio.run(run())

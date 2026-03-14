"""GE Browser Pipeline Loop — click continue and capture screenshots."""
import asyncio
import sys
import time
from datetime import datetime
from pathlib import Path

SS_DIR = Path("demo_screenshots/ge_browser_e2e")
CDP_URL = "http://localhost:9222"

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
        hasResearch: text.includes('research report') || text.includes('cited report') || text.includes('market research') || text.includes('research pipeline'),
        hasAdCopy: text.includes('ad copy') || text.includes('ad creative') || text.includes('headline'),
        hasImages: bigImgs.length > 0,
        imageCount: bigImgs.length,
        hasVideo: text.includes('commercial') || text.includes('veo') || text.includes('video gen'),
        hasFocusGroup: text.includes('focus group') || text.includes('panelist'),
        hasPDF: text.includes('pdf') || text.includes('campaign brief') || text.includes('final report'),
        hasThinking: text.includes('thinking') || document.querySelectorAll('[class*="think"]').length > 0,
        hasComplete: text.includes('pipeline complete') || text.includes('campaign is complete') || text.includes('all stages complete'),
        lastLines: text.split('\\n').filter(l => l.trim()).slice(-5).join(' | ').substring(0, 200),
    };
}"""

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


async def run():
    from playwright.async_api import async_playwright

    SS_DIR.mkdir(parents=True, exist_ok=True)
    start = time.time()

    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(CDP_URL)
        context = browser.contexts[0]
        page = context.pages[0]
        await page.set_viewport_size({"width": 1920, "height": 1080})

        for wave in range(45):
            elapsed = (time.time() - start) / 60
            ts = datetime.now().strftime("%H%M%S")
            print(f"\n=== Wave {wave+1} ({elapsed:.1f} min) ===", flush=True)

            # Scroll to bottom
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(2000)

            # Screenshot
            ss = SS_DIR / f"pipeline_{wave+1:02d}_{ts}.png"
            await page.screenshot(path=str(ss))
            print(f"  Screenshot: {ss.name}", flush=True)

            # Check content
            try:
                info = await page.evaluate(CHECK_CONTENT_JS)
            except Exception as e:
                print(f"  Check error: {e}", flush=True)
                info = {}

            stages = []
            if info.get("hasResearch"):
                stages.append("RESEARCH")
            if info.get("hasAdCopy"):
                stages.append("AD_COPY")
            if info.get("hasImages"):
                stages.append("IMAGES")
            if info.get("hasVideo"):
                stages.append("VIDEO")
            if info.get("hasFocusGroup"):
                stages.append("FOCUS_GROUP")
            if info.get("hasPDF"):
                stages.append("PDF")

            print(f"  Stages: {stages}", flush=True)
            print(f"  Images: {info.get('imageCount', 0)}", flush=True)
            last = info.get("lastLines", "")
            print(f"  Last: {last[:150]}", flush=True)

            # Check completion
            if info.get("hasComplete") or (info.get("hasFocusGroup") and info.get("hasPDF")):
                print(f"\n*** PIPELINE COMPLETE! ***", flush=True)
                await page.screenshot(
                    path=str(SS_DIR / f"COMPLETE_{ts}.png"), full_page=True
                )
                height = await page.evaluate("document.body.scrollHeight")
                for pct in [0, 20, 40, 60, 80, 100]:
                    await page.evaluate(f"window.scrollTo(0, {int(height * pct / 100)})")
                    await page.wait_for_timeout(500)
                    await page.screenshot(
                        path=str(SS_DIR / f"FINAL_scroll{pct}_{ts}.png")
                    )
                break

            # Click continue button
            try:
                await page.evaluate("window.scrollTo(0, 0)")
                await page.wait_for_timeout(500)
                clicked = await page.evaluate(CLICK_CONTINUE_JS)
                if clicked:
                    print(f"  Clicked continue button", flush=True)
                else:
                    print(f"  No continue button - sending via chat", flush=True)
                    inp = await page.query_selector('div[contenteditable="true"]')
                    if inp:
                        await inp.click()
                        await page.keyboard.type("continue", delay=10)
                        await page.keyboard.press("Enter")
                        print(f"  Sent continue via chat", flush=True)
            except Exception as e:
                print(f"  Continue error: {str(e)[:80]}", flush=True)

            # Wait for response
            print(f"  Waiting 30s...", flush=True)
            await page.wait_for_timeout(30000)

        elapsed = (time.time() - start) / 60
        print(f"\n=== DONE — {elapsed:.1f} minutes ===", flush=True)


if __name__ == "__main__":
    asyncio.run(run())

import { chromium } from 'playwright';

const BASE = 'http://localhost:5173';

function sleep(ms) {
  return new Promise(r => setTimeout(r, ms));
}

async function screenshot(page, name) {
  await page.screenshot({ path: `/tmp/screenshot-${name}.png`, fullPage: true });
  console.log(`  -> /tmp/screenshot-${name}.png`);
}

async function main() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });

  try {
    // 1. Trends Page - Campaign tab (default)
    console.log('\n=== Step 1: Campaign Tab ===');
    await page.goto(BASE + '/trends', { waitUntil: 'domcontentloaded', timeout: 15000 });
    await sleep(3000);

    // Fill config
    await page.locator('input[placeholder*="Google Pixel"]').first().fill('Google');
    await page.locator('input[placeholder*="Pixel 9 Pro"]').first().fill('Pixel 9 Pro');
    await page.locator('input[placeholder*="millennials"]').first().fill('Tech enthusiasts 25-40');
    await page.locator('textarea[placeholder*="camera"]').first().fill('AI camera, best display, 7 years of updates');
    await page.locator('button:has-text("Save Configuration")').first().click();
    await sleep(500);
    console.log('  Config saved');
    await screenshot(page, '01-campaign-tab');

    // 2. Switch to Trends tab via evaluate (more reliable)
    console.log('\n=== Step 2: Trends Tab ===');
    const clickedTab = await page.evaluate(() => {
      const buttons = document.querySelectorAll('button');
      for (const btn of buttons) {
        const text = btn.textContent?.trim();
        if (text === 'Trends' || (text?.startsWith('Trends') && text?.includes('('))) {
          btn.click();
          return text;
        }
      }
      return null;
    });
    console.log(`  Clicked tab: "${clickedTab}"`);
    await sleep(1000);

    // Verify tab switched
    const refreshVisible = await page.locator('button:has-text("Refresh Trends")').first().isVisible().catch(() => false);
    console.log(`  Refresh Trends button visible: ${refreshVisible}`);

    const checkboxes = await page.locator('input[type="checkbox"]').all();
    console.log(`  Found ${checkboxes.length} checkboxes`);

    if (checkboxes.length >= 2) {
      await checkboxes[0].click();
      await sleep(200);
      await checkboxes[1].click();
      await sleep(200);
      console.log('  Selected 2 trends');
    }
    await screenshot(page, '02-trends-tab');

    // 3. Switch to Review tab
    console.log('\n=== Step 3: Review Tab ===');
    await page.evaluate(() => {
      const buttons = document.querySelectorAll('button');
      for (const btn of buttons) {
        if (btn.textContent?.trim() === 'Review') { btn.click(); return; }
      }
    });
    await sleep(500);
    await screenshot(page, '03-review-tab');

    // 4. Rating Page
    console.log('\n=== Step 4: Rating Page ===');
    await page.click('a[href="/rating"]');
    await sleep(1000);
    await page.locator('button:has-text("Manage Rubrics")').first().click();
    await sleep(500);
    await page.locator('button:has-text("Activate for Pipeline")').first().click();
    await sleep(500);
    console.log('  Rubric activated');
    await screenshot(page, '04-rubric-activated');

    // 5. Orchestration Page
    console.log('\n=== Step 5: Orchestration Page ===');
    await page.click('a[href="/orchestration"]');
    await sleep(1000);
    await screenshot(page, '05-orchestration');

    const newRunBtn = await page.locator('text=New Run').first().isVisible().catch(() => false);
    const startDisabled = await page.locator('button:has-text("Start Pipeline")').first().isDisabled().catch(() => true);
    console.log(`  New Run button: ${newRunBtn}, Start disabled: ${startDisabled}`);

    console.log('\n=== FULL FLOW TEST COMPLETE ===\n');

  } catch (err) {
    console.error('Test error:', err.message);
    await screenshot(page, 'error');
  } finally {
    await browser.close();
  }
}

main();

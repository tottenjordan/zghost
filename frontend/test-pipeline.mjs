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
    // 1. Setup: Fill config, select trends, activate rubric
    console.log('\n=== Setup: Config + Trends + Rubric ===');
    await page.goto(BASE + '/trends', { waitUntil: 'domcontentloaded', timeout: 15000 });
    await sleep(2000);

    // Fill config
    await page.locator('input[placeholder*="Google Pixel"]').first().fill('Google');
    await page.locator('input[placeholder*="Pixel 9 Pro"]').first().fill('Pixel 9 Pro');
    await page.locator('input[placeholder*="millennials"]').first().fill('Tech enthusiasts 25-40');
    await page.locator('textarea[placeholder*="camera"]').first().fill('AI camera, best display, 7 years of updates');
    await page.locator('button:has-text("Save Configuration")').first().click();
    await sleep(500);
    console.log('  Config saved');

    // Select 2 trends
    const checkboxes = await page.locator('input[type="checkbox"]').all();
    if (checkboxes.length >= 2) {
      await checkboxes[0].click();
      await sleep(200);
      await checkboxes[1].click();
      await sleep(200);
    }
    console.log('  2 trends selected');

    // Activate rubric
    await page.click('a[href="/rating"]');
    await sleep(1000);
    await page.locator('button:has-text("Manage Rubrics")').first().click();
    await sleep(500);
    const activateBtn = page.locator('button:has-text("Activate for Pipeline")').first();
    if (await activateBtn.isVisible().catch(() => false)) {
      await activateBtn.click();
      await sleep(500);
    }
    console.log('  Rubric activated');

    // 2. Go to Orchestration and start pipeline
    console.log('\n=== Starting Pipeline ===');
    await page.click('a[href="/orchestration"]');
    await sleep(1000);
    await screenshot(page, 'pipeline-01-before-start');

    // Verify Start Pipeline is enabled
    const startBtn = page.locator('button:has-text("Start Pipeline")').first();
    const startDisabled = await startBtn.isDisabled().catch(() => true);
    console.log(`  Start Pipeline disabled: ${startDisabled}`);

    if (startDisabled) {
      console.log('  ERROR: Start Pipeline is disabled, cannot proceed');
      await screenshot(page, 'pipeline-error-disabled');
      return;
    }

    // Click Start Pipeline
    await startBtn.click();
    console.log('  Clicked Start Pipeline!');
    await sleep(2000);
    await screenshot(page, 'pipeline-02-started');

    // 3. Monitor pipeline execution
    console.log('\n=== Monitoring Pipeline ===');
    const maxWait = 300000; // 5 minutes max
    const pollInterval = 10000; // check every 10s
    const startTime = Date.now();
    let iteration = 0;

    while (Date.now() - startTime < maxWait) {
      iteration++;
      await sleep(pollInterval);

      // Check current state
      const elapsed = Math.round((Date.now() - startTime) / 1000);

      // Check for events in the event stream
      const eventCount = await page.locator('text=Event Stream').first().textContent().catch(() => '0 events');
      console.log(`  [${elapsed}s] ${eventCount}`);

      // Check timeline for running agents
      const runningAgents = await page.evaluate(() => {
        const pulsingElements = document.querySelectorAll('[class*="animate-pulse"]');
        return pulsingElements.length;
      });
      console.log(`  [${elapsed}s] Running agents (pulsing): ${runningAgents}`);

      // Check session state
      const sessionInfo = await page.locator('text=Session:').first().textContent().catch(() => 'none');
      console.log(`  [${elapsed}s] ${sessionInfo}`);

      // Take periodic screenshots
      if (iteration % 3 === 0) {
        await screenshot(page, `pipeline-03-progress-${elapsed}s`);
      }

      // Check if pipeline completed
      const completedText = await page.locator('text=completed').isVisible().catch(() => false);
      const errorText = await page.locator('text=error').isVisible().catch(() => false);
      const idleStatus = await page.locator('text=Pipeline idle').isVisible().catch(() => false);

      // Check breadcrumb for status change
      const statusChips = await page.evaluate(() => {
        const spans = document.querySelectorAll('span');
        return Array.from(spans)
          .map(s => s.textContent?.trim())
          .filter(t => t && (t.includes('Running') || t.includes('Complete') || t.includes('Error') || t.includes('Idle')))
          .join(', ');
      });
      if (statusChips) console.log(`  [${elapsed}s] Status: ${statusChips}`);

      if (completedText || errorText) {
        console.log(`  Pipeline finished at ${elapsed}s`);
        break;
      }
    }

    await screenshot(page, 'pipeline-04-final');

    // 4. Check results
    console.log('\n=== Checking Results ===');

    // Switch to timeline to see completed agents
    await page.locator('button:has-text("Timeline")').first().click().catch(() => {});
    await sleep(1000);
    await screenshot(page, 'pipeline-05-timeline-final');

    // Check for generated content in the details panel
    const stateTab = page.locator('button:has-text("State")').first();
    if (await stateTab.isVisible().catch(() => false)) {
      await stateTab.click();
      await sleep(1000);
      await screenshot(page, 'pipeline-06-state');
    }

    // Navigate to Narrative page to check generated content
    console.log('\n=== Checking Narrative Page ===');
    await page.click('a[href="/narrative"]').catch(() => {});
    await sleep(1000);
    await screenshot(page, 'pipeline-07-narrative');

    // Navigate to AV Studio to check generated videos
    console.log('\n=== Checking AV Studio Page ===');
    await page.click('a[href="/av-studio"]').catch(() => {});
    await sleep(1000);
    await screenshot(page, 'pipeline-08-av-studio');

    console.log('\n=============================');
    console.log('  PIPELINE TEST COMPLETE');
    console.log('=============================\n');

  } catch (err) {
    console.error('Test error:', err.message);
    await screenshot(page, 'pipeline-error');
  } finally {
    await browser.close();
  }
}

main();

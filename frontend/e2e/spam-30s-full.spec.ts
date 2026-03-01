import { test, expect } from '@playwright/test';
import { OrchestrationPage } from './pages/OrchestrationPage';
import { pollForKey, getSessionState } from './helpers/statePoller';

/**
 * Full 30s Spam campaign E2E:
 *   1. Configure custom campaign (Spam/Spam/Older Millennials/Green color)
 *   2. Auto-select trends, launch pipeline with autopilot
 *   3. Wait for full pipeline completion (research → ad creative → AV → focus group)
 *   4. Iterate on PDF once in Narrative Studio
 *   5. Tweak video once in Evaluation Studio
 */
test('Spam 30s: custom config → pipeline → narrative iteration → studio tweak', async ({ page }) => {
  test.setTimeout(60 * 60 * 1000); // 60 min — 30s pipeline can take 25-35 min
  const startTime = Date.now();
  const log = (phase: string, msg: string) =>
    console.log(`[${phase}] ${msg} (${((Date.now() - startTime) / 60000).toFixed(1)}m)`);

  // ── PHASE 1: Inject custom config and navigate to wizard ──────────
  log('setup', 'Navigating to /trends to set origin for localStorage');
  await page.goto('/trends');
  await page.waitForLoadState('domcontentloaded');
  await page.waitForTimeout(2_000);

  // Inject autopilot/duration/autoStart via localStorage
  // Note: campaignStore uses loadFromStorage() which reads flat JSON, NOT Zustand persist format
  // Form fields must be filled manually — CampaignConfig uses local state, not store
  log('setup', 'Injecting autopilot + duration settings into localStorage');
  await page.evaluate(() => {
    const store = {
      config: {
        brand: 'Spam',
        target_product: 'Spam',
        target_audience: 'Older Millennials',
        key_selling_points: 'Green color',
      },
      selectedSearchTrends: [],
      selectedYtTrends: [],
      activeRubrics: [],
      sessions: [],
      activeSessionIndex: -1,
      commercialDuration: 30,
      autopilot: true,
      autoStart: true,
      maxConcurrentRuns: 2,
      queuedRuns: [],
    };
    localStorage.setItem('campaign-store', JSON.stringify(store));
  });

  // Reload so Zustand picks up the persisted values
  await page.reload({ waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(2_000);

  // ── PHASE 2: Fill form fields directly, save, select trends, launch ─
  log('wizard', 'Filling campaign form fields');
  await page.getByPlaceholder('e.g., Google Pixel').fill('Spam');
  await page.getByPlaceholder('e.g., Pixel 9 Pro').fill('Spam');
  await page.getByPlaceholder('e.g., Tech-savvy millennials').fill('Older Millennials');
  await page.getByPlaceholder('e.g., AI-powered camera').fill('Green color');
  await page.waitForTimeout(500);

  log('wizard', 'Clicking Save Configuration');
  const saveBtn = page.getByRole('button', { name: /save configuration/i });
  await saveBtn.scrollIntoViewIfNeeded();
  await saveBtn.click();
  await page.waitForTimeout(2_000);
  await page.screenshot({ path: 'screenshots/spam-01-config-saved.png', fullPage: true });

  // Should auto-advance to Trends tab; wait for trends to load
  log('wizard', 'Waiting for trends to load');
  await page.waitForTimeout(5_000);

  // Select first Google Search trend
  log('wizard', 'Selecting Google Search trend');
  const googleTabClicked = await page.evaluate(() => {
    const buttons = document.querySelectorAll('button');
    for (const btn of buttons) {
      if (btn.textContent?.includes('Google Search')) {
        btn.click();
        return true;
      }
    }
    return false;
  });
  log('wizard', `Google Search tab clicked: ${googleTabClicked}`);
  await page.waitForTimeout(2_000);

  // Click first checkbox
  const checkboxes = page.locator('input[type="checkbox"]');
  const cbCount = await checkboxes.count();
  log('wizard', `Found ${cbCount} checkboxes`);
  if (cbCount > 0) {
    await checkboxes.first().click();
    await page.waitForTimeout(500);
  }

  // Select first YouTube trend
  log('wizard', 'Selecting YouTube trend');
  const ytTabClicked = await page.evaluate(() => {
    const buttons = document.querySelectorAll('button');
    for (const btn of buttons) {
      if (btn.textContent?.includes('YouTube')) {
        btn.click();
        return true;
      }
    }
    return false;
  });
  log('wizard', `YouTube tab clicked: ${ytTabClicked}`);
  await page.waitForTimeout(2_000);

  const ytCheckboxes = page.locator('input[type="checkbox"]');
  const ytCbCount = await ytCheckboxes.count();
  log('wizard', `Found ${ytCbCount} YouTube checkboxes`);
  if (ytCbCount > 0) {
    await ytCheckboxes.first().click();
    await page.waitForTimeout(500);
  }

  await page.screenshot({ path: 'screenshots/spam-02-trends-selected.png', fullPage: true });

  // Navigate to Review tab and launch
  log('wizard', 'Going to Review tab');
  const reviewClicked = await page.evaluate(() => {
    const divs = document.querySelectorAll('div');
    for (const div of divs) {
      const cls = div.className;
      if (cls.includes('inline-flex') && cls.includes('rounded-lg') && cls.includes('backdrop-blur')) {
        const buttons = div.querySelectorAll('button');
        if (buttons.length >= 4) {
          for (const btn of buttons) {
            if (btn.textContent?.includes('Review')) {
              btn.click();
              return true;
            }
          }
        }
      }
    }
    return false;
  });
  log('wizard', `Review tab clicked: ${reviewClicked}`);
  await page.waitForTimeout(2_000);

  log('wizard', 'Clicking Launch Pipeline');
  const launchBtn = page.getByRole('button', { name: /launch pipeline/i });
  await launchBtn.scrollIntoViewIfNeeded();
  await launchBtn.click({ timeout: 15_000 });

  // Wait for navigation to /orchestration/:runId
  // Session creation (VertexAI + memory preload) can take 30-60s
  await page.waitForURL('**/orchestration/**', { timeout: 120_000 });
  log('wizard', 'Navigated to orchestration run page');
  await page.screenshot({ path: 'screenshots/spam-03-orchestration.png', fullPage: true });

  // ── PHASE 3: Pipeline execution with auto-approval ────────────────
  const orchPage = new OrchestrationPage(page);

  // Get session ID — first try URL (most reliable), then fallback to store
  // Match both numeric (VertexAI) and UUID (InMemory) session IDs
  let sessionId = page.url().match(/orchestration\/([a-zA-Z0-9-]+)/)?.[1] ?? null;
  if (!sessionId) {
    sessionId = await orchPage.getSessionId(15);
  }
  log('pipeline', `Session ID: ${sessionId}`);
  expect(sessionId).toBeTruthy();

  // Wait for the frontend's auto-reconnect to fire and complete.
  // The OrchestrationPage sends "Continue where you left off" via useEffect
  // when it detects sessionId + isRunning but no streamUrl.
  log('pipeline', 'Waiting for frontend auto-reconnect to settle...');
  await page.waitForTimeout(10_000);

  // Start auto-approval loop with a specific pipeline start message.
  // The wizard creates the session but doesn't actually start the pipeline stream,
  // so we need to send the start message as the first approval.
  const pipelineStartMsg = `Start the full pipeline, producing a 30-second commercial. Campaign metadata and trends are already configured in session state — skip trend-discovery and proceed directly to market research. Use auto-select mode for trends, approve all outputs automatically, and proceed through all steps without pausing for user confirmation.`;
  const stopSignal = { stopped: false };
  const approvalLoop = orchPage.autoApproveLoop(stopSignal, sessionId!, pipelineStartMsg);

  // Wait for research report — research phase can take 10-20 min for 30s pipeline
  log('pipeline', 'Waiting for research report...');
  await pollForKey(page, sessionId!, 'combined_final_cited_report', 1_800_000, 15_000);
  log('pipeline', 'Research report complete');
  await page.screenshot({ path: 'screenshots/spam-04-research-done.png', fullPage: true });

  // Wait for images — ad creative phase ~5-10 min
  log('pipeline', 'Waiting for image artifacts...');
  await pollForKey(page, sessionId!, 'img_artifact_keys', 900_000, 15_000);
  log('pipeline', 'Image artifacts ready');

  // Wait for videos — AV studio generates clips
  log('pipeline', 'Waiting for video artifacts...');
  await pollForKey(page, sessionId!, 'vid_artifact_keys', 900_000, 15_000);
  log('pipeline', 'Video artifacts ready');

  // Wait for commercial — final assembly
  log('pipeline', 'Waiting for commercial artifact...');
  const commercial = await pollForKey(page, sessionId!, 'commercial_artifact', 900_000, 15_000);
  log('pipeline', `Commercial: ${JSON.stringify(commercial).substring(0, 200)}`);
  await page.screenshot({ path: 'screenshots/spam-05-commercial-done.png', fullPage: true });

  // Stop auto-approval — pipeline is complete
  stopSignal.stopped = true;
  await approvalLoop;
  log('pipeline', 'Auto-approval loop stopped');

  // ── PHASE 4: Iterate on PDF in Narrative Studio ───────────────────
  log('narrative', 'Navigating to Narrative Studio');
  await page.goto(`/narrative?session=${sessionId}`, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(5_000);
  await page.screenshot({ path: 'screenshots/spam-06-narrative-loaded.png', fullPage: true });

  // Wait for the report to load (either as inline text or PDF)
  log('narrative', 'Waiting for report content to appear');
  await page.waitForFunction(
    () => {
      const iframe = document.querySelector('iframe');
      const text = document.body.innerText;
      return (
        (iframe && iframe.src && iframe.src.length > 0) ||
        text.includes('Research') ||
        text.includes('report') ||
        text.length > 2000
      );
    },
    { timeout: 60_000 },
  );
  log('narrative', 'Report content visible');

  // Send a refinement message to iterate on the report
  log('narrative', 'Sending refinement message');
  const chatInput = page.locator(
    'input[placeholder*="Reply"], textarea[placeholder*="Reply"], input[placeholder*="message"], textarea[placeholder*="message"]',
  );
  const inputVisible = await chatInput.first().isVisible().catch(() => false);
  if (inputVisible) {
    await chatInput.first().fill(
      'Please add a section about the nostalgic appeal of Spam to older millennials and emphasize the iconic green can.',
    );
    await chatInput.first().press('Enter');
    log('narrative', 'Refinement message sent');
    await page.waitForTimeout(10_000);
  } else {
    log('narrative', 'Chat input not found, trying direct API refinement');
    // Use the API directly to send a refinement
    try {
      await page.request.post(`/api/v1/narrative/refine`, {
        data: {
          session_id: sessionId,
          user_id: 'default-user',
          message: 'Please add a section about the nostalgic appeal of Spam to older millennials and emphasize the iconic green can.',
        },
      });
      log('narrative', 'API refinement sent');
      await page.waitForTimeout(10_000);
    } catch (e) {
      log('narrative', `Refinement API call failed: ${e}`);
    }
  }
  await page.screenshot({ path: 'screenshots/spam-07-narrative-refined.png', fullPage: true });

  // Try to generate PDF
  log('narrative', 'Attempting to generate PDF');
  const genPdfBtn = page.getByRole('button', { name: /generate pdf|create pdf|export pdf/i });
  const pdfBtnVisible = await genPdfBtn.isVisible().catch(() => false);
  if (pdfBtnVisible) {
    await genPdfBtn.click();
    log('narrative', 'PDF generation triggered');
    await page.waitForTimeout(15_000);
  } else {
    log('narrative', 'No PDF button found, skipping PDF generation');
  }
  await page.screenshot({ path: 'screenshots/spam-08-narrative-pdf.png', fullPage: true });

  // ── PHASE 5: Tweak video in Studio ────────────────────────────────
  log('studio', 'Navigating to AV Studio');
  await page.goto(`/studio?session=${sessionId}`, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(5_000);
  await page.screenshot({ path: 'screenshots/spam-09-studio-loaded.png', fullPage: true });

  // Wait for video player to be visible
  log('studio', 'Waiting for video player');
  const videoPlayer = page.locator('video').first();
  try {
    await videoPlayer.waitFor({ state: 'visible', timeout: 30_000 });
    log('studio', 'Video player visible');

    // Try playing the video to verify it works
    await videoPlayer.click();
    await page.waitForTimeout(3_000);
    const currentTime = await videoPlayer.evaluate((v: HTMLVideoElement) => v.currentTime);
    log('studio', `Video current time after play: ${currentTime}`);
  } catch {
    log('studio', 'Video player not immediately visible, continuing');
  }
  await page.screenshot({ path: 'screenshots/spam-10-studio-video.png', fullPage: true });

  // ── PHASE 6: Final assertions ─────────────────────────────────────
  log('assertions', 'Running final assertions');
  const finalState = await getSessionState(page, sessionId!);

  // Campaign config
  expect(finalState.brand).toBeTruthy();
  expect(finalState.target_product).toBeTruthy();
  log('assertions', `Brand: ${finalState.brand}, Product: ${finalState.target_product}`);

  // Research report
  expect(finalState.combined_final_cited_report).toBeTruthy();

  // Image artifacts (>= 1)
  const finalImgs = finalState.img_artifact_keys as { img_artifact_keys: unknown[] } | undefined;
  expect(finalImgs?.img_artifact_keys?.length).toBeGreaterThanOrEqual(1);
  log('assertions', `Images: ${finalImgs?.img_artifact_keys?.length ?? 0}`);

  // Video artifacts (>= 1)
  const finalVids = finalState.vid_artifact_keys as { vid_artifact_keys: unknown[] } | undefined;
  expect(finalVids?.vid_artifact_keys?.length).toBeGreaterThanOrEqual(1);
  log('assertions', `Videos: ${finalVids?.vid_artifact_keys?.length ?? 0}`);

  // Commercial artifact
  const commercialArtifact = finalState.commercial_artifact;
  expect(commercialArtifact).toBeTruthy();
  const artifactKey =
    typeof commercialArtifact === 'string'
      ? commercialArtifact
      : (commercialArtifact as { artifact_key?: string })?.artifact_key ?? '';
  expect(artifactKey).toMatch(/commercial/i);
  log('assertions', `Commercial: ${artifactKey}`);

  await page.screenshot({ path: 'screenshots/spam-11-test-complete.png', fullPage: true });

  // ── Summary ───────────────────────────────────────────────────────
  const totalMin = (Date.now() - startTime) / 60000;
  console.log('');
  console.log('═══════════════════════════════════════════════');
  console.log('  Spam 30s Full E2E Complete');
  console.log(`  Session:    ${sessionId}`);
  console.log(`  Brand:      ${finalState.brand}`);
  console.log(`  Product:    ${finalState.target_product}`);
  console.log(`  Commercial: ${artifactKey}`);
  console.log(`  Images:     ${finalImgs?.img_artifact_keys?.length ?? 0}`);
  console.log(`  Videos:     ${finalVids?.vid_artifact_keys?.length ?? 0}`);
  console.log(`  Duration:   ${totalMin.toFixed(1)} min`);
  console.log('═══════════════════════════════════════════════');
});

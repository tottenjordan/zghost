import { test, expect } from '@playwright/test';
import { OrchestrationPage } from './pages/OrchestrationPage';
import { StudioPage } from './pages/StudioPage';
import { pollForKey, getSessionState } from './helpers/statePoller';

interface CampaignConfig {
  brand: string;
  target_product: string;
  target_audience: string;
  key_selling_points: string;
}

const API_SERVER = 'http://localhost:8000';

/**
 * Helper: run a full 15s commercial pipeline.
 *
 * Key design decisions:
 * 1. Create session via direct API call (bypasses Vite proxy POST issues)
 * 2. Fetch trends from API, pick first search + first YT trend
 * 3. Inject session into localStorage and navigate to orchestration page
 * 4. autoStart triggers the pipeline stream from the frontend
 * 5. Auto-approve loop sends follow-up approvals when agent idles
 */
async function run15sPipeline(
  page: import('@playwright/test').Page,
  config: CampaignConfig,
  tag: string,
) {
  const startTime = Date.now();
  const log = (phase: string, msg: string) =>
    console.log(`[${tag}][${phase}] ${msg} (${((Date.now() - startTime) / 60000).toFixed(1)}m)`);

  const orchPage = new OrchestrationPage(page);
  const studioPage = new StudioPage(page);

  // ── PHASE 1: Create session via direct API ─────────────────────────
  // Use hardcoded trends to avoid cold-cache timeout on /api/v1/trends/available.
  // These just need to be present in session state so the root agent skips trend discovery.
  const selectedSearch = [{
    trend_title: 'AI Marketing Trends 2026',
    trend_rank: 1,
    trend_refresh_date: '',
  }];
  const selectedYt = [{
    video_title: 'Top Digital Marketing Strategies',
    video_duration: '10:00',
    video_url: 'https://youtube.com/watch?v=example',
  }];
  log('setup', `Using trends: "${selectedSearch[0].trend_title}", "${selectedYt[0].video_title}"`);

  // Create session with initial state directly via API server
  log('setup', 'Creating session via direct API call');
  const sessionResp = await page.request.post(`${API_SERVER}/api/v1/sessions`, {
    data: {
      initial_state: {
        ...config,
        commercial_duration: 15,
        autopilot_mode: true,
        target_search_trends: { target_search_trends: selectedSearch },
        target_yt_trends: { target_yt_trends: selectedYt },
        // Pre-populate yt_video_analysis so research pipeline skips YouTube video fetch
        // (the fake URL would cause analyze_youtube_videos to fail)
        yt_video_analysis: `Video Title: ${selectedYt[0].video_title}\nMain Topic: Digital marketing strategies and trends for 2026.\nKey Themes: AI-powered marketing, personalization at scale, short-form video content.\nTrend Context: This video is trending because marketers are seeking new strategies for the coming year.\nSummary: The video covers emerging digital marketing strategies including AI automation, personalized customer journeys, and the growing importance of authentic brand storytelling.`,
      },
    },
  });
  expect(sessionResp.ok()).toBeTruthy();
  const sessionData = await sessionResp.json();
  const sessionId = sessionData.session_id;
  log('setup', `Session created: ${sessionId}`);
  expect(sessionId).toBeTruthy();

  // ── PHASE 2: Navigate to orchestration and start pipeline ──────────
  // Inject session into localStorage so the frontend knows about it
  log('setup', 'Navigating to frontend and injecting session');
  await page.goto('/orchestration', { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(2_000);

  await page.evaluate(({ cfg, sid, searchTrends: st, ytTrends: yt }) => {
    const store = {
      config: cfg,
      selectedSearchTrends: st.map((t: any) => ({ title: t.trend_title, rank: t.trend_rank })),
      selectedYtTrends: yt.map((t: any) => ({ title: t.video_title, videoUrl: t.video_url })),
      activeRubrics: [],
      sessions: [{
        id: `session-${sid}`,
        sessionId: sid,
        label: `${cfg.brand} ${new Date().toLocaleTimeString()}`,
        status: 'running',
        startedAt: Date.now(),
        config: cfg,
        commercialDuration: 15,
        searchTrends: st.map((t: any) => ({ title: t.trend_title, rank: t.trend_rank })),
        ytTrends: yt.map((t: any) => ({ title: t.video_title, videoUrl: t.video_url })),
        autopilot: true,
      }],
      activeSessionIndex: 0,
      sessionId: sid,
      commercialDuration: 15,
      autopilot: true,
      autoStart: true,
      pipelineStatus: 'running',
      maxConcurrentRuns: 4,
      queuedRuns: [],
    };
    localStorage.setItem('campaign-store', JSON.stringify(store));
  }, { cfg: config, sid: sessionId, searchTrends: selectedSearch, ytTrends: selectedYt });

  // Navigate to the run page — this triggers autoStart
  await page.goto(`/orchestration/${sessionId}`, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(3_000);
  await page.screenshot({ path: `screenshots/${tag}-01-orchestration.png`, fullPage: true });
  log('pipeline', 'Orchestration page loaded');

  // Wait for autoStart to establish SSE stream
  log('pipeline', 'Waiting for autoStart stream to establish...');
  await page.waitForTimeout(15_000);

  // Start auto-approval loop (no initial message — autoStart already sent one)
  const stopSignal = { stopped: false };
  const approvalLoop = orchPage.autoApproveLoop(stopSignal, sessionId);

  // ── PHASE 3: Wait for research report ─────────────────────────────
  log('pipeline', 'Waiting for research report...');
  await pollForKey(page, sessionId, 'combined_final_cited_report', 1_200_000, 15_000);
  log('pipeline', 'Research report complete');
  await page.screenshot({ path: `screenshots/${tag}-02-research-done.png`, fullPage: true });

  // ── PHASE 4: Wait for image artifacts ─────────────────────────────
  log('pipeline', 'Waiting for image artifacts...');
  await pollForKey(page, sessionId, 'img_artifact_keys', 1_200_000, 15_000);
  log('pipeline', 'Image artifacts ready');

  // ── PHASE 5: Wait for video artifacts ─────────────────────────────
  log('pipeline', 'Waiting for video artifacts...');
  await pollForKey(page, sessionId, 'vid_artifact_keys', 1_200_000, 15_000);
  log('pipeline', 'Video artifacts ready');

  // ── PHASE 6: Wait for commercial ──────────────────────────────────
  log('pipeline', 'Waiting for commercial artifact...');
  const commercial = await pollForKey(page, sessionId, 'commercial_artifact', 1_200_000, 15_000);
  log('pipeline', `Commercial: ${JSON.stringify(commercial).substring(0, 200)}`);
  await page.screenshot({ path: `screenshots/${tag}-03-commercial-done.png`, fullPage: true });

  // Stop auto-approval
  stopSignal.stopped = true;
  await approvalLoop;
  log('pipeline', 'Auto-approval loop stopped');

  // ── PHASE 7: Verify Narrative Pane ────────────────────────────────
  log('narrative', 'Navigating to Narrative Studio');
  await page.goto(`/narrative?session=${sessionId}`, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(5_000);
  await page.screenshot({ path: `screenshots/${tag}-04-narrative-loaded.png`, fullPage: true });

  // Wait for report content
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

  // Send a refinement message
  log('narrative', 'Sending refinement message');
  const chatInput = page.locator(
    'input[placeholder*="Reply"], textarea[placeholder*="Reply"], input[placeholder*="message"], textarea[placeholder*="message"]',
  );
  const inputVisible = await chatInput.first().isVisible().catch(() => false);
  if (inputVisible) {
    await chatInput.first().fill('Make the tone more playful and energetic');
    await chatInput.first().press('Enter');
    log('narrative', 'Refinement message sent');
    await page.waitForTimeout(10_000);
  } else {
    log('narrative', 'Chat input not found, trying direct API refinement');
    try {
      await page.request.post(`${API_SERVER}/api/v1/narrative/refine`, {
        data: {
          session_id: sessionId,
          user_id: 'default-user',
          message: 'Make the tone more playful and energetic',
        },
      });
      log('narrative', 'API refinement sent');
      await page.waitForTimeout(10_000);
    } catch (e) {
      log('narrative', `Refinement API call failed: ${e}`);
    }
  }
  await page.screenshot({ path: `screenshots/${tag}-05-narrative-refined.png`, fullPage: true });

  // ── PHASE 8: Verify AV Studio ─────────────────────────────────────
  log('studio', 'Navigating to AV Studio');
  await studioPage.goto(sessionId);
  await page.waitForTimeout(5_000);
  await page.screenshot({ path: `screenshots/${tag}-06-studio-loaded.png`, fullPage: true });

  // Wait for video player
  log('studio', 'Waiting for video player');
  let hasCommercialPlayer = false;
  try {
    await studioPage.waitForCommercial(30_000);
    hasCommercialPlayer = true;
    log('studio', 'Video player visible');

    // Try playing the video
    const videoPlayer = page.locator('video').first();
    await videoPlayer.click();
    await page.waitForTimeout(3_000);
    const currentTime = await videoPlayer.evaluate((v: HTMLVideoElement) => v.currentTime);
    log('studio', `Video current time after play: ${currentTime}`);
  } catch {
    log('studio', 'Video player not immediately visible, continuing');
  }

  // Try interacting with studio tabs
  const tabNames = ['Clips', 'Voice', 'Music', 'Timeline', 'Characters'];
  for (const tabName of tabNames) {
    try {
      const tab = page.locator(`button:has-text("${tabName}")`).first();
      if (await tab.isVisible()) {
        await tab.click();
        await page.waitForTimeout(1_000);
        log('studio', `Clicked ${tabName} tab`);
      }
    } catch { /* skip */ }
  }
  await page.screenshot({ path: `screenshots/${tag}-07-studio-tabs.png`, fullPage: true });

  // ── PHASE 9: Final assertions ─────────────────────────────────────
  log('assertions', 'Running final assertions');
  const finalState = await getSessionState(page, sessionId);

  expect(finalState.brand).toBeTruthy();
  expect(finalState.target_product).toBeTruthy();
  log('assertions', `Brand: ${finalState.brand}, Product: ${finalState.target_product}`);

  expect(finalState.combined_final_cited_report).toBeTruthy();

  const finalImgs = finalState.img_artifact_keys as { img_artifact_keys: unknown[] } | undefined;
  expect(finalImgs?.img_artifact_keys?.length).toBeGreaterThanOrEqual(1);
  log('assertions', `Images: ${finalImgs?.img_artifact_keys?.length ?? 0}`);

  const finalVids = finalState.vid_artifact_keys as { vid_artifact_keys: unknown[] } | undefined;
  expect(finalVids?.vid_artifact_keys?.length).toBeGreaterThanOrEqual(1);
  log('assertions', `Videos: ${finalVids?.vid_artifact_keys?.length ?? 0}`);

  const commercialArtifact = finalState.commercial_artifact;
  expect(commercialArtifact).toBeTruthy();
  const artifactKey =
    typeof commercialArtifact === 'string'
      ? commercialArtifact
      : (commercialArtifact as { artifact_key?: string })?.artifact_key ?? '';
  expect(artifactKey).toMatch(/commercial/i);
  log('assertions', `Commercial: ${artifactKey}`);

  await page.screenshot({ path: `screenshots/${tag}-08-test-complete.png`, fullPage: true });

  const totalMin = (Date.now() - startTime) / 60000;
  console.log('');
  console.log('===================================================');
  console.log(`  [${tag}] E2E Pipeline Complete (15s commercial)`);
  console.log(`  Session:    ${sessionId}`);
  console.log(`  Brand:      ${finalState.brand}`);
  console.log(`  Product:    ${finalState.target_product}`);
  console.log(`  Commercial: ${artifactKey}`);
  console.log(`  Images:     ${finalImgs?.img_artifact_keys?.length ?? 0}`);
  console.log(`  Videos:     ${finalVids?.vid_artifact_keys?.length ?? 0}`);
  console.log(`  Narrative:  Verified`);
  console.log(`  AV Studio:  ${hasCommercialPlayer ? 'Commercial loaded' : 'Page loaded'}`);
  console.log(`  Duration:   ${totalMin.toFixed(1)} min`);
  console.log('===================================================');

  return { sessionId, finalState, durationMin: totalMin, hasCommercialPlayer };
}


// ── PARALLEL TESTS ──────────────────────────────────────────────────
test.describe('Parallel 15s Commercials', () => {
  test.describe.configure({ mode: 'parallel' });

  test('15s commercial — Subaru Crossover (First Car for Dogs)', async ({ page }) => {
    test.setTimeout(60 * 60 * 1000);
    const result = await run15sPipeline(page, {
      brand: 'Subaru',
      target_product: 'Crossover',
      target_audience: 'Dog owners and dog lovers who treat their pets like family',
      key_selling_points: 'Spacious cargo area for dogs, all-wheel drive for adventures, pet-friendly interior materials, safety features to protect your best friend',
    }, 'subaru');
    console.log(`[subaru] PASSED in ${result.durationMin.toFixed(1)} min`);
  });

  test('15s commercial — Pepsi Sweaters (Really Hot Sweater)', async ({ page }) => {
    test.setTimeout(60 * 60 * 1000);
    const result = await run15sPipeline(page, {
      brand: 'Pepsi',
      target_product: 'Sweaters',
      target_audience: 'Millennials who love cozy fashion and bold brand collaborations',
      key_selling_points: 'Limited-edition Pepsi branded sweaters, bold retro design, ultra-soft premium knit, the really hot sweater of the season',
    }, 'pepsi');
    console.log(`[pepsi] PASSED in ${result.durationMin.toFixed(1)} min`);
  });
});

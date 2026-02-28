import { test, expect } from '@playwright/test';
import { TrendsPage } from './pages/TrendsPage';
import { OrchestrationPage } from './pages/OrchestrationPage';
import { StudioPage } from './pages/StudioPage';
import { pollForKey, getSessionState } from './helpers/statePoller';

/**
 * Helper: run a full 10s commercial pipeline with a given preset.
 * Returns the session ID and final state on success.
 */
async function run10sPipeline(
  page: import('@playwright/test').Page,
  presetLabel: string,
  tag: string,
) {
  const pipelineStartTime = Date.now();
  const trendsPage = new TrendsPage(page);
  const orchPage = new OrchestrationPage(page);
  const studioPage = new StudioPage(page);

  // ── PHASE 1: Setup ──────────────────────────────────────────────────
  console.log(`[${tag}][phase-1] Navigating to /trends, loading preset "${presetLabel}"`);
  await trendsPage.goto();
  await trendsPage.loadPresetAndSave(presetLabel);
  await trendsPage.screenshot(`${tag}-01-trends-page`);

  console.log(`[${tag}][phase-1] Selecting Google and YouTube trends`);
  await trendsPage.selectGoogleTrend(0);
  await trendsPage.selectYouTubeTrend(0);
  await trendsPage.screenshot(`${tag}-01b-trends-selected`);

  // Set commercial duration to 10s and autoStart flag in localStorage,
  // then do a full page navigation so the zustand store re-initializes
  // from localStorage with the correct values. The wizard's SPA navigation
  // would use the in-memory store (default 30s) since localStorage updates
  // aren't picked up by an already-mounted store.
  console.log(`[${tag}][phase-1] Setting duration=10s and autoStart in localStorage`);
  await page.evaluate(() => {
    try {
      const raw = localStorage.getItem('campaign-store');
      if (raw) {
        const store = JSON.parse(raw);
        store.commercialDuration = 10;
        store.autopilot = true;
        store.autoStart = true;
        localStorage.setItem('campaign-store', JSON.stringify(store));
      }
    } catch { /* ignore */ }
  });

  console.log(`[${tag}][phase-1] Navigating to /orchestration (full page load)`);
  await page.goto('/orchestration', { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(3_000); // allow React to mount and autoStart to fire
  console.log(`[${tag}][phase-1] Navigated to /orchestration`);

  // ── PHASE 2: Pipeline execution with auto-approval ──────────────────
  console.log(`[${tag}][phase-2] Waiting for pipeline auto-start`);

  await orchPage.startPipelineIfNeeded();
  await orchPage.screenshot(`${tag}-02-pipeline-started`);

  // Get session ID
  const sessionId = await orchPage.getSessionId(15);
  console.log(`[${tag}][phase-2] Session ID: ${sessionId}`);
  expect(sessionId).toBeTruthy();

  // Start auto-approval loop in background
  const stopSignal = { stopped: false };
  const approvalLoop = orchPage.autoApproveLoop(stopSignal, sessionId!);

  // ── PHASE 3: Wait for research report ─────────────────────────────
  console.log(`[${tag}][phase-3] Waiting for research report...`);
  await pollForKey(page, sessionId!, 'combined_final_cited_report', 600_000);
  await orchPage.screenshot(`${tag}-03-research-complete`);
  console.log(`[${tag}][phase-3] Research report complete`);

  // ── PHASE 4: Wait for image artifacts ─────────────────────────────
  console.log(`[${tag}][phase-4] Waiting for image artifacts...`);
  await pollForKey(page, sessionId!, 'img_artifact_keys', 600_000, 10_000);
  console.log(`[${tag}][phase-4] Image artifacts ready`);
  await orchPage.screenshot(`${tag}-04-images-done`);

  // ── PHASE 5: Wait for video artifacts ─────────────────────────────
  console.log(`[${tag}][phase-5] Waiting for video artifacts...`);
  await pollForKey(page, sessionId!, 'vid_artifact_keys', 600_000, 10_000);
  console.log(`[${tag}][phase-5] Video artifacts ready`);
  await orchPage.screenshot(`${tag}-05-videos-done`);

  // ── PHASE 6: Wait for commercial ──────────────────────────────────
  console.log(`[${tag}][phase-6] Waiting for commercial artifact...`);
  const commercial = await pollForKey(page, sessionId!, 'commercial_artifact', 600_000, 10_000);
  console.log(`[${tag}][phase-6] Commercial artifact:`, JSON.stringify(commercial).substring(0, 200));
  await orchPage.screenshot(`${tag}-06-commercial-generated`);

  // Navigate to studio to verify
  await studioPage.goto(sessionId!);
  try {
    await studioPage.waitForCommercial(30_000);
    await studioPage.screenshot(`${tag}-07-studio-view`);
    console.log(`[${tag}][phase-6] Studio loaded with video player`);
  } catch {
    console.log(`[${tag}][phase-6] Studio video player not immediately visible`);
    await studioPage.screenshot(`${tag}-07-studio-fallback`);
  }

  // ── PHASE 7: Wait for focus group ─────────────────────────────────
  console.log(`[${tag}][phase-7] Waiting for focus group...`);
  await orchPage.goto();
  try {
    await pollForKey(page, sessionId!, 'focus_group_evaluation', 300_000, 10_000);
    console.log(`[${tag}][phase-7] Focus group evaluation complete`);
  } catch {
    console.log(`[${tag}][phase-7] Focus group key not found, continuing`);
  }
  await orchPage.screenshot(`${tag}-08-focus-group-done`);

  // ── PHASE 8: Final assertions ─────────────────────────────────────
  console.log(`[${tag}][phase-8] Running final assertions`);
  stopSignal.stopped = true;
  await approvalLoop;

  const finalState = await getSessionState(page, sessionId!);

  expect(finalState.brand).toBeTruthy();
  expect(finalState.target_product).toBeTruthy();
  expect(finalState.combined_final_cited_report).toBeTruthy();

  const finalImgs = finalState.img_artifact_keys as { img_artifact_keys: unknown[] } | undefined;
  expect(finalImgs?.img_artifact_keys?.length).toBeGreaterThanOrEqual(2);

  const finalVids = finalState.vid_artifact_keys as { vid_artifact_keys: unknown[] } | undefined;
  expect(finalVids?.vid_artifact_keys?.length).toBeGreaterThanOrEqual(2);

  const commercialArtifact = finalState.commercial_artifact;
  expect(commercialArtifact).toBeTruthy();
  const artifactKey =
    typeof commercialArtifact === 'string'
      ? commercialArtifact
      : (commercialArtifact as { artifact_key?: string })?.artifact_key ?? '';
  expect(artifactKey).toMatch(/commercial/i);

  await orchPage.screenshot(`${tag}-09-test-complete`);

  const totalDurationMin = (Date.now() - pipelineStartTime) / 60000;
  console.log('');
  console.log(`═══════════════════════════════════════════`);
  console.log(`  [${tag}] E2E Pipeline Complete`);
  console.log(`  Session:    ${sessionId}`);
  console.log(`  Commercial: ${artifactKey}`);
  console.log(`  Images:     ${finalImgs?.img_artifact_keys?.length ?? 0}`);
  console.log(`  Videos:     ${finalVids?.vid_artifact_keys?.length ?? 0}`);
  console.log(`  Duration:   ${totalDurationMin.toFixed(1)} min`);
  if (totalDurationMin > 15) {
    console.warn(`  ⚠ Pipeline exceeded 15-min target (took ${totalDurationMin.toFixed(1)} min)`);
  }
  console.log(`═══════════════════════════════════════════`);

  return { sessionId, finalState, durationMin: totalDurationMin };
}


// ── PARALLEL TESTS ──────────────────────────────────────────────────
// These two tests run in parallel (different browser contexts)

test.describe('Parallel 10s Commercials', () => {
  test.describe.configure({ mode: 'parallel' });

  test('10s commercial — Google Pixel 9 Pro', async ({ page }) => {
    test.setTimeout(45 * 60 * 1000);
    const result = await run10sPipeline(page, 'Google Pixel 9 Pro', 'pixel');
    console.log(`[pixel] PASSED in ${result.durationMin.toFixed(1)} min`);
  });

  test('10s commercial — Nike Air Max', async ({ page }) => {
    test.setTimeout(45 * 60 * 1000);
    const result = await run10sPipeline(page, 'Nike Air Max', 'nike');
    console.log(`[nike] PASSED in ${result.durationMin.toFixed(1)} min`);
  });
});

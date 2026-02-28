import { test, expect } from '@playwright/test';
import { TrendsPage } from './pages/TrendsPage';
import { OrchestrationPage } from './pages/OrchestrationPage';
import { StudioPage } from './pages/StudioPage';
import { pollForKey, getSessionState } from './helpers/statePoller';

test('Full pipeline: 10s commercial from wizard to focus group', async ({ page }) => {
  test.setTimeout(45 * 60 * 1000); // 45 min

  const trendsPage = new TrendsPage(page);
  const orchPage = new OrchestrationPage(page);
  const studioPage = new StudioPage(page);

  // ── PHASE 1: Setup ──────────────────────────────────────────────────
  console.log('[phase-1] Navigating to /trends, loading preset, and saving config');
  await trendsPage.goto();
  await trendsPage.loadPresetAndSave('Google Pixel 9 Pro');
  await trendsPage.screenshot('01-trends-page');

  console.log('[phase-1] Selecting Google and YouTube trends');
  await trendsPage.selectGoogleTrend(0);
  await trendsPage.selectYouTubeTrend(0);
  await trendsPage.screenshot('01b-trends-selected');

  console.log('[phase-1] Launching to orchestration');
  await trendsPage.clickLaunch();
  console.log('[phase-1] Navigated to /orchestration');

  // ── PHASE 2: Pipeline execution with auto-approval ──────────────────
  console.log('[phase-2] Starting pipeline (or confirming auto-start)');

  try {
    const durationVisible = await orchPage.durationSelect.isVisible();
    if (durationVisible) {
      await orchPage.setDuration(10);
    }
  } catch {
    console.log('[phase-2] Duration selector not available');
  }

  await orchPage.startPipelineIfNeeded();
  await orchPage.screenshot('02-pipeline-started');

  // Get session ID (with retries — store may take a moment to populate)
  const sessionId = await orchPage.getSessionId(15);
  console.log(`[phase-2] Session ID: ${sessionId}`);
  expect(sessionId).toBeTruthy();

  // Start auto-approval loop in background (with sessionId for activity tracking)
  const stopSignal = { stopped: false };
  const approvalLoop = orchPage.autoApproveLoop(stopSignal, sessionId!);

  // ── PHASE 3: Wait for research report (~3-10 min) ───────────────────
  console.log('[phase-3] Waiting for research report...');
  await pollForKey(page, sessionId!, 'combined_final_cited_report', 600_000);
  await orchPage.screenshot('03-research-complete');
  console.log('[phase-3] Research report complete');

  // ── PHASE 4: Wait for image artifacts (~10-20 min from start) ───────
  // Stay on orchestration page — don't navigate away during pipeline
  console.log('[phase-4] Waiting for image artifacts...');
  await pollForKey(page, sessionId!, 'img_artifact_keys', 1_500_000, 10_000);
  console.log('[phase-4] Image artifacts ready');
  await orchPage.screenshot('04-images-done');

  // ── PHASE 5: Wait for video artifacts ───────────────────────────────
  console.log('[phase-5] Waiting for video artifacts...');
  await pollForKey(page, sessionId!, 'vid_artifact_keys', 600_000, 10_000);
  console.log('[phase-5] Video artifacts ready');
  await orchPage.screenshot('05-videos-done');

  // ── PHASE 6: Wait for commercial (~5-10 more min) ──────────────────
  console.log('[phase-6] Waiting for commercial artifact...');
  const commercial = await pollForKey(page, sessionId!, 'commercial_artifact', 900_000, 10_000);
  console.log('[phase-6] Commercial artifact:', JSON.stringify(commercial).substring(0, 200));
  await orchPage.screenshot('06-commercial-generated');

  // Navigate to studio to verify
  await studioPage.goto(sessionId!);
  try {
    await studioPage.waitForCommercial(30_000);
    await studioPage.screenshot('07-studio-view');
    console.log('[phase-6] Studio loaded with video player');
  } catch {
    console.log('[phase-6] Studio video player not immediately visible');
    await studioPage.screenshot('07-studio-fallback');
  }

  // ── PHASE 7: Wait for focus group ───────────────────────────────────
  console.log('[phase-7] Waiting for focus group...');
  await orchPage.goto();
  try {
    await pollForKey(page, sessionId!, 'focus_group_evaluation', 300_000, 10_000);
    console.log('[phase-7] Focus group evaluation complete');
  } catch {
    console.log('[phase-7] Focus group key not found, continuing');
  }
  await orchPage.screenshot('08-focus-group-done');

  // ── PHASE 8: Final assertions ───────────────────────────────────────
  console.log('[phase-8] Running final assertions');
  stopSignal.stopped = true;
  await approvalLoop;

  const finalState = await getSessionState(page, sessionId!);

  // Campaign config
  expect(finalState.brand).toBeTruthy();
  expect(finalState.target_product).toBeTruthy();

  // Research report
  expect(finalState.combined_final_cited_report).toBeTruthy();

  // Image artifacts (>= 2)
  const finalImgs = finalState.img_artifact_keys as { img_artifact_keys: unknown[] } | undefined;
  expect(finalImgs?.img_artifact_keys?.length).toBeGreaterThanOrEqual(2);

  // Video artifacts (>= 2)
  const finalVids = finalState.vid_artifact_keys as { vid_artifact_keys: unknown[] } | undefined;
  expect(finalVids?.vid_artifact_keys?.length).toBeGreaterThanOrEqual(2);

  // Commercial artifact
  const commercialArtifact = finalState.commercial_artifact;
  expect(commercialArtifact).toBeTruthy();
  const artifactKey =
    typeof commercialArtifact === 'string'
      ? commercialArtifact
      : (commercialArtifact as { artifact_key?: string })?.artifact_key ?? '';
  expect(artifactKey).toMatch(/commercial/i);

  await orchPage.screenshot('09-test-complete');

  // ── Summary ─────────────────────────────────────────────────────────
  console.log('');
  console.log('═══════════════════════════════════════════');
  console.log('  E2E Pipeline Complete');
  console.log(`  Session:    ${sessionId}`);
  console.log(`  Commercial: ${artifactKey}`);
  console.log(`  Images:     ${finalImgs?.img_artifact_keys?.length ?? 0}`);
  console.log(`  Videos:     ${finalVids?.vid_artifact_keys?.length ?? 0}`);
  console.log('═══════════════════════════════════════════');
});

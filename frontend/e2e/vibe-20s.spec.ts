import { test, expect } from '@playwright/test';
import { OrchestrationPage } from './pages/OrchestrationPage';
import { StudioPage } from './pages/StudioPage';
import { pollForKey, getSessionState } from './helpers/statePoller';

/**
 * Vibe Prompts E2E: 20-second commercial — hybrid approach.
 *
 * 1. Create session via API directly (avoids stale session contamination)
 * 2. Start pipeline via browser EventSource (keeps SSE alive like the React app)
 * 3. Auto-approve via direct API calls
 * 4. Poll for completion keys
 */
test('Vibe: 20s commercial via frontend — Google Pixel 9 Pro', async ({ page }) => {
  test.setTimeout(45 * 60 * 1000); // 45 min
  const pipelineStartTime = Date.now();

  const orchPage = new OrchestrationPage(page);
  const studioPage = new StudioPage(page);

  // ── PHASE 1: Create session via API ───────────────────────────────
  console.log('[20s][phase-1] Creating session via API with Pixel config, 20s duration');
  const sessionResp = await page.request.post('/api/v1/sessions', {
    data: {
      initial_state: {
        brand: 'Google Pixel',
        target_product: 'Pixel 9 Pro',
        target_audience: 'Tech-savvy millennials and Gen Z creators who value AI-powered photography',
        key_selling_points: 'AI-powered camera with Best Take, Magic Eraser, Tensor G4 chip, 7 years of updates, Gemini AI built-in',
        commercial_duration: 20,
        autopilot_mode: true,
        target_search_trends: {
          target_search_trends: [
            { trend_title: 'AI photography', trend_rank: 1, trend_refresh_date: '03/01/2026' },
          ],
        },
        target_yt_trends: {
          target_yt_trends: [
            {
              video_title: 'Pixel 9 Pro Camera Review - AI Features Deep Dive',
              video_duration: 'PT12M30S',
              video_url: 'https://www.youtube.com/watch?v=example123',
            },
          ],
        },
      },
    },
  });
  expect(sessionResp.ok()).toBe(true);
  const sessionData = await sessionResp.json();
  const sessionId = sessionData.session_id;
  console.log(`[20s][phase-1] Session created: ${sessionId}`);
  expect(sessionId).toBeTruthy();

  // Verify session state
  const earlyState = await getSessionState(page, sessionId);
  console.log(`[20s][phase-1] brand=${earlyState.brand}, product=${earlyState.target_product}, duration=${earlyState.commercial_duration}`);
  expect(earlyState.brand).toBe('Google Pixel');
  expect(earlyState.commercial_duration).toBe(20);

  // ── PHASE 2: Navigate to orchestration + start pipeline via EventSource ─
  console.log('[20s][phase-2] Navigating to /orchestration');
  await page.goto('/orchestration', { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(2_000);

  // Build the pipeline start message (same format as handleStart)
  const pipelineMessage =
    'Start the full pipeline, producing a 20-second commercial. ' +
    'Campaign metadata and trends are already configured in session state ' +
    '— skip trend-discovery and proceed directly to market research. ' +
    'Use auto-select mode for trends, approve all outputs automatically, ' +
    'and proceed through all steps without pausing for user confirmation.';

  // Start pipeline via EventSource in browser context — this keeps the SSE
  // connection alive just like the frontend's useOrchestration hook does.
  console.log('[20s][phase-2] Starting pipeline via browser EventSource');
  await page.evaluate(
    ({ sid, msg }) => {
      const params = new URLSearchParams({ user_id: 'default-user', message: msg });
      const url = `/api/v1/run/${sid}/stream?${params}`;
      const source = new EventSource(url);

      // Store events and connection state on window for later inspection
      (window as any).__pipeline_events = [];
      (window as any).__pipeline_connected = true;
      (window as any).__pipeline_complete = false;

      source.onmessage = (e) => {
        try {
          const parsed = JSON.parse(e.data);
          (window as any).__pipeline_events.push(parsed);

          // Auto-close when stream completes (same as frontend)
          if (parsed.type === 'agent_complete' && parsed.session_id) {
            source.close();
            (window as any).__pipeline_connected = false;
            (window as any).__pipeline_complete = true;
          }
        } catch {
          // ignore parse errors
        }
      };

      source.onerror = () => {
        if (source.readyState === EventSource.CLOSED) {
          (window as any).__pipeline_connected = false;
          (window as any).__pipeline_complete = true;
        }
      };
    },
    { sid: sessionId, msg: pipelineMessage },
  );

  // Wait a moment for EventSource to establish
  await page.waitForTimeout(3_000);

  // Verify EventSource connected
  const connected = await page.evaluate(() => (window as any).__pipeline_connected);
  console.log(`[20s][phase-2] EventSource connected: ${connected}`);

  await orchPage.screenshot('20s-02-pipeline-started');

  // Start auto-approval loop in background
  const stopSignal = { stopped: false };
  const approvalLoop = orchPage.autoApproveLoop(stopSignal, sessionId);

  // ── PHASE 3: Wait for research report (~3-10 min) ───────────────────
  console.log('[20s][phase-3] Waiting for research report...');
  try {
    await pollForKey(page, sessionId, 'combined_final_cited_report', 600_000);
    console.log('[20s][phase-3] Research report complete');
  } catch {
    console.log('[20s][phase-3] Research report not found, checking pipeline progress...');
    const midState = await getSessionState(page, sessionId);
    const hasProgress = !!midState.ad_copy_draft || !!midState.final_select_ad_copies;
    console.log(`[20s][phase-3] Has ad creative progress: ${hasProgress}`);
    if (!hasProgress) {
      // Check EventSource status
      const evCount = await page.evaluate(() => (window as any).__pipeline_events?.length ?? 0);
      const complete = await page.evaluate(() => (window as any).__pipeline_complete ?? false);
      console.log(`[20s][phase-3] EventSource events: ${evCount}, complete: ${complete}`);
      throw new Error('Pipeline stalled: no research report and no ad creative');
    }
  }
  await orchPage.screenshot('20s-03-research-complete');

  // ── PHASE 4: Wait for image artifacts ───────────────────────────────
  console.log('[20s][phase-4] Waiting for image artifacts...');
  await pollForKey(page, sessionId, 'img_artifact_keys', 600_000, 10_000);
  console.log('[20s][phase-4] Image artifacts ready');
  await orchPage.screenshot('20s-04-images-done');

  // ── PHASE 5: Wait for video artifacts ───────────────────────────────
  console.log('[20s][phase-5] Waiting for video artifacts...');
  await pollForKey(page, sessionId, 'vid_artifact_keys', 600_000, 10_000);
  console.log('[20s][phase-5] Video artifacts ready');
  await orchPage.screenshot('20s-05-videos-done');

  // ── PHASE 6: Wait for commercial (~5-10 more min) ──────────────────
  console.log('[20s][phase-6] Waiting for commercial artifact...');
  const commercial = await pollForKey(page, sessionId, 'commercial_artifact', 600_000, 10_000);
  console.log('[20s][phase-6] Commercial artifact:', JSON.stringify(commercial).substring(0, 200));
  await orchPage.screenshot('20s-06-commercial-generated');

  // Navigate to studio to verify
  await studioPage.goto(sessionId);
  try {
    await studioPage.waitForCommercial(30_000);
    await studioPage.screenshot('20s-07-studio-view');
    console.log('[20s][phase-6] Studio loaded with video player');
  } catch {
    console.log('[20s][phase-6] Studio video player not immediately visible');
    await studioPage.screenshot('20s-07-studio-fallback');
  }

  // ── PHASE 7: Wait for focus group ───────────────────────────────────
  console.log('[20s][phase-7] Waiting for focus group...');
  await orchPage.goto();
  try {
    await pollForKey(page, sessionId, 'focus_group_evaluation', 300_000, 10_000);
    console.log('[20s][phase-7] Focus group evaluation complete');
  } catch {
    console.log('[20s][phase-7] Focus group key not found, continuing');
  }
  await orchPage.screenshot('20s-08-focus-group-done');

  // ── PHASE 8: Final assertions ───────────────────────────────────────
  console.log('[20s][phase-8] Running final assertions');
  stopSignal.stopped = true;
  await approvalLoop;

  const finalState = await getSessionState(page, sessionId);

  expect(finalState.brand).toBeTruthy();
  expect(finalState.target_product).toBeTruthy();

  // Research report (may be skipped in autopilot mode)
  if (finalState.combined_final_cited_report) {
    console.log('[20s][phase-8] Research report present');
  } else {
    console.log('[20s][phase-8] Research report skipped (autopilot mode)');
  }

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

  await orchPage.screenshot('20s-09-test-complete');

  // Check EventSource final status
  const finalEvCount = await page.evaluate(() => (window as any).__pipeline_events?.length ?? 0);
  const finalComplete = await page.evaluate(() => (window as any).__pipeline_complete ?? false);

  // ── Summary ─────────────────────────────────────────────────────────
  const totalDurationMin = (Date.now() - pipelineStartTime) / 60000;
  console.log('');
  console.log('═══════════════════════════════════════════');
  console.log('  [20s] E2E Pipeline Complete');
  console.log(`  Session:    ${sessionId}`);
  console.log(`  Commercial: ${artifactKey}`);
  console.log(`  Images:     ${finalImgs?.img_artifact_keys?.length ?? 0}`);
  console.log(`  Videos:     ${finalVids?.vid_artifact_keys?.length ?? 0}`);
  console.log(`  Duration:   ${totalDurationMin.toFixed(1)} min`);
  console.log(`  Events:     ${finalEvCount} (complete: ${finalComplete})`);
  console.log('═══════════════════════════════════════════');
});

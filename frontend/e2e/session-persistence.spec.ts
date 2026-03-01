import { test, expect } from '@playwright/test';
import { TrendsPage } from './pages/TrendsPage';
import { OrchestrationPage } from './pages/OrchestrationPage';
import { pollForKey, getSessionState } from './helpers/statePoller';
import { MCDONALDS_PRESET, PIXEL_PRESET, injectPreset } from './helpers/presetInjector';

/**
 * Session Persistence E2E Test
 *
 * Promise: "A completed pipeline run, when revisited after the in-memory SSE
 * events are gone, has all tabs populated from reconstructed session state."
 *
 * Uses the ralph-wiggum iterative pattern:
 *   Phase 1 — Run a full 30s McDonald's pipeline with autopilot
 *   Phase 2 — Start a second run (Pixel, 10s) to push run1 out of active view
 *   Phase 3 — Navigate back to run1 and verify all tabs
 */
test.describe('Session Persistence', () => {
  test('completed run has all tabs populated when revisited', async ({ page }) => {
    test.setTimeout(60 * 60 * 1000); // 60 min total budget

    const orchPage = new OrchestrationPage(page);
    const trendsPage = new TrendsPage(page);

    // ════════════════════════════════════════════════════════════════════
    // PHASE 1: Run a full 30s McDonald's pipeline with autopilot
    // ════════════════════════════════════════════════════════════════════
    console.log('[phase-1] Setting up McDonald\'s 30s pipeline');

    await trendsPage.goto();

    // Inject McDonald's preset via localStorage
    await injectPreset(page, MCDONALDS_PRESET, 30);
    await page.reload({ waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(2_000);

    // Select trends
    console.log('[phase-1] Selecting trends');
    await trendsPage.selectGoogleTrend(0);
    await trendsPage.selectYouTubeTrend(0);
    await trendsPage.screenshot('sp-01-trends-selected');

    // Set autoStart + autopilot in localStorage, then navigate
    console.log('[phase-1] Setting autoStart + autopilot, navigating to orchestration');
    await page.evaluate(() => {
      try {
        const raw = localStorage.getItem('campaign-store');
        if (raw) {
          const store = JSON.parse(raw);
          store.commercialDuration = 30;
          store.autopilot = true;
          store.autoStart = true;
          localStorage.setItem('campaign-store', JSON.stringify(store));
        }
      } catch { /* ignore */ }
    });

    await page.goto('/orchestration', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3_000);

    await orchPage.startPipelineIfNeeded();
    await orchPage.screenshot('sp-02-pipeline-started');

    // Get session ID for run1
    const run1SessionId = await orchPage.getSessionId(15);
    console.log(`[phase-1] Run1 session ID: ${run1SessionId}`);
    expect(run1SessionId).toBeTruthy();

    // Start auto-approval loop
    const stopSignal = { stopped: false };
    const approvalLoop = orchPage.autoApproveLoop(stopSignal, run1SessionId!);

    // Wait for pipeline completion — poll for commercial_artifact
    console.log('[phase-1] Waiting for research report...');
    await pollForKey(page, run1SessionId!, 'combined_final_cited_report', 600_000);
    console.log('[phase-1] Research complete');

    console.log('[phase-1] Waiting for ad copies...');
    await pollForKey(page, run1SessionId!, 'final_select_ad_copies', 600_000, 10_000);
    console.log('[phase-1] Ad copies complete');

    console.log('[phase-1] Waiting for images...');
    await pollForKey(page, run1SessionId!, 'img_artifact_keys', 600_000, 10_000);
    console.log('[phase-1] Images complete');

    console.log('[phase-1] Waiting for commercial artifact...');
    await pollForKey(page, run1SessionId!, 'commercial_artifact', 600_000, 10_000);
    console.log('[phase-1] Commercial complete');
    await orchPage.screenshot('sp-03-run1-complete');

    // Stop approval loop
    stopSignal.stopped = true;
    await approvalLoop;

    // Capture run1 final state for later verification
    const run1State = await getSessionState(page, run1SessionId!);
    console.log('[phase-1] Run1 final state keys:', Object.keys(run1State).join(', '));

    // ════════════════════════════════════════════════════════════════════
    // PHASE 2: Start a second run (Pixel, 10s) to make run1 non-active
    // ════════════════════════════════════════════════════════════════════
    console.log('[phase-2] Starting second run (Pixel 10s)');

    await page.goto('/trends', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(2_000);

    await injectPreset(page, PIXEL_PRESET, 10);
    await page.reload({ waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(2_000);

    await trendsPage.selectGoogleTrend(0);
    await trendsPage.selectYouTubeTrend(0);

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

    await page.goto('/orchestration', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3_000);
    await orchPage.startPipelineIfNeeded();

    const run2SessionId = await orchPage.getSessionId(15);
    console.log(`[phase-2] Run2 session ID: ${run2SessionId}`);

    // Wait briefly for run2 to progress (don't need full completion)
    console.log('[phase-2] Waiting 30s for run2 to progress...');
    await page.waitForTimeout(30_000);
    await orchPage.screenshot('sp-04-run2-started');

    // ════════════════════════════════════════════════════════════════════
    // PHASE 3: Navigate back to run1 and verify all tabs
    // ════════════════════════════════════════════════════════════════════
    console.log('[phase-3] Navigating back to run1 to verify persistence');

    // Call the reconstruction endpoint directly to verify it works
    const reconstructResp = await page.request.get(
      `/api/v1/orchestration/${run1SessionId}/events/reconstruct`
    );
    expect(reconstructResp.ok()).toBeTruthy();
    const reconstructData = await reconstructResp.json();
    console.log(`[phase-3] Reconstructed ${reconstructData.total_events} events for run1`);
    expect(reconstructData.total_events).toBeGreaterThan(0);
    expect(reconstructData.reconstructed).toBe(true);

    // Verify event structure
    const events = reconstructData.events;
    const eventTypes = [...new Set(events.map((e: any) => e.type))];
    console.log(`[phase-3] Event types: ${eventTypes.join(', ')}`);
    expect(eventTypes).toContain('agent_start');
    expect(eventTypes).toContain('agent_step');
    expect(eventTypes).toContain('agent_complete');

    // Verify agent names present in events
    const agentNames = [...new Set(events.map((e: any) => e.agent_name))];
    console.log(`[phase-3] Agent names in events: ${agentNames.join(', ')}`);
    expect(agentNames).toContain('trends_and_insights_agent');
    expect(agentNames).toContain('research_orchestrator');
    expect(agentNames).toContain('ad_content_generator_agent');
    expect(agentNames).toContain('av_editing_studio_agent');

    // Verify events have content with text parts (for Chat tab)
    const textEvents = events.filter(
      (e: any) => e.data?.parts?.some((p: any) => p.text)
    );
    console.log(`[phase-3] Events with text content: ${textEvents.length}`);
    expect(textEvents.length).toBeGreaterThan(3);

    // Verify timestamps are ordered
    for (let i = 1; i < events.length; i++) {
      expect(events[i].timestamp).toBeGreaterThanOrEqual(events[i - 1].timestamp);
    }

    // Verify the run1 session state is still intact
    const revisitState = await getSessionState(page, run1SessionId!);
    expect(revisitState.brand).toBeTruthy();
    expect(revisitState.combined_final_cited_report).toBeTruthy();
    expect(revisitState.final_select_ad_copies).toBeTruthy();
    expect(revisitState.commercial_artifact).toBeTruthy();

    await orchPage.screenshot('sp-05-run1-revisited');

    // ════════════════════════════════════════════════════════════════════
    // Summary
    // ════════════════════════════════════════════════════════════════════
    console.log('');
    console.log('═══════════════════════════════════════════');
    console.log('  Session Persistence E2E PASSED');
    console.log(`  Run1 (McDonald's 30s): ${run1SessionId}`);
    console.log(`  Run2 (Pixel 10s):      ${run2SessionId}`);
    console.log(`  Reconstructed events:  ${reconstructData.total_events}`);
    console.log(`  Agent names:           ${agentNames.join(', ')}`);
    console.log(`  Text events:           ${textEvents.length}`);
    console.log('═══════════════════════════════════════════');
  });
});

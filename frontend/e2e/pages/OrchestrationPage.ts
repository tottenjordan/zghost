import { type Page, type Locator } from '@playwright/test';

export class OrchestrationPage {
  readonly page: Page;

  // Pipeline controls
  readonly durationSelect: Locator;
  readonly startButton: Locator;
  readonly stopButton: Locator;

  // Chat / Approval
  readonly chatInput: Locator;
  readonly approveButton: Locator;
  readonly reviseButton: Locator;

  // Tabs
  readonly chatTab: Locator;
  readonly resultsTab: Locator;
  readonly evalTab: Locator;
  readonly detailsTab: Locator;

  constructor(page: Page) {
    this.page = page;

    this.durationSelect = page.locator('select#duration');
    this.startButton = page.getByRole('button', { name: /start pipeline/i });
    this.stopButton = page.getByRole('button', { name: /stop/i });

    this.chatInput = page.locator('input[placeholder*="Reply to the agent"]');
    this.approveButton = page.getByRole('button', { name: /approve all/i });
    this.reviseButton = page.getByRole('button', { name: /revise/i });

    this.chatTab = page.getByRole('tab', { name: /chat/i });
    this.resultsTab = page.getByRole('tab', { name: /results/i });
    this.evalTab = page.getByRole('tab', { name: /eval/i });
    this.detailsTab = page.getByRole('tab', { name: /details/i });
  }

  async goto() {
    await this.page.goto('/orchestration');
    await this.page.waitForLoadState('networkidle');
  }

  async setDuration(duration: 10 | 15 | 30) {
    await this.durationSelect.selectOption(String(duration));
  }

  /**
   * Start the pipeline. If the pipeline already auto-started (from wizard launch),
   * this is a no-op — it checks if the start button exists/enabled first.
   */
  async startPipelineIfNeeded() {
    const startVisible = await this.startButton.isVisible().catch(() => false);
    if (startVisible) {
      const startEnabled = await this.startButton.isEnabled().catch(() => false);
      if (startEnabled) {
        console.log('[orch] Clicking "Start Pipeline"');
        await this.startButton.click();
        await this.page.waitForTimeout(3_000);
        return;
      }
    }
    console.log('[orch] Pipeline already running or auto-started, skipping start');
  }

  async waitForApprovalPrompt(timeout = 120_000) {
    await this.approveButton.waitFor({ state: 'visible', timeout });
  }

  async clickApproveAll() {
    await this.approveButton.click();
    // Wait for the approval to be processed and button to disappear
    await this.page.waitForTimeout(3_000);
  }

  async typeAndSend(message: string) {
    await this.chatInput.fill(message);
    await this.chatInput.press('Enter');
    await this.page.waitForTimeout(2_000);
  }

  async waitForBanner(text: string, timeout = 300_000) {
    await this.page.getByText(text).first().waitFor({ state: 'visible', timeout });
  }

  async clickBannerButton(text: string) {
    await this.page.getByText(text).first().click();
  }

  /**
   * Get the current event count and check if the last event is an
   * `agent_complete` from `root_agent` (stream finished).
   */
  private async getEventStatus(sessionId: string): Promise<{
    count: number;
    lastIsComplete: boolean;
  }> {
    try {
      const resp = await this.page.request.get(
        `/api/v1/orchestration/${sessionId}/events`,
      );
      if (!resp.ok()) return { count: 0, lastIsComplete: false };
      const data = await resp.json();
      const events = data?.events as Array<{ type?: string; agent_name?: string }> | undefined;
      if (!events || events.length === 0) return { count: 0, lastIsComplete: false };
      const last = events[events.length - 1];
      const lastIsComplete = last.type === 'agent_complete' && last.agent_name === 'root_agent';
      return { count: events.length, lastIsComplete };
    } catch {
      return { count: 0, lastIsComplete: false };
    }
  }

  /**
   * Wait until the backend stream is complete:
   * 1. Wait for event count to exceed `afterEventCount` (new events arrived)
   * 2. Then wait for `agent_complete` from root_agent, or stabilization (20s)
   * Returns the final event count.
   */
  private async waitForStreamComplete(
    sessionId: string,
    afterEventCount: number,
    maxWaitMs: number,
    stopSignal: { stopped: boolean },
  ): Promise<number> {
    const start = Date.now();
    let lastCount = afterEventCount;
    let stablePolls = 0;
    let sawNewEvents = false;

    while (Date.now() - start < maxWaitMs && !stopSignal.stopped) {
      const status = await this.getEventStatus(sessionId);

      // Phase 1: Wait for NEW events (count > afterEventCount)
      if (!sawNewEvents) {
        if (status.count > afterEventCount) {
          sawNewEvents = true;
          lastCount = status.count;
          console.log(`[stream-wait] New events detected: ${status.count} (was ${afterEventCount})`);
        }
        await this.page.waitForTimeout(5_000);
        continue;
      }

      // Phase 2: Wait for stream to finish
      // Primary: agent_complete from root_agent (stored since our backend fix)
      if (status.lastIsComplete && status.count > lastCount) {
        return status.count;
      }
      // Also detect completion when lastIsComplete AND events stabilized
      if (status.lastIsComplete) {
        return status.count;
      }

      // Fallback: event count stable for 4 polls (20s) = stream likely done
      if (status.count === lastCount) {
        stablePolls++;
        if (stablePolls >= 4) return status.count;
      } else {
        stablePolls = 0;
      }
      lastCount = status.count;

      await this.page.waitForTimeout(5_000);
    }
    return lastCount;
  }

  /**
   * Send a message directly to the backend stream endpoint, bypassing the
   * frontend UI.  This avoids React state guards (isSending, sending) that
   * can silently block "Approve All" button clicks.
   *
   * We consume the SSE stream response body so the connection doesn't hang.
   */
  private async sendMessageDirect(
    sessionId: string,
    message: string,
  ): Promise<void> {
    const url = `/api/v1/run/${sessionId}/stream?user_id=default-user&message=${encodeURIComponent(message)}`;
    try {
      // Fire-and-forget: consume enough to confirm the request started
      const resp = await this.page.request.get(url, { timeout: 600_000 });
      // Response body is the full SSE stream — just dispose it
      await resp.dispose();
    } catch {
      // Stream may have been interrupted or timed out — that's OK
      // Events are still stored server-side
    }
  }

  /**
   * Auto-approval loop — sends approval messages directly to the backend
   * API, waiting for each stream to complete before sending the next.
   *
   * This bypasses the frontend UI entirely to avoid React state guards
   * (isSending, sending, sendingRef) that can silently block button clicks.
   */
  async autoApproveLoop(
    stopSignal: { stopped: boolean },
    sessionId?: string,
  ) {
    if (!sessionId) {
      console.log('[auto-approve] No session ID, skipping');
      return;
    }

    let knownEventCount = 0;

    // Wait for the initial pipeline start stream to complete
    console.log('[auto-approve] Waiting for initial stream to complete...');
    knownEventCount = await this.waitForStreamComplete(
      sessionId, 0, 300_000, stopSignal,
    );
    console.log(`[auto-approve] Initial stream completed (${knownEventCount} events)`);

    let lastApprovalTime = 0;

    while (!stopSignal.stopped) {
      try {
        // Check if the stream is done (agent waiting for input)
        const status = await this.getEventStatus(sessionId);
        if (!status.lastIsComplete && status.count === knownEventCount) {
          // Still processing or no change — wait
          await this.page.waitForTimeout(5_000);
          continue;
        }

        // Throttle: minimum 15s between approvals to avoid rapid-fire loops
        const now = Date.now();
        const sinceLast = now - lastApprovalTime;
        if (sinceLast < 15_000) {
          await this.page.waitForTimeout(15_000 - sinceLast);
        }

        // Stream is complete — send approval message directly via API
        console.log(`[auto-approve] Sending approval at ${new Date().toISOString()} (events: ${status.count})`);
        lastApprovalTime = Date.now();
        await this.sendMessageDirect(sessionId, 'Looks good, proceed with all options.');

        // Update known event count from what the stream produced
        const afterStatus = await this.getEventStatus(sessionId);
        knownEventCount = afterStatus.count;
        console.log(`[auto-approve] Stream completed (${knownEventCount} events)`);

      } catch (err) {
        console.log(`[auto-approve] Error: ${err}`);
      }
      await this.page.waitForTimeout(5_000);
    }
  }

  /**
   * Get the session ID from localStorage (with retries).
   * Falls back to extracting from the page's event stream if localStorage fails.
   */
  async getSessionId(maxRetries = 10): Promise<string | null> {
    for (let i = 0; i < maxRetries; i++) {
      const id = await this.page.evaluate(() => {
        try {
          const raw = localStorage.getItem('campaign-store');
          if (!raw) return null;
          const store = JSON.parse(raw);
          const state = store?.state ?? store;
          const sessions = state?.sessions ?? [];
          const activeIndex = state?.activeSessionIndex ?? 0;
          const fromSessions = sessions[activeIndex]?.sessionId;
          if (fromSessions) return fromSessions;
          // Also check top-level sessionId
          if (state?.sessionId) return state.sessionId;
          return null;
        } catch {
          return null;
        }
      });
      if (id) return id;
      console.log(`[orch] Session ID not found (attempt ${i + 1}/${maxRetries}), retrying...`);
      await this.page.waitForTimeout(3_000);
    }

    // Fallback: try to extract from page content (event stream shows session_id)
    const fallbackId = await this.page.evaluate(() => {
      const text = document.body.innerText;
      const match = text.match(/session_id["\s:]+([a-f0-9-]{36})/i);
      return match?.[1] ?? null;
    });
    if (fallbackId) {
      console.log(`[orch] Session ID found via page text fallback: ${fallbackId}`);
    }
    return fallbackId;
  }

  async screenshot(name: string) {
    await this.page.screenshot({ path: `screenshots/${name}.png`, fullPage: true });
  }
}

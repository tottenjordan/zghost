import { type Page } from '@playwright/test';

/**
 * Poll session state via the API until a specific key is populated.
 *
 * @param page - Playwright page (used for page.request)
 * @param sessionId - ADK session ID
 * @param key - Top-level state key to check (e.g. 'combined_final_cited_report')
 * @param timeout - Max wait time in ms (default 5 min)
 * @param interval - Poll interval in ms (default 5s)
 * @returns The value of the key once populated
 */
export async function pollForKey(
  page: Page,
  sessionId: string,
  key: string,
  timeout = 300_000,
  interval = 5_000,
): Promise<unknown> {
  const start = Date.now();
  const url = `/api/v1/sessions/${sessionId}/state?user_id=default-user`;

  while (Date.now() - start < timeout) {
    try {
      const resp = await page.request.get(url);
      if (resp.ok()) {
        const body = await resp.json();
        const state = body?.state ?? body;
        const value = state?.[key];

        if (isPopulated(value)) {
          console.log(`[poller] Key "${key}" populated after ${Math.round((Date.now() - start) / 1000)}s`);
          return value;
        }
      }
    } catch {
      // Network hiccup — retry
    }
    await page.waitForTimeout(interval);
  }

  throw new Error(`Timed out waiting for state key "${key}" after ${timeout / 1000}s`);
}

/**
 * Fetch the full session state.
 */
export async function getSessionState(
  page: Page,
  sessionId: string,
): Promise<Record<string, unknown>> {
  const url = `/api/v1/sessions/${sessionId}/state?user_id=default-user`;
  const resp = await page.request.get(url);
  if (!resp.ok()) {
    throw new Error(`Failed to fetch session state: ${resp.status()}`);
  }
  const body = await resp.json();
  return body?.state ?? body;
}

function isPopulated(value: unknown): boolean {
  if (value === null || value === undefined) return false;
  if (typeof value === 'string') return value.trim().length > 0;
  if (Array.isArray(value)) return value.length > 0;
  if (typeof value === 'object') {
    // Check nested arrays (e.g. { img_artifact_keys: [...] })
    const vals = Object.values(value as Record<string, unknown>);
    return vals.some((v) => {
      if (Array.isArray(v)) return v.length > 0;
      if (typeof v === 'string') return v.trim().length > 0;
      return v !== null && v !== undefined;
    });
  }
  return true;
}

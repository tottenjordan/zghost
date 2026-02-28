import { type Page, type Locator } from '@playwright/test';

export class TrendsPage {
  readonly page: Page;
  readonly presetSelect: Locator;
  readonly saveConfigButton: Locator;
  readonly launchButton: Locator;

  constructor(page: Page) {
    this.page = page;
    this.presetSelect = page.locator('select').first();
    this.saveConfigButton = page.getByRole('button', { name: /save configuration/i });
    this.launchButton = page.getByRole('button', { name: /add execution run/i });
  }

  async goto() {
    await this.page.goto('/trends');
    await this.page.waitForLoadState('networkidle');
  }

  async loadPresetAndSave(label: string = 'Google Pixel 9 Pro') {
    await this.presetSelect.selectOption({ label });
    await this.page.waitForTimeout(1_000);
    await this.saveConfigButton.scrollIntoViewIfNeeded();
    await this.saveConfigButton.click();
    await this.page.waitForTimeout(1_000);
    try {
      await this.page.getByText('Configuration saved successfully').waitFor({
        state: 'visible',
        timeout: 5_000,
      });
      console.log('[trends] Configuration saved successfully');
    } catch {
      console.log('[trends] Save confirmation not visible, continuing');
    }
  }

  /**
   * Click a wizard step tab by programmatically finding and clicking the button
   * whose text content contains the step label within the TabsList container.
   */
  async goToStep(stepLabel: 'Campaign' | 'Trends' | 'Evaluation' | 'Review') {
    // Scroll to top first so step bar is in view
    await this.page.evaluate(() => window.scrollTo(0, 0));
    await this.page.waitForTimeout(300);

    // Programmatically find and click the correct step button
    const clicked = await this.page.evaluate((label) => {
      // Find the TabsList container (div with inline-flex and rounded-lg containing 4 buttons)
      const divs = document.querySelectorAll('div');
      for (const div of divs) {
        const cls = div.className;
        if (cls.includes('inline-flex') && cls.includes('rounded-lg') && cls.includes('backdrop-blur')) {
          const buttons = div.querySelectorAll('button');
          if (buttons.length >= 4) {
            for (const btn of buttons) {
              if (btn.textContent?.includes(label)) {
                btn.click();
                return { clicked: true, text: btn.textContent };
              }
            }
          }
        }
      }
      return { clicked: false, text: null };
    }, stepLabel);

    console.log(`[trends] goToStep("${stepLabel}"):`, JSON.stringify(clicked));
    await this.page.waitForTimeout(1_000);
  }

  async selectGoogleTrend(index = 0) {
    await this.goToStep('Trends');
    await this.screenshot('debug-trends-tab');
    await this.page.waitForTimeout(2_000);

    // Within the Trends tab content, click the Google Search inner tab if present
    const googleSearchClicked = await this.page.evaluate(() => {
      const buttons = document.querySelectorAll('button');
      for (const btn of buttons) {
        if (btn.textContent?.includes('Google Search')) {
          btn.click();
          return true;
        }
      }
      return false;
    });
    console.log(`[trends] Google Search inner tab clicked: ${googleSearchClicked}`);
    await this.page.waitForTimeout(1_000);

    // Now find and click checkboxes
    const checkboxes = this.page.locator('input[type="checkbox"]');
    const count = await checkboxes.count();
    console.log(`[trends] Found ${count} checkboxes`);
    if (count > index) {
      await checkboxes.nth(index).click();
      await this.page.waitForTimeout(500);
    } else {
      // Fallback: click card directly via evaluate
      console.log('[trends] No checkboxes found, clicking first card via JS');
      await this.page.evaluate((idx) => {
        const cards = document.querySelectorAll('[class*="cursor-pointer"]');
        if (cards.length > idx) {
          (cards[idx] as HTMLElement).click();
        }
      }, index);
    }
  }

  async selectYouTubeTrend(index = 0) {
    // Click YouTube inner tab
    const ytClicked = await this.page.evaluate(() => {
      const buttons = document.querySelectorAll('button');
      for (const btn of buttons) {
        if (btn.textContent?.includes('YouTube')) {
          btn.click();
          return true;
        }
      }
      return false;
    });
    console.log(`[trends] YouTube inner tab clicked: ${ytClicked}`);
    await this.page.waitForTimeout(1_000);

    const checkboxes = this.page.locator('input[type="checkbox"]');
    const count = await checkboxes.count();
    console.log(`[trends] Found ${count} YouTube checkboxes`);
    if (count > index) {
      await checkboxes.nth(index).click();
      await this.page.waitForTimeout(500);
    } else {
      console.log('[trends] No YT checkboxes, clicking first card via JS');
      await this.page.evaluate((idx) => {
        const cards = document.querySelectorAll('[class*="cursor-pointer"]');
        if (cards.length > idx) {
          (cards[idx] as HTMLElement).click();
        }
      }, index);
    }
  }

  async clickLaunch() {
    await this.goToStep('Review');
    await this.page.waitForTimeout(1_000);

    const isDisabled = await this.launchButton.isDisabled();
    if (isDisabled) {
      console.log('[trends] Launch button is disabled');
      await this.screenshot('launch-button-disabled');
    }

    await this.launchButton.click({ timeout: 15_000 });
    await this.page.waitForURL('**/orchestration**', { timeout: 10_000 });
  }

  async screenshot(name: string) {
    await this.page.screenshot({ path: `screenshots/${name}.png`, fullPage: true });
  }
}

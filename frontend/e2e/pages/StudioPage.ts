import { type Page, type Locator } from '@playwright/test';

export class StudioPage {
  readonly page: Page;
  readonly videoPlayer: Locator;
  readonly clipsTab: Locator;

  constructor(page: Page) {
    this.page = page;
    this.videoPlayer = page.locator('video').first();
    this.clipsTab = page.getByText('Clips');
  }

  async goto(sessionId: string) {
    await this.page.goto(`/studio?session=${sessionId}`);
    await this.page.waitForLoadState('networkidle');
  }

  async waitForCommercial(timeout = 60_000) {
    await this.videoPlayer.waitFor({ state: 'visible', timeout });
  }

  async verifyCommercialPlays() {
    // Click play and check that video time advances
    await this.videoPlayer.click();
    await this.page.waitForTimeout(2_000);
    const currentTime = await this.videoPlayer.evaluate(
      (v: HTMLVideoElement) => v.currentTime,
    );
    return currentTime > 0;
  }

  async screenshot(name: string) {
    await this.page.screenshot({ path: `screenshots/${name}.png`, fullPage: true });
  }
}

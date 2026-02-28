import { type Page, type Locator } from '@playwright/test';

export class NarrativePage {
  readonly page: Page;
  readonly acceptButton: Locator;
  readonly skipButton: Locator;
  readonly chatInput: Locator;

  constructor(page: Page) {
    this.page = page;
    this.acceptButton = page.getByRole('button', { name: /accept report/i });
    this.skipButton = page.getByRole('button', { name: /skip to creative/i });
    this.chatInput = page.locator('input[placeholder*="Reply"], textarea[placeholder*="Reply"]');
  }

  async goto(sessionId: string) {
    await this.page.goto(`/narrative?session=${sessionId}`);
    await this.page.waitForLoadState('networkidle');
  }

  async waitForReportLoad(timeout = 60_000) {
    // Report loads as either inline text or a PDF iframe
    await this.page.waitForFunction(
      () => {
        const iframe = document.querySelector('iframe');
        const textContent = document.body.innerText;
        return (
          (iframe && iframe.src && iframe.src.length > 0) ||
          textContent.includes('Research Report') ||
          textContent.includes('report') ||
          textContent.length > 2000
        );
      },
      { timeout },
    );
  }

  async acceptReport() {
    await this.acceptButton.click();
    await this.page.waitForURL('**/orchestration**', { timeout: 10_000 });
  }

  async skipToCreative() {
    await this.skipButton.click();
    await this.page.waitForURL('**/orchestration**', { timeout: 10_000 });
  }

  async screenshot(name: string) {
    await this.page.screenshot({ path: `screenshots/${name}.png`, fullPage: true });
  }
}

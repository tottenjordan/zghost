#!/usr/bin/env python3
"""
Capture screenshots of all frontend pages for documentation.
"""
from playwright.sync_api import sync_playwright
import time

def capture_screenshots():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = context.new_page()

        screenshots_dir = '/usr/local/google/home/jwortz/zghost/.claude/worktrees/frontend-workflow/frontend/docs/screenshots'
        base_url = 'http://localhost:5174'

        # Page 1: Trend Discovery (landing page)
        print("Capturing Trend Discovery page...")
        page.goto(f'{base_url}/trends')
        page.wait_for_load_state('networkidle')
        time.sleep(2)  # Wait for any animations
        page.screenshot(path=f'{screenshots_dir}/trends-page.png', full_page=True)

        # Page 2: Agent Orchestration (note: may crash)
        print("Capturing Orchestration page...")
        try:
            page.goto(f'{base_url}/orchestration')
            page.wait_for_load_state('networkidle')
            time.sleep(2)
            page.screenshot(path=f'{screenshots_dir}/orchestration-page.png', full_page=True)
        except Exception as e:
            print(f"Orchestration page error (expected): {e}")

        # Page 3: Rating & Evaluation
        print("Capturing Rating page...")
        page.goto(f'{base_url}/rating')
        page.wait_for_load_state('networkidle')
        time.sleep(2)
        page.screenshot(path=f'{screenshots_dir}/rating-page.png', full_page=True)

        # Rating - Manage Rubrics tab
        print("Capturing Rating - Manage Rubrics tab...")
        page.click('button:has-text("Manage Rubrics")')
        time.sleep(1)
        page.screenshot(path=f'{screenshots_dir}/rating-rubrics.png', full_page=True)

        # Rating - Results tab
        print("Capturing Rating - Results tab...")
        page.click('button:has-text("Results")')
        time.sleep(1)
        page.screenshot(path=f'{screenshots_dir}/rating-results.png', full_page=True)

        # Page 4: AV Studio
        print("Capturing AV Studio page...")
        page.goto(f'{base_url}/studio')
        page.wait_for_load_state('networkidle')
        time.sleep(2)
        page.screenshot(path=f'{screenshots_dir}/studio-page.png', full_page=True)

        # Page 5: Narrative Interface
        print("Capturing Narrative page...")
        page.goto(f'{base_url}/narrative')
        page.wait_for_load_state('networkidle')
        time.sleep(2)
        page.screenshot(path=f'{screenshots_dir}/narrative-page.png', full_page=True)

        # Additional: Sidebar expanded
        print("Capturing sidebar...")
        page.goto(f'{base_url}/trends')
        page.wait_for_load_state('networkidle')
        # Sidebar should be visible by default
        time.sleep(1)
        page.screenshot(path=f'{screenshots_dir}/sidebar-expanded.png')

        browser.close()
        print("\nAll screenshots captured successfully!")

if __name__ == '__main__':
    capture_screenshots()

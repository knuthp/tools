import os
from playwright.sync_api import sync_playwright

def run_cuj(page):
    # Load the standalone HTML file using file://
    file_path = os.path.abspath("genealogy_scrollytelling.html")
    page.goto(f"file://{file_path}")
    page.wait_for_timeout(1000)

    # Step 1: Initial state is loaded. Take screenshot.
    page.screenshot(path="/home/jules/verification/screenshots/step1_initial.png")
    page.wait_for_timeout(500)

    # Scroll step-by-step
    steps = ["#step-1", "#step-2", "#step-3", "#step-4", "#step-5", "#step-6"]
    for i, step in enumerate(steps):
        element = page.locator(step)
        if element.is_visible():
            element.scroll_into_view_if_needed()
            page.wait_for_timeout(1000)
            # Take screenshots of key transitions
            if i == 2: # Step 3 (Fictitious ghosts)
                page.screenshot(path="/home/jules/verification/screenshots/step3_ghosts.png")
            elif i == 4: # Step 5 (Prussian nobles fully revealed)
                page.screenshot(path="/home/jules/verification/screenshots/step5_revealed.png")

    # Step 6: Final step. Select an ancestor from the dropdown to test interactive features
    page.screenshot(path="/home/jules/verification/screenshots/step6_interactive.png")
    page.wait_for_timeout(500)

    # Interact with dropdown
    select = page.locator("#ancestor-select")
    select.select_option("alistair")
    page.wait_for_timeout(1000)
    page.screenshot(path="/home/jules/verification/screenshots/step6_selected_alistair.png")
    page.wait_for_timeout(1000)

if __name__ == "__main__":
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            record_video_dir="/home/jules/verification/videos"
        )
        page = context.new_page()
        try:
            run_cuj(page)
        finally:
            context.close()
            browser.close()

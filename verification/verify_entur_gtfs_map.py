import os
from playwright.sync_api import sync_playwright

def run_cuj(page):
    # Go to the local server
    page.goto("http://localhost:8000/entur_gtfs_map.html")
    page.wait_for_timeout(2000)  # Wait for initial load

    # Initial view
    page.screenshot(path="/home/jules/verification/screenshots/initial_load.png")

    # Change day to Saturday
    page.select_option("#day-select", "saturday")
    page.wait_for_timeout(500)

    # Uncheck Ferry
    page.get_by_label("Ferry").uncheck()
    page.wait_for_timeout(500)

    # Click Update Map
    page.click("#update-btn")

    # Wait for the status to change and then back to "Found X stations"
    # Or just wait a few seconds as it involves heavy DuckDB query
    try:
        page.wait_for_selector("#loading", state="hidden", timeout=120000)
    except Exception as e:
        print(f"Loading took too long: {e}")

    # Take screenshot after update
    page.screenshot(path="/home/jules/verification/screenshots/after_update.png")

    # Hover over the center of the map where Oslo is likely to have columns
    # Oslo is center [10.7522, 59.9139]
    # We'll just try to hover over some area in the middle of the map
    viewport = page.viewport_size
    page.mouse.move(viewport['width'] / 2, viewport['height'] / 2)
    page.wait_for_timeout(1000)

    # Take final screenshot with tooltip
    page.screenshot(path="/home/jules/verification/screenshots/verification.png")
    page.wait_for_timeout(1000)

if __name__ == "__main__":
    os.makedirs("/home/jules/verification/videos", exist_ok=True)
    os.makedirs("/home/jules/verification/screenshots", exist_ok=True)
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

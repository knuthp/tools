import os

from playwright.sync_api import sync_playwright


def verify_ais_trips():
    os.makedirs("/home/jules/verification/video", exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Record video
        context = browser.new_context(record_video_dir="/home/jules/verification/video")
        page = context.new_page()
        page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))
        page.on("pageerror", lambda exc: print(f"BROWSER ERROR: {exc}"))

        # Start a local server to serve the file
        import subprocess
        import time
        server = subprocess.Popen(["python3", "-m", "http.server", "8000"])
        time.sleep(2) # Wait for server to start

        try:
            page.goto("http://localhost:8000/ais_trips.html")

            # Wait for DuckDB to initialize and data to load
            # The status element changes to "Loaded ... vessels."
            # Increased timeout for slow data fetch in CI/sandbox
            page.wait_for_selector("text=Loaded", timeout=300000)

            # Wait for animation to run for a bit
            page.wait_for_timeout(5000)

            # Take a screenshot
            page.screenshot(path="/home/jules/verification/ais_trips.png")

            # Interact with controls
            page.fill("#speed", "2000")
            page.wait_for_timeout(2000)

            page.fill("#trail", "60")
            page.wait_for_timeout(2000)

            page.screenshot(path="/home/jules/verification/ais_trips_controls.png")

        finally:
            context.close()
            browser.close()
            server.terminate()

if __name__ == "__main__":
    verify_ais_trips()

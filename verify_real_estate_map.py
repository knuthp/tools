import http.server
import os
import sys
import threading
import time

from playwright.sync_api import sync_playwright


def run_server():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    handler = http.server.SimpleHTTPRequestHandler
    httpd = http.server.HTTPServer(('127.0.0.1', 8000), handler)
    httpd.serve_forever()

def verify():
    # Start local server in a thread
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    time.sleep(2)  # Give the server time to start

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        # Navigate to the tool
        print("Navigating to http://127.0.0.1:8000/real_estate_map.html")
        page.goto("http://127.0.0.1:8000/real_estate_map.html")

        # Wait for the status to change from "Loading..." and "Fetching data..."
        print("Waiting for data to load...")
        # Use a function to wait until text contains "Found" or "Error"
        page.wait_for_function(
            "document.getElementById('status').innerText.includes('Found') || "
            "document.getElementById('status').innerText.includes('Error')",
            timeout=30000
        )

        status_text = page.inner_text("#status")
        print(f"Status: {status_text}")

        if "Found" not in status_text:
            print("Error: Data didn't load correctly")
            browser.close()
            sys.exit(1)

        # Check if table has rows
        rows_count = page.locator("#table-body tr").count()
        print(f"Table rows: {rows_count}")
        if rows_count == 0:
            print("Error: Table is empty")
            browser.close()
            sys.exit(1)

        # Verify map exists
        if not page.query_selector("#map"):
            print("Error: Map container not found")
            browser.close()
            sys.exit(1)

        # Take a screenshot
        page.screenshot(path="verification/real_estate_map.png")
        print("Screenshot saved to verification/real_estate_map.png")

        browser.close()
    print("Verification successful!")

if __name__ == "__main__":
    if not os.path.exists("verification"):
        os.makedirs("verification")
    verify()

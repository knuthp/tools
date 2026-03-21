from playwright.sync_api import sync_playwright
import os
import http.server
import socketserver
import threading

PORT = 8000

class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

def run():
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        thread = threading.Thread(target=httpd.serve_forever)
        thread.daemon = True
        thread.start()

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(record_video_dir="verification/video")
            page = context.new_page()

            page.on("pageerror", lambda exc: print(f"uncaught exception: {exc}"))
            page.on("console", lambda msg: print(f"console {msg.type}: {msg.text}"))

            page.goto(f"http://localhost:{PORT}/fox_platformer.html")
            page.wait_for_timeout(3000)

            page.screenshot(path="verification/start_screen.png")

            # Click to start
            page.mouse.click(400, 300)
            page.wait_for_timeout(3000)

            page.screenshot(path="verification/gameplay.png")

            # Move right
            page.keyboard.down("ArrowRight")
            page.wait_for_timeout(2000)
            page.keyboard.up("ArrowRight")
            page.screenshot(path="verification/after_movement.png")

            context.close()
            browser.close()

        httpd.shutdown()

if __name__ == "__main__":
    run()

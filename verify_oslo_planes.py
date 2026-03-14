import asyncio
import os

from playwright.async_api import async_playwright


async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(args=['--disable-web-security'])
        context = await browser.new_context(viewport={'width': 1280, 'height': 720})
        page = await context.new_page()

        file_path = f"file://{os.path.abspath('oslo_planes.html')}"
        print(f"Loading: {file_path}")

        await page.goto(file_path)

        # Wait for data to load and render
        print("Waiting for aircraft data...")
        try:
            await page.wait_for_function(
                "() => document.getElementById('status').textContent"
                ".includes('aircraft tracked')",
                timeout=30000
            )
        except Exception as e:
            print(f"Timeout or error waiting for status: {e}")
            await browser.close()
            return

        status = await page.text_content('#status')
        print(f"Status: {status}")

        # Give it a moment to render icons
        await asyncio.sleep(2)

        await page.screenshot(path='oslo_planes_final.png')
        print("Screenshot saved to oslo_planes_final.png")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
